# 🎮 TikTok Live ↔ Minecraft Server Bridge (RCON)

Puente asíncrono en Python (`asyncio`) que conecta un directo de **TikTok Live** con un servidor local o remoto de **Minecraft** mediante el protocolo **RCON**.

---

## 🛠️ 1. Habilitar RCON en el Servidor de Minecraft

1. Abre el archivo `server.properties` en la carpeta de tu servidor de Minecraft.
2. Busca o agrega las siguientes líneas y configúralas así:

```properties
enable-rcon=true
rcon.port=25575
rcon.password=tu_password_rcon_segura
broadcast-rcon-to-ops=false
```

3. **Reinicia tu servidor de Minecraft** para que los cambios surtan efecto (deberías ver en la consola del servidor un mensaje indicando `RCON running on 0.0.0.0:25575`).

---

## 🚀 2. Instalación y Configuración del Script

1. **Crear un entorno virtual (recomendado) e instalar dependencias:**

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configurar variables de entorno:**
   Copia el archivo `.env.example` a `.env` y rellena tus datos:

```powershell
copy .env.example .env
```

Edita `.env`:
```env
TIKTOK_USERNAME=@usuario_del_streamer
RCON_HOST=127.0.0.1
RCON_PORT=25575
RCON_PASSWORD=tu_password_rcon_segura
MC_TARGET_PLAYER=@a
```

3. **Personalizar Eventos (`events_config.json`):**
   Puedes agregar o modificar regalos, comandos de chat, umbrales de likes y recompensas por follow editando `events_config.json` sin tocar el código Python. Variables disponibles en los comandos:
   - `{player}`: Jugador objetivo configurado (`@a`, `@p` o tu Nick).
   - `{user}`: Nombre del espectador de TikTok (sanitizado automáticamente).
   - `{count}`: Cantidad de regalos enviados en combo/racha.
   - `{threshold}`: Umbral de likes alcanzado.

---

## ▶️ 3. Ejecución

Con el servidor de Minecraft encendido y el usuario transmitiendo en TikTok Live, ejecuta:

```powershell
python app.py
```
