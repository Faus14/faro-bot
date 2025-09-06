# 🛡️ Faro Bot - Ethereum Validator Monitoring

Un bot de Telegram completo para monitorear nodos validadores de Ethereum, con alertas automáticas y soporte para múltiples clientes (Geth, Nethermind, Besu, Lighthouse, Prysm, Teku, Nimbus).

## ✨ Características

- 📱 **Control desde Telegram**: Consulta estado de tus nodos desde cualquier lugar
- 🔔 **Alertas automáticas**: Notificaciones en tiempo real por Telegram
- 🎯 **Multi-cliente**: Compatible con todos los principales clientes de Ethereum
- 🔧 **Completamente configurable**: Habilita/deshabilita componentes según tu setup
- 📊 **Monitoreo integral**: Execution Layer, Beacon Node, Validator Client y recursos del sistema
- 🚀 **Fácil instalación**: Docker Compose con configuración automática

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Telegram Bot  │ ←→ │ Prometheus   │ ←→ │ Your Nodes  │
│   (Commands)    │    │ (Metrics)    │    │ EL/BN/VC    │
└─────────────────┘    └──────────────┘    └─────────────┘
         ↑                       ↑
         │              ┌──────────────┐
         └──────────────│ Alertmanager │
                        │ (Alerts)     │
                        └──────────────┘
```

## 🚀 Instalación Rápida

### 1. Clona el repositorio
```bash
git clone https://github.com/Faus14/faro-bot.git
cd faro-bot
```

### 2. Crea tu bot de Telegram

1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Ejecuta `/newbot` y sigue las instrucciones
3. Guarda el **token** que te proporciona (formato: `123456789:ABCdef...`)
4. Obtén tu **Chat ID**:
   - Envía un mensaje a tu bot
   - Ve a: `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   - Busca `"chat":{"id":12345678...}` en la respuesta

### 3. Configuración del .env

Copia el archivo de ejemplo y configúralo:
```bash
cp .env.example .env
nano .env
```

**Configuración mínima obligatoria:**
```bash
# ===== Bot de Telegram (OBLIGATORIO) =====
TELEGRAM_BOT_TOKEN=123456789:ABCdef_tu_token_aqui
ALERTS_CHAT_ID=12345678  # Tu chat ID

# ===== Validador =====
VALIDATOR_INDEX=1234567  # Índice de tu validador en Beaconcha.in
```

### 4. Ajusta según tu stack

#### Para Lighthouse (default):
```bash
ENABLE_EL=true
ENABLE_BN=true  
ENABLE_VC=true

EL_METRICS_HOSTPORT=127.0.0.1:6060
EL_METRICS_PATH=/debug/metrics  # Geth

BN_METRICS_HOSTPORT=127.0.0.1:5054
BN_REST_BASE=http://127.0.0.1:5052

VC_METRICS_HOSTPORT=127.0.0.1:5064
```

#### Para Prysm:
```bash
ENABLE_EL=true
ENABLE_BN=true
ENABLE_VC=true

# Geth/Nethermind/Besu (según uses)
EL_METRICS_HOSTPORT=127.0.0.1:6060
EL_METRICS_PATH=/debug/metrics  # /metrics para Nethermind/Besu

# Prysm Beacon Node
BN_METRICS_HOSTPORT=127.0.0.1:8080
BN_REST_BASE=http://127.0.0.1:3500

# Prysm Validator
VC_METRICS_HOSTPORT=127.0.0.1:8081
```

#### Para Teku:
```bash
ENABLE_EL=true
ENABLE_BN=true
ENABLE_VC=true

# Execution client
EL_METRICS_HOSTPORT=127.0.0.1:6060
EL_METRICS_PATH=/debug/metrics  # o /metrics

# Teku (BN+VC integrado)
BN_METRICS_HOSTPORT=127.0.0.1:8008
BN_REST_BASE=http://127.0.0.1:5051
VC_METRICS_HOSTPORT=127.0.0.1:8008  # Mismo puerto
```

### 5. Arranca el sistema
```bash
docker-compose up -d
```

### 6. Verifica que funciona
Envía `/start` a tu bot en Telegram. Deberías ver el menú de comandos.

## 📱 Comandos del Bot

- `/start` - Menú de ayuda
- `/nodo` - Estado de Execution Layer, Beacon Node y Validator Client
- `/host` - Uso de CPU, RAM y disco del servidor
- `/atesta` - Información de attestations y efectividad del validador
- `/nodes` - Lista de nodos configurados

## 🔧 Configuración Avanzada

**Switches**
```bash
ENABLE_EL=true
ENABLE_BN=true
ENABLE_VC=true
ENABLE_NODE_EXPORTER=true
```

**Umbrales**
```bash
HOST_MEM_THRESHOLD=90
HOST_DISK_THRESHOLD=90
HOST_CPU_THRESHOLD=90
BN_PEERS_THRESHOLD=30
GETH_PEERS_THRESHOLD=25
```

## 🚨 Alertas Automáticas

- **Críticas**: VC caído, BN caído, EL caído, validador sin attestations
- **Advertencias**: pocos peers, CPU/RAM/disco alto

Las alertas se envían a Telegram vía Alertmanager.

## 📊 Compatibilidad

- **EL**: Geth (`/debug/metrics`), Nethermind (`/metrics`), Besu (`/metrics`)
- **BN**: Lighthouse, Prysm, Teku, Nimbus (ajusta puertos en `.env`)
- **VC**: Lighthouse, Prysm, Teku, Nimbus

## 🔄 Reload / cambios en `.env`

- Si cambias valores en `.env`, los servicios necesitan reiniciarse:
```bash
docker compose up -d
```

- Si el cambio es sólo en **umbrales de reglas** (`*_THRESHOLD`), podés hacer reload sin reiniciar:
```bash
curl -X POST http://127.0.0.1:9090/-/reload
curl -X POST http://127.0.0.1:9093/-/reload
```

## 📁 Estructura del Proyecto

```
faro-bot/
├── .env.example
├── docker-compose.yml
├── bot/
│   ├── bot.py
│   ├── Dockerfile
│   └── requirements.txt
├── prometheus/
│   ├── prometheus.yml.src
│   ├── entrypoint.sh
│   └── rules/
│       └── faro-core.yml.src
└── alertmanager/
    ├── alertmanager.yml.src
    └── entrypoint.sh
```

## 🔒 Seguridad

- Métricas expuestas sólo en `127.0.0.1`
- Acceso limitado por `chat_id`
- Comunicación con Telegram encriptada (HTTPS)