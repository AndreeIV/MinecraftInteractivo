"""
Puente Asíncrono entre TikTok Live y Minecraft Server (vía RCON).

Escucha eventos en tiempo real de un stream de TikTok Live (Regalos, Comentarios,
Likes y Nuevos Seguidores) y ejecuta comandos dinámicos en un servidor de
Minecraft mediante el protocolo RCON.
"""

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcrcon import MCRcon, MCRconException
from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent,
    FollowEvent,
    GiftEvent,
    LikeEvent,
)

# =====================================================================
# CONFIGURACIÓN DE LOGGING
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TikTokMCBridge")


# =====================================================================
# CLIENTE RCON ASÍNCRONO Y ROBUSTO PARA MINECRAFT
# =====================================================================
class AsyncMinecraftRCON:
    """
    Gestiona la conexión RCON con el servidor de Minecraft de forma segura
    para programación asíncrona (asyncio), incluyendo reconexión automática.
    """

    def __init__(self, host: str, port: int, password: str) -> None:
        self.host = host
        self.port = port
        self.password = password
        self._rcon: Optional[MCRcon] = None
        self._lock = asyncio.Lock()
        self._connected = False

    def _connect_sync(self) -> bool:
        """Establece la conexión síncrona con RCON (ejecutado en un hilo separado)."""
        try:
            if self._rcon is not None:
                try:
                    self._rcon.disconnect()
                except Exception:
                    pass
            self._rcon = MCRcon(self.host, self.password, port=self.port)
            self._rcon.connect()
            self._connected = True
            logger.info(f"Conectado exitosamente a Minecraft RCON ({self.host}:{self.port})")
            return True
        except Exception as exc:
            self._connected = False
            logger.error(f"No se pudo conectar a Minecraft RCON ({self.host}:{self.port}): {exc}")
            return False

    async def connect(self) -> bool:
        """Inicia la conexión RCON de manera asíncrona."""
        async with self._lock:
            return await asyncio.to_thread(self._connect_sync)

    def _send_command_sync(self, command: str) -> Optional[str]:
        """Envía un comando por RCON con reintento automático si se perdió la conexión."""
        if not self._connected or self._rcon is None:
            if not self._connect_sync():
                return None

        try:
            # En RCON los comandos no requieren el '/' inicial, pero lo limpiamos por seguridad
            clean_cmd = command.lstrip("/")
            response = self._rcon.command(clean_cmd)
            return response
        except (MCRconException, ConnectionError, OSError, Exception) as exc:
            logger.warning(f"Error al enviar comando RCON ('{command}'): {exc}. Intentando reconectar...")
            self._connected = False
            if self._connect_sync() and self._rcon is not None:
                try:
                    clean_cmd = command.lstrip("/")
                    return self._rcon.command(clean_cmd)
                except Exception as retry_exc:
                    logger.error(f"Fallo definitivo al reenviar comando '{command}': {retry_exc}")
            return None

    async def execute_command(self, command: str) -> Optional[str]:
        """Ejecuta un comando de Minecraft de forma asíncrona sin bloquear el Event Loop."""
        async with self._lock:
            response = await asyncio.to_thread(self._send_command_sync, command)
            logger.info(f"[MC CMD] -> /{command.lstrip('/')}")
            if response:
                logger.debug(f"[MC RSP] <- {response}")
            return response

    async def execute_batch(self, commands: List[str], delay: float = 0.05) -> None:
        """Ejecuta una lista de comandos con una pequeña pausa entre ellos para no saturar el servidor."""
        for cmd in commands:
            await self.execute_command(cmd)
            if delay > 0:
                await asyncio.sleep(delay)

    async def disconnect(self) -> None:
        """Cierra la conexión RCON de forma limpia."""
        async with self._lock:
            if self._rcon is not None and self._connected:
                try:
                    await asyncio.to_thread(self._rcon.disconnect)
                    logger.info("Conexión RCON cerrada correctamente.")
                except Exception as exc:
                    logger.debug(f"Error al cerrar RCON: {exc}")
                finally:
                    self._connected = False


# =====================================================================
# GESTOR DE REGLAS Y MAPEO DE EVENTOS
# =====================================================================
class EventMapper:
    """
    Carga y gestiona el mapeo de eventos desde un archivo JSON (o diccionario por defecto),
    controlando cooldowns, acumuladores de likes y formateo seguro de variables.
    """

    DEFAULT_CONFIG: Dict[str, Any] = {
        "target_player": "@p",
        "gifts": {
            "Rose": {
                "scale_with_count": True,
                "max_repeats": 25,
                "commands": ["execute at {player} run summon minecraft:zombie ~ ~ ~"],
            },
            "Rosa": {
                "scale_with_count": True,
                "max_repeats": 25,
                "commands": ["execute at {player} run summon minecraft:zombie ~ ~ ~"],
            },
            "GG": {
                "scale_with_count": False,
                "commands": ["give {player} minecraft:diamond {count}"],
            },
            "TikTok": {
                "scale_with_count": False,
                "commands": ["give {player} minecraft:diamond {count}"],
            },
        },
        "comments": {
            "!creeper": {
                "cooldown_seconds": 15,
                "commands": ["execute at {player} run summon minecraft:creeper ~ ~ ~"],
            }
        },
        "likes": {
            "threshold": 50,
            "commands": ["effect give {player} minecraft:speed 10 1"],
        },
        "follow": {
            "enabled": True,
            "cooldown_seconds": 5,
            "commands": ["give {player} minecraft:golden_apple 1"],
        },
    }

    def __init__(self, config_path: Path, default_player: str = "@p") -> None:
        self.config_path = config_path
        self.default_player = default_player
        self.config: Dict[str, Any] = self._load_config()

        # Estado interno para control de spam (cooldowns y acumulador de likes)
        self._comment_cooldowns: Dict[str, float] = {}
        self._last_follow_time: float = 0.0
        self._accumulated_likes: int = 0

    def _load_config(self) -> Dict[str, Any]:
        """Carga la configuración desde JSON o usa el diccionario por defecto si falla."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Reglas de eventos cargadas desde '{self.config_path.name}'")
                    return data
            except Exception as exc:
                logger.error(f"Error leyendo {self.config_path}: {exc}. Usando configuración por defecto.")
        else:
            logger.warning(f"No se encontró '{self.config_path.name}'. Usando configuración por defecto.")
        return self.DEFAULT_CONFIG

    @staticmethod
    def sanitize_username(username: str) -> str:
        """Limpia el nombre de usuario para evitar romper JSON o inyectar comandos en Minecraft."""
        clean = re.sub(r'["\'\\{}\[\]\n\r]', "", username or "Usuario")
        return clean[:24] if clean else "Usuario"

    def format_commands(
        self,
        raw_commands: List[str],
        user: str,
        count: int = 1,
        threshold: int = 1,
    ) -> List[str]:
        """Reemplaza los placeholders ({player}, {user}, {count}, {threshold}) en los comandos."""
        player = os.getenv("MC_TARGET_PLAYER") or self.config.get("target_player", self.default_player)
        safe_user = self.sanitize_username(user)

        replacements = {
            "{player}": str(player),
            "{user}": str(safe_user),
            "{count}": str(count),
            "{threshold}": str(threshold),
        }

        formatted = []
        for cmd in raw_commands:
            result = cmd
            for placeholder, value in replacements.items():
                result = result.replace(placeholder, value)
            formatted.append(result)
        return formatted

    def get_gift_commands(self, gift_name: str, gift_id: int, user: str, count: int) -> List[str]:
        """Busca si el regalo (por nombre o ID) tiene comandos asociados."""
        gifts_cfg: Dict[str, Any] = self.config.get("gifts", {})

        # Búsqueda insensible a mayúsculas/minúsculas por nombre o por ID en string
        matched_rule = None
        for key, rule in gifts_cfg.items():
            if key.lower() == gift_name.lower() or key == str(gift_id):
                matched_rule = rule
                break

        if not matched_rule:
            return []

        raw_commands = matched_rule.get("commands", [])
        scale_with_count = matched_rule.get("scale_with_count", False)
        max_repeats = matched_rule.get("max_repeats", 20)

        if scale_with_count and count > 1:
            # Si scale_with_count es True (ej. invocar 1 zombie por cada Rosa),
            # repetimos los comandos de acción (como summon) pero enviamos el anuncio (tellraw) solo 1 vez.
            repeats = min(count, max_repeats)
            action_cmds = [c for c in raw_commands if not c.lstrip("/").startswith("tellraw")]
            announce_cmds = [c for c in raw_commands if c.lstrip("/").startswith("tellraw")]

            final_cmds: List[str] = []
            for _ in range(repeats):
                final_cmds.extend(self.format_commands(action_cmds, user=user, count=count))
            final_cmds.extend(self.format_commands(announce_cmds, user=user, count=count))
            return final_cmds

        return self.format_commands(raw_commands, user=user, count=count)

    def get_comment_commands(self, comment_text: str, user: str) -> List[str]:
        """Evalúa si un comentario coincide con un comando del chat y verifica su cooldown."""
        comments_cfg: Dict[str, Any] = self.config.get("comments", {})
        clean_text = comment_text.strip().lower()

        # Permite coincidencia exacta o que empiece por el comando (ej. "!creeper")
        matched_key = None
        matched_rule = None
        for key, rule in comments_cfg.items():
            if clean_text == key.lower() or clean_text.startswith(key.lower() + " "):
                matched_key = key.lower()
                matched_rule = rule
                break

        if not matched_rule or not matched_key:
            return []

        now = time.monotonic()
        cooldown = float(matched_rule.get("cooldown_seconds", 10))
        last_used = self._comment_cooldowns.get(matched_key, 0.0)

        if now - last_used < cooldown:
            remaining = int(cooldown - (now - last_used))
            logger.info(f"Comando '{matched_key}' de {user} en enfriamiento ({remaining}s restantes).")
            return []

        self._comment_cooldowns[matched_key] = now
        raw_commands = matched_rule.get("commands", [])
        return self.format_commands(raw_commands, user=user)

    def process_likes(self, like_count: int, user: str) -> List[str]:
        """Acumula likes y devuelve comandos cada vez que se supera el umbral configurado."""
        likes_cfg: Dict[str, Any] = self.config.get("likes", {})
        threshold = int(likes_cfg.get("threshold", 50))
        if threshold <= 0:
            return []

        self._accumulated_likes += like_count
        logger.info(
            f"[LIKE] +{like_count} likes de {user} (Progreso: {self._accumulated_likes}/{threshold})"
        )

        if self._accumulated_likes >= threshold:
            # Reiniciamos el contador conservando el excedente
            self._accumulated_likes %= threshold
            raw_commands = likes_cfg.get("commands", [])
            return self.format_commands(raw_commands, user=user, count=like_count, threshold=threshold)

        return []

    def get_follow_commands(self, user: str) -> List[str]:
        """Devuelve los comandos al recibir un nuevo seguidor, respetando el cooldown."""
        follow_cfg: Dict[str, Any] = self.config.get("follow", {})
        if not follow_cfg.get("enabled", True):
            return []

        now = time.monotonic()
        cooldown = float(follow_cfg.get("cooldown_seconds", 5))
        if now - self._last_follow_time < cooldown:
            return []

        self._last_follow_time = now
        raw_commands = follow_cfg.get("commands", [])
        return self.format_commands(raw_commands, user=user)


# =====================================================================
# PUENTE PRINCIPAL TIKTOK LIVE <-> MINECRAFT
# =====================================================================
class TikTokMinecraftBridge:
    """Orquesta la escucha de eventos de TikTokLive y el despacho hacia Minecraft RCON."""

    def __init__(
        self,
        tiktok_username: str,
        rcon_client: AsyncMinecraftRCON,
        mapper: EventMapper,
    ) -> None:
        # Aseguramos que el usuario tenga el formato correcto (con @ al inicio)
        self.username = tiktok_username if tiktok_username.startswith("@") else f"@{tiktok_username}"
        self.rcon = rcon_client
        self.mapper = mapper
        self.client = TikTokLiveClient(unique_id=self.username)

        self._register_events()

    def _register_events(self) -> None:
        """Registra los manejadores asíncronos para cada evento de TikTok Live."""

        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent) -> None:
            logger.info(f"¡Conectado exitosamente al TikTok Live de {event.unique_id} (Room ID: {self.client.room_id})!")
            await self.rcon.execute_command(
                f'tellraw @a ["",{{"text":"[TikTok Live] ","color":"light_purple","bold":true}},'
                f'{{"text":"Conectado al directo de {self.username}","color":"green"}}]'
            )

        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent) -> None:
            logger.warning(f"Desconectado del TikTok Live de {self.username}.")

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent) -> None:
            user = event.user.nickname or event.user.unique_id or "Anonimo"
            comment = event.comment
            logger.info(f"[CHAT] {user}: {comment}")

            commands = self.mapper.get_comment_commands(comment, user)
            if commands:
                await self.rcon.execute_batch(commands)

        @self.client.on(GiftEvent)
        async def on_gift(event: GiftEvent) -> None:
            user = event.user.nickname or event.user.unique_id or "Anonimo"
            gift_name = getattr(event.gift, "name", "Unknown")
            gift_id = getattr(event.gift, "id", 0)
            repeat_count = getattr(event, "repeat_count", 1) or 1
            is_streakable = getattr(event.gift, "streakable", False)
            is_streaking = getattr(event, "streaking", False)

            # En regalos con racha (streakable, ej. Rosas), esperamos a que termine el combo
            # para no ejecutar el comando duplicado en cada clic intermedio de la racha.
            if is_streakable and is_streaking:
                return

            logger.info(f"[GIFT] {user} envió {repeat_count}x '{gift_name}' (ID: {gift_id})")

            commands = self.mapper.get_gift_commands(
                gift_name=gift_name,
                gift_id=gift_id,
                user=user,
                count=repeat_count,
            )
            if commands:
                await self.rcon.execute_batch(commands)

        @self.client.on(LikeEvent)
        async def on_like(event: LikeEvent) -> None:
            user = event.user.nickname or event.user.unique_id or "Anonimo"
            like_count = getattr(event, "count", 1) or 1

            commands = self.mapper.process_likes(like_count=like_count, user=user)
            if commands:
                await self.rcon.execute_batch(commands)

        @self.client.on(FollowEvent)
        async def on_follow(event: FollowEvent) -> None:
            user = event.user.nickname or event.user.unique_id or "Anonimo"
            logger.info(f"[FOLLOW] ¡{user} ha comenzado a seguir el canal!")

            commands = self.mapper.get_follow_commands(user=user)
            if commands:
                await self.rcon.execute_batch(commands)

    async def start(self) -> None:
        """Inicia la conexión con Minecraft RCON y mantiene un bucle resiliente hacia TikTok Live."""
        logger.info("Iniciando puente TikTok Live <-> Minecraft...")
        await self.rcon.connect()

        reconnect_delay = 10
        try:
            while True:
                try:
                    logger.info(f"Intentando conectar al stream de TikTok de {self.username}...")
                    await self.client.start()
                    # En TikTokLive v6+, client.start() puede lanzar una tarea o esperar hasta desconexión;
                    # si retorna de inmediato con el cliente conectado, esperamos mientras siga activo.
                    while getattr(self.client, "connected", False):
                        await asyncio.sleep(2)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error(
                        f"Conexión con TikTok Live interrumpida o el usuario no está en vivo: {exc}. "
                        f"Reintentando en {reconnect_delay} segundos..."
                    )
                await asyncio.sleep(reconnect_delay)
        finally:
            await self.rcon.disconnect()


# =====================================================================
# PUNTO DE ENTRADA (MAIN)
# =====================================================================
async def main() -> None:
    # Cargar variables desde el archivo .env si existe
    load_dotenv()

    tiktok_username = os.getenv("TIKTOK_USERNAME", "@tu_usuario_tiktok").strip()
    rcon_host = os.getenv("RCON_HOST", "127.0.0.1").strip()
    rcon_port = int(os.getenv("RCON_PORT", "25575"))
    rcon_password = os.getenv("RCON_PASSWORD", "minecraft123")
    target_player = os.getenv("MC_TARGET_PLAYER", "@p").strip()

    if tiktok_username in ("@tu_usuario_tiktok", "tu_usuario_tiktok", ""):
        logger.warning(
            "⚠️ No has configurado 'TIKTOK_USERNAME' en tu archivo .env. "
            "Edita el archivo .env con el usuario real del streamer."
        )

    config_path = Path(__file__).parent / "events_config.json"

    rcon_client = AsyncMinecraftRCON(host=rcon_host, port=rcon_port, password=rcon_password)
    event_mapper = EventMapper(config_path=config_path, default_player=target_player)
    bridge = TikTokMinecraftBridge(
        tiktok_username=tiktok_username,
        rcon_client=rcon_client,
        mapper=event_mapper,
    )

    await bridge.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Puente detenido manualmente por el usuario (Ctrl+C).")
