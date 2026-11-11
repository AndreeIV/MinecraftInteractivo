"""
=====================================================================
CONFIGURACIÓN DE EVENTOS TIKTOK LIVE -> MINECRAFT
=====================================================================
¡Aquí puedes pegar tus comandos de Minecraft TAL CUAL salen de cualquier
generador (TikFinity, StreamToEarn, MCStacker, etc.) SIN usar barras "\"!

Solo envuelve cada comando entre r''' y ''' (tres comillas simples).

Variables compatibles automáticamente:
  - Jugador de Minecraft: {player} o {playername}
  - Usuario de TikTok (apodo): {user} o {nickname}
  - Usuario de TikTok (@id): {username} o {uniqueId}
  - Cantidad de regalos/likes: {count} o {repeatCount}
  - Meta de likes: {threshold}
"""

EVENTS_CONFIG = {
    "target_player": "@a",

    # =================================================================
    # 1. REGALOS (GIFTS)
    # =================================================================
    "gifts": {
        "Rose": {
            "description": "Invoca un Zombie personalizado por cada Rosa enviada",
            "scale_with_count": True,
            "max_repeats": 25,
            "commands": [
                r'''execute at {playername} run summon zombie ~5 ~ ~5 {Health:75f,Attributes:[{Name:"generic.max_health",Base:75f},{Name:"generic.movement_speed",Base:0.5f}],ActiveEffects:[{Id:12,Amplifier:0,Duration:2000000,ShowParticles:0b}],CustomNameVisible:1b,CustomName:'{"text":"","extra":[{"text":"{nickname}","color":"aqua","bold":true},{"text":" <3","color":"dark_red","bold":true}]}',HandDropChances:[0.0f,0.0f]}''',
                r'''tellraw @a ["",{"text":"[🌹 TikTok] ","color":"light_purple","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" envió ","color":"white"},{"text":"{count}x Rosa","color":"red"},{"text":" -> ¡Zombie invocado!","color":"gray"}]''',
            ],
        },
        "Rosa": {
            "description": "Alias en español para Rosa",
            "scale_with_count": True,
            "max_repeats": 25,
            "commands": [
                r'''execute at {playername} run summon zombie ~5 ~ ~5 {Health:75f,Attributes:[{Name:"generic.max_health",Base:75f},{Name:"generic.movement_speed",Base:0.5f}],ActiveEffects:[{Id:12,Amplifier:0,Duration:2000000,ShowParticles:0b}],CustomNameVisible:1b,CustomName:'{"text":"","extra":[{"text":"{nickname}","color":"aqua","bold":true},{"text":" <3","color":"dark_red","bold":true}]}',HandDropChances:[0.0f,0.0f]}''',
                r'''tellraw @a ["",{"text":"[🌹 TikTok] ","color":"light_purple","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" envió ","color":"white"},{"text":"{count}x Rosa","color":"red"},{"text":" -> ¡Zombie invocado!","color":"gray"}]''',
            ],
        },
        "GG": {
            "description": "Entrega diamantes al jugador",
            "scale_with_count": False,
            "commands": [
                r'''give {player} minecraft:diamond {count}''',
                r'''tellraw @a ["",{"text":"[💎 TikTok] ","color":"aqua","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" envió ","color":"white"},{"text":"{count}x GG","color":"green"},{"text":" -> +{count} Diamante(s)!","color":"aqua"}]''',
            ],
        },
        "TikTok": {
            "description": "Entrega diamantes al jugador al recibir el regalo TikTok",
            "scale_with_count": False,
            "commands": [
                r'''give {player} minecraft:diamond {count}''',
                r'''tellraw @a ["",{"text":"[💎 TikTok] ","color":"aqua","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" envió ","color":"white"},{"text":"{count}x TikTok","color":"light_purple"},{"text":" -> +{count} Diamante(s)!","color":"aqua"}]''',
            ],
        },
        "Doughnut": {
            "description": "Invoca un Creeper por cada Dona enviada",
            "scale_with_count": True,
            "max_repeats": 10,
            "commands": [
                r'''execute at {player} run summon minecraft:creeper ~ ~ ~ {CustomName:'{"text":"Creeper de {nickname}","color":"green","bold":true}',CustomNameVisible:1b}''',
                r'''tellraw @a ["",{"text":"[🍩 TikTok] ","color":"gold","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" envió una Dona -> ¡Cuidado con el Creeper!","color":"red"}]''',
            ],
        },
    },

    # =================================================================
    # 2. COMENTARIOS DEL CHAT (COMMANDS)
    # =================================================================
    "comments": {
        "!creeper": {
            "cooldown_seconds": 15,
            "commands": [
                r'''execute at {player} run summon minecraft:creeper ~ ~ ~ {CustomName:'{"text":"{nickname}","color":"red"}',CustomNameVisible:1b}''',
                r'''tellraw @a ["",{"text":"[💬 Chat] ","color":"green","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" usó ","color":"white"},{"text":"!creeper","color":"red"}]''',
            ],
        },
        "!velocidad": {
            "cooldown_seconds": 10,
            "commands": [
                r'''effect give {player} minecraft:speed 15 2''',
                r'''tellraw @a ["",{"text":"[💬 Chat] ","color":"green","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" activó super velocidad!","color":"aqua"}]''',
            ],
        },
        "!salto": {
            "cooldown_seconds": 10,
            "commands": [
                r'''effect give {player} minecraft:jump_boost 15 3''',
                r'''tellraw @a ["",{"text":"[💬 Chat] ","color":"green","bold":true},{"text":"{nickname}","color":"yellow"},{"text":" activó super salto!","color":"aqua"}]''',
            ],
        },
    },

    # =================================================================
    # 3. LIKES ACUMULADOS
    # =================================================================
    "likes": {
        "threshold": 5,
        "commands": [
            r'''effect give {player} minecraft:speed 10 1''',
            r'''execute at {player} run particle minecraft:heart ~ ~2 ~ 0.5 0.5 0.5 0.1 15''',
            r'''tellraw @a ["",{"text":"[❤️ Likes] ","color":"red","bold":true},{"text":"¡Llegamos a +{threshold} likes gracias a ","color":"white"},{"text":"{nickname}","color":"yellow"},{"text":"! (¡Velocidad activada!)","color":"green"}]''',
        ],
    },

    # =================================================================
    # 4. NUEVOS SEGUIDORES (FOLLOWS)
    # =================================================================
    "follow": {
        "enabled": True,
        "cooldown_seconds": 5,
        "commands": [
            r'''execute at {playername} run summon zombie ~5 ~ ~5 {Health:150f,Attributes:[{Name:"generic.max_health",Base:150f},{Name:"generic.movement_speed",Base:0.4f}],CustomNameVisible:1b,CustomName:'{"text":"","extra":[{"text":"{nickname}","color":"aqua","bold":true},{"text":" <3","color":"dark_red","bold":true}]}',ArmorItems:[{id:"minecraft:golden_boots",Count:1b,tag:{Enchantments:[{id:"minecraft:projectile_protection",lvl:4}]}},{id:"minecraft:golden_leggings",Count:1b,tag:{Enchantments:[{id:"minecraft:projectile_protection",lvl:4}]}},{id:"minecraft:golden_chestplate",Count:1b,tag:{Enchantments:[{id:"minecraft:projectile_protection",lvl:4}]}},{id:"minecraft:golden_helmet",Count:1b,tag:{Enchantments:[{id:"minecraft:projectile_protection",lvl:4}]}}],ArmorDropChances:[0.0f,0.0f,0.0f,0.0f]}''',
            r'''/title @a title {"text":"¡Ty {nickname}","color":"dark_red","bold":true,"extra":[{"text":" - Spawn Zombie Golden","color":"dark_red","bold":true}]}''',
            r'''tellraw @a ["",{"text":"[⭐ Nuevo Follow] ","color":"gold","bold":true},{"text":"¡Gracias por seguirnos, ","color":"white"},{"text":"{nickname}","color":"yellow"},{"text":"! (+3 Golden Zombies)","color":"gold"}]''',
        ],
    },
    "share": {
        "enabled": True,
        "cooldown_seconds": 5,
        "commands": [
            r'''execute at {player} run summon minecraft:firework_rocket ~ ~1 ~ {LifeTime:20}''',
            r'''give {player} minecraft:golden_apple 5''',
            r'''tellraw @a ["",{"text":"[🔗 Compartido] ","color":"blue","bold":true},{"text":"¡Gracias por compartir, ","color":"white"},{"text":"{nickname}","color":"yellow"},{"text":"! (+5 Manzana Dorada)","color":"gold"}]''',
        ],
    },
}
