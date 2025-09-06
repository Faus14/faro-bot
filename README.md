# 🌐 Faro — Bot de Telegram + Alertas para Validadores

Faro es un bot de Telegram que corre en el mismo servidor que tu validador y permite:

- `/nodo <alias>` → estado del nodo: VC/BN/EL (up/down, peers, sync)
- `/host <alias>` → CPU, RAM y Disco del servidor (sin Node Exporter)
- `/atesta <alias>` → última attestation + eficiencia (Hoodi / beaconcha.in)

**Alertas opcionales** (Prometheus + Alertmanager → Telegram): RAM alta, disco >90%, peers bajos, VC/BN/EL caídos.

> **Nota:** No necesitas Prometheus ni Grafana para usar los comandos del bot. Las alertas son opcionales (pueden activarse con un perfil de Compose).

## 📋 Requisitos previos

### 1. 🤖 Crear tu bot en Telegram (BotFather) - OBLIGATORIO

**Este paso es obligatorio para que Faro funcione:**

1. Abrí [@BotFather](https://t.me/botfather)
2. Enviá `/newbot`
3. Elegí nombre y username (debe terminar en `bot`, ej.: `@FaroSentinelBot`)
4. Copiá el **TOKEN** que te da BotFather (formato `123456:ABC...`)
5. Guardá este token, lo vas a necesitar en el `.env`

### 2. ⚙️ Configurar métricas en tu nodo

Para que el bot lea estado local, asegurate de habilitar métricas/REST:

#### Geth (Execution)
**Flags del servicio:**
```bash
--metrics --metrics.addr 127.0.0.1 --metrics.port 6060
```

**Prueba rápida:**
```bash
curl -s http://127.0.0.1:6060/debug/metrics | grep '^geth_peers '
```

#### Lighthouse — Beacon Node (REST)
```bash
--http --http-address 127.0.0.1 --http-port 5052
```

**Prueba:**
```bash
curl -s http://127.0.0.1:5052/eth/v1/node/peer_count
```

#### Lighthouse — Validator Client (metrics)
```bash
--metrics --metrics-address 127.0.0.1 --metrics-port 5064
```

**Prueba:**
```bash
curl -s http://127.0.0.1:5064/metrics | head
```

**Host:** Como el bot corre en el mismo servidor, `/host` usa `/proc` y `/` del host (no hace falta Node Exporter).

### 3. 📱 Obtener chat_id para alertas (OPCIONAL)

**Solo si vas a usar alertas:** Mandá un mensaje a [@RawDataBot](https://t.me/rawdatabot) o a tu bot y copiá el `chat.id`. Lo vas a necesitar para `ALERTS_CHAT_ID` en el `.env`.

## 📇 Dato requerido: `validator_index`

Para usar `/atesta` y ver la efectividad/última attestation, Faro necesita saber **qué validador** consultar.
Cuando registres tu nodo con `/addlocal`, **debes pasar el `validator_index`**:

```
/addlocal <alias> <validator_index>
ejemplo:
/addlocal VPS01 1212617
```

> Si tenés **varios validadores**, repetí `/addlocal` con un alias distinto por cada uno.

### 🔎 ¿Cómo obtengo mi `validator_index`?

Elegí cualquiera de estos métodos:

**A) Desde tu Beacon Node (REST) — usando tu pubkey**
1. Tomá tu `validator_pubkey` (0x…)
2. Ejecutá en el servidor (BN en 127.0.0.1:5052):
   ```bash
   curl -s "http://127.0.0.1:5052/eth/v1/beacon/states/head/validators?id=0xTU_PUBLIC_KEY" | jq -r '.data[0].index'
   ```

El número devuelto es tu `validator_index`.

**B) Vía beaconcha.in / Hoodi (web)**
1. Buscá tu **pubkey** o **address** en el explorador (beaconcha.in / tu instancia Hoodi).
2. Abrí la página del validador → ahí verás el **Index** (número entero).

**C) Si corrés Lighthouse y conocés el key store**
* Podés listar tus validadores y sus pubkeys con Lighthouse; luego usa el método (A) para convertir **pubkey → index**.

**D) Desde un dump/archivo propio**
* Si guardás el mapping pubkey ↔ index, tomá el **index** directamente desde ahí.

✅ **Recomendado:** verificá que el índice es correcto ejecutando `/atesta <alias>`; deberías ver `epoch`, `slot` y `eficiencia`.

## ✅ Instalación y configuración

**Dónde ejecutar:** todos estos comandos se ejecutan en el servidor donde corre tu validador, dentro de una terminal (shell).

```bash
# 1) Clonar el repositorio
git clone https://github.com/Faus14/faro-bot.git
cd faro-bot

# 2) Configurar variables de entorno
cp .env.example .env
nano .env   # configurá tu TELEGRAM_BOT_TOKEN (OBLIGATORIO) y opcionalmente ALERTS_CHAT_ID
```

### 🔧 Variables de entorno (.env)

```bash
# ===== Bot de Telegram =====
TELEGRAM_BOT_TOKEN=   # <— OBLIGATORIO - sin esto no funciona nada
BOT_PUBLIC_NAME=@FaroBot
BRAND_NAME=Faro

# ===== Endpoints locales por defecto =====
DEFAULT_EL_URL=http://127.0.0.1:6060/debug/metrics
DEFAULT_BN_REST_BASE=http://127.0.0.1:5052
DEFAULT_VC_METRICS_URL=http://127.0.0.1:5064/metrics
# Si lo dejás vacío, /host usa /proc y / (no hace falta Node Exporter)
DEFAULT_HOST_METRICS_URL=

# ===== Hoodi API (para /atesta) =====
HUDI_API_BASE=https://hoodi.beaconcha.in/api/v1

# ===== Alertas (Prometheus/Alertmanager) =====
ALERTS_ENABLED=false          # ponelo en true para levantar Prometheus + Alertmanager
ALERTS_CHAT_ID=               # ej. 5184123209 (tu chat o grupo) - OPCIONAL, solo para alertas
```

## 🚀 Ejecutar Faro

### Modo básico (solo comandos del bot)

```bash
# Levantar solo el bot
docker compose up -d --build
docker compose logs -f bot   # ver progreso (Ctrl+C para salir)
```

### Probar en Telegram

En Telegram, háblale a tu bot:

```
/start
/addlocal VPS01 1212617
/nodo VPS01
/host VPS01
/atesta VPS01
```

### Activar alertas (opcional)

Si querés recibir alertas de Prometheus/Alertmanager en Telegram:

#### 1. Validar reglas (recomendado)
```bash
docker run --rm -v $(pwd)/prometheus/rules:/rules prom/prometheus \
  promtool check rules /rules/faro-core.yml
```

#### 2. Habilitar alertas
```bash
# Habilitar el flag en .env
sed -i 's/^ALERTS_ENABLED=.*/ALERTS_ENABLED=true/' .env

# Levantar servicios con el perfil 'alerts'
docker compose --profile alerts up -d
```

#### 3. Verificar salud
```bash
# Listar grupos de reglas activos en Prometheus
curl -s http://127.0.0.1:9090/api/v1/rules | jq '.data.groups[].name'

# Ver salud de Alertmanager
curl -s http://127.0.0.1:9093/-/healthy
```

> **Importante:** `prometheus/prometheus.yml` ya trae `scrape_configs` apuntando a `127.0.0.1` (geth/lighthouse/VC). Si tus puertos son distintos, ajustá ese archivo y reiniciá el servicio de Prometheus del compose.

## 📜 Comandos del bot

- `/start` → ayuda
- `/addlocal <alias> <validator_index>` → registra nodo local con defaults (EL/BN/VC)
- `/nodes` → lista nodos
- `/nodo <alias>` → VC/BN/EL (up/down, peers, sync)
- `/host <alias>` → CPU, RAM, Disco del servidor
- `/atesta <alias>` → última attestation + eficiencia (Hoodi)

## 🐳 Docker Compose

- **Dónde está:** `docker-compose.yml` en la raíz del proyecto
- **Qué hace:** levanta el bot (siempre). Y, si activás alertas, levanta Prometheus y Alertmanager usando el perfil `alerts`

**Puntos clave:**
- `network_mode: host` → el contenedor del bot accede a `127.0.0.1:5052/5064/6060`
- Volúmenes `/proc` y `/` en solo lectura → `/host` sin Node Exporter
- Prometheus y Alertmanager también usan `network_mode: host` (puertos 9090 y 9093)

## 📁 Estructura del proyecto

```
faro-bot/
├─ README.md
├─ .env.example
├─ docker-compose.yml
├─ bot/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ bot.py
├─ prometheus/
│  ├─ prometheus.yml
│  └─ rules/
│     └─ faro-core.yml
└─ alertmanager/
   └─ alertmanager.yml
```

## 🧪 Verificación rápida

### Estado del bot (logs):
```bash
docker compose logs -f bot
```

### Probar endpoints locales manualmente:
```bash
curl -s http://127.0.0.1:6060/debug/metrics | grep '^geth_peers '
curl -s http://127.0.0.1:5052/eth/v1/node/peer_count
curl -s http://127.0.0.1:5064/metrics | head
```

### Probar comandos en Telegram:
```
/addlocal VPS01 1212617
/nodo VPS01
/host VPS01
/atesta VPS01
```

## 🛠️ Troubleshooting

### El bot no arranca
Revisá el token:
```bash
docker compose logs -f bot
```
Debe estar definido `TELEGRAM_BOT_TOKEN` en `.env`.

### /nodo no muestra peers/sync
Verificá puertos locales:
```bash
ss -lntp | egrep ':(5052|5064|6060)\s'
```
Probá con curl como en "Verificación rápida".

### /host devuelve ?%
- Esperá 2–3 s (el cálculo de CPU usa deltas)
- Chequeá montajes de `/proc` y `/` en el compose

### No llegan alertas
1. Validá reglas con `promtool` (comando arriba)
2. Revisá `ALERTS_CHAT_ID` y `TELEGRAM_BOT_TOKEN` en `.env`
3. Mirá salud de AM: `curl -s http://127.0.0.1:9093/-/healthy`
4. **Logs:**
   ```bash
   docker compose logs -f faro_prometheus
   docker compose logs -f faro_alertmanager
   ```

## 🔒 Seguridad

- Faro no maneja claves ni secretos de tu validador
- Endpoints de clientes son locales (`127.0.0.1`); no se exponen a Internet
- Montajes del host son de sólo lectura
- Alertas usan tu bot de Telegram y un `chat_id` (no hay datos sensibles)

## 📜 Créditos / Licencia

MIT / Apache-2.0 (elegí la que prefieras).

"Faro" por SEEDNodes (o tu branding)