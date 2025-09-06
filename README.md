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

### Switches de Componentes
Habilita/deshabilita según tu setup:
```bash
ENABLE_EL=true           # Execution Layer (Geth/Nethermind/Besu)
ENABLE_BN=true           # Beacon Node 
ENABLE_VC=true           # Validator Client
ENABLE_NODE_EXPORTER=true # Métricas del sistema
```

### Umbrales de Alertas
Personaliza cuándo recibir alertas:
```bash
HOST_MEM_THRESHOLD=90    # % RAM
HOST_DISK_THRESHOLD=90   # % Disco  
HOST_CPU_THRESHOLD=90    # % CPU
BN_PEERS_THRESHOLD=30    # Peers mínimos Beacon Node
GETH_PEERS_THRESHOLD=25  # Peers mínimos Execution Layer
```

## 🚨 Alertas Automáticas

El bot enviará alertas automáticamente por:

**Críticas** (inmediatas):
- Validator Client caído
- Beacon Node caído  
- Execution Layer caído
- Validator sin publicar attestations

**Advertencias** (5-10 min):
- Pocos peers conectados
- Uso alto de CPU/RAM/Disco

## 📊 Compatibilidad de Clientes

### Execution Layer
| Cliente | Puerto por Defecto | Path | Config |
|---------|-------------------|------|--------|
| **Geth** | 6060 | `/debug/metrics` | `--metrics --metrics.port 6060` |
| **Nethermind** | 6060 | `/metrics` | `--Metrics.Enabled=true --Metrics.Port=6060` |
| **Besu** | 9545 | `/metrics` | `--metrics-enabled --metrics-port=9545` |

### Beacon Node
| Cliente | Métricas | REST API | Config |
|---------|----------|----------|--------|
| **Lighthouse** | 5054 | 5052 | `--metrics --http` |
| **Prysm** | 8080 | 3500 | `--monitoring-host=0.0.0.0` |
| **Teku** | 8008 | 5051 | `--metrics-enabled --rest-api-enabled` |
| **Nimbus** | 8008 | 5052 | `--metrics --rest` |

### Validator Client  
| Cliente | Puerto por Defecto | Config |
|---------|-------------------|--------|
| **Lighthouse** | 5064 | `--metrics` |
| **Prysm** | 8081 | `--monitoring-host=0.0.0.0` |
| **Teku** | 8009 | `--metrics-enabled` |
| **Nimbus** | 8009 | `--metrics` |

## 🐛 Solución de Problemas

### El bot no responde
```bash
# Verifica que el bot esté corriendo
docker-compose logs bot

# Revisa la configuración
cat .env | grep TELEGRAM
```

### No llegan alertas
```bash
# Verifica Alertmanager
docker-compose logs alertmanager

# Comprueba el Chat ID
curl "https://api.telegram.org/bot<TU_TOKEN>/getUpdates"
```

### Métricas no disponibles
```bash
# Testa conexión directa
curl http://127.0.0.1:5054/metrics  # Lighthouse BN
curl http://127.0.0.1:6060/debug/metrics  # Geth

# Revisa configuración de puertos
netstat -tlnp | grep :5054
```

### El comando /nodo muestra "N/A"
1. Verifica que los clientes expongan métricas en los puertos configurados
2. Confirma que `ENABLE_*=true` para los componentes que usas
3. Revisa que los paths sean correctos (`/metrics` vs `/debug/metrics`)

## 📁 Estructura del Proyecto

```
faro-bot/
├── .env.example              # Configuración de ejemplo
├── docker-compose.yml        # Orquestación de servicios
├── bot/
│   ├── Dockerfile            # Bot de Telegram
│   ├── bot.py                # Lógica principal
│   └── requirements.txt      # Dependencias Python
├── prometheus/
│   ├── prometheus.yml.tmpl   # Config de Prometheus
│   ├── entrypoint.sh         # Script de inicio
│   └── rules/
│       └── faro-core.yml.tmpl # Reglas de alertas
└── alertmanager/
    ├── alertmanager.yml.tmpl # Config de alertas
    └── entrypoint.sh         # Script de inicio
```

## 🔒 Seguridad

- El bot solo expone métricas en `127.0.0.1` (localhost)
- No almacena datos sensibles en disco
- Las comunicaciones con Telegram son encriptadas (HTTPS)
- Acceso restringido por Chat ID de Telegram

## 🆘 Soporte

- **Issues**: [GitHub Issues](https://github.com/Faus14/faro-bot/issues)
- **Documentación**: Este README
- **Telegram**: Contacta al desarrollador para soporte

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

**🛡️ Mantén tus validadores seguros con Faro Bot**