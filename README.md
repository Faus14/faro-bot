# 🌐 Faro — Bot de Telegram + Alertas para Validadores

Faro es un bot de Telegram que corre en el mismo servidor que tu validador y permite:

- `/nodo <alias>` → estado del nodo: VC/BN/EL (up/down, peers, sync)
- `/host <alias>` → CPU, RAM y Disco del servidor (sin Node Exporter)
- `/atesta <alias>` → última attestation + eficiencia (Hoodi / beaconcha.in)

**Alertas opcionales** (Prometheus + Alertmanager → Telegram): RAM alta, disco >90%, peers bajos, VC/BN/EL caídos.

> **Nota:** No necesitas Prometheus ni Grafana para usar los comandos del bot. Las alertas son opcionales (pueden activarse con un perfil de Compose).

## ✅ Quickstart (desde cero)

**Dónde ejecutar:** todos estos comandos se ejecutan en el servidor donde corre tu validador, dentro de una terminal (shell).

```bash
# 1) Clonar
git clone https://github.com/tuusuario/faro-bot.git
cd faro-bot

# 2) Variables
cp .env.example .env
nano .env   # pegá tu TELEGRAM_BOT_TOKEN y (opcional) ALERTS_CHAT_ID

# 3) Levantar sólo el bot (comandos /nodo, /host, /atesta)
docker compose up -d --build
docker compose logs -f bot   # ver progreso (Ctrl+C para salir)
```

En Telegram, háblale a tu bot:

```
/start
/addlocal VPS01 1212617
/nodo VPS01
/host VPS01
/atesta VPS01
```

Si luego querés activar alertas, seguí la sección "Activar alertas (opcional)" más abajo.

## 🤖 Crear tu bot en Telegram (BotFather)

1. Abrí [@BotFather](https://t.me/botfather)
2. Enviá `/newbot`
3. Elegí nombre y username (debe terminar en `bot`, ej.: `@FaroSentinelBot`)
4. Copiá el **TOKEN** que te da BotFather (formato `123456:ABC...`)
5. Pegalo en `.env` como:
   ```
   TELEGRAM_BOT_TOKEN=TU_TOKEN
   ```

**chat_id para Alertmanager** (si vas a usar alertas): Mandá un mensaje a [@RawDataBot](https://t.me/rawdatabot) o a tu bot y copiá el `chat.id`. Ponelo en `.env` como `ALERTS_CHAT_ID=`.

## ⚙️ Requisitos en tu nodo (métricas locales)

Para que el bot lea estado local, asegurate de habilitar métricas/REST:

### Geth (Execution)

**Flags del servicio:**
```bash
--metrics --metrics.addr 127.0.0.1 --metrics.port 6060
```

**Prueba rápida:**
```bash
curl -s http://127.0.0.1:6060/debug/metrics | grep '^geth_peers '
```

### Lighthouse — Beacon Node (REST)
```bash
--http --http-address 127.0.0.1 --http-port 5052
```

**Prueba:**
```bash
curl -s http://127.0.0.1:5052/eth/v1/node/peer_count
```

### Lighthouse — Validator Client (metrics)
```bash
--metrics --metrics-address 127.0.0.1 --metrics-port 5064
```

**Prueba:**
```bash
curl -s http://127.0.0.1:5064/metrics | head
```

**Host:** Como el bot corre en el mismo servidor, `/host` usa `/proc` y `/` del host (no hace falta Node Exporter).

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

## 🔧 Variables de entorno (.env)

```bash
# ===== Bot de Telegram =====
TELEGRAM_BOT_TOKEN=   # <— obligatorio
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
ALERTS_ENABLED=false          # true para activar servicios de alertas
ALERTS_CHAT_ID=               # ej. 5184123209 (tu chat o grupo de Telegram)
```

## 🐳 Docker Compose

- **Dónde está:** `docker-compose.yml` en la raíz del proyecto
- **Qué hace:** levanta el bot (siempre). Y, si activás alertas, levanta Prometheus y Alertmanager usando el perfil `alerts`

**Puntos clave:**
- `network_mode: host` → el contenedor del bot accede a `127.0.0.1:5052/5064/6060`
- Volúmenes `/proc` y `/` en solo lectura → `/host` sin Node Exporter
- Prometheus y Alertmanager también usan `network_mode: host` (puertos 9090 y 9093)

## 📜 Comandos del bot (MVP)

- `/start` → ayuda
- `/addlocal <alias> <validator_index>` → registra nodo local con defaults (EL/BN/VC)
- `/nodes` → lista nodos
- `/nodo <alias>` → VC/BN/EL (up/down, peers, sync)
- `/host <alias>` → CPU, RAM, Disco del servidor
- `/atesta <alias>` → última attestation + eficiencia (Hoodi)

## 🔔 Activar alertas (opcional)

**Qué incluye:** reglas para validator/BN/EL/host; Alertmanager con envío a Telegram.

**Prerrequisitos:** poner `TELEGRAM_BOT_TOKEN` (obligatorio) y `ALERTS_CHAT_ID` en `.env`.

### Validar reglas (opcional pero recomendado)

**Dónde ejecutarlo:** en la raíz del proyecto (directorio `faro-bot/`).

```bash
docker run --rm -v $(pwd)/prometheus/rules:/rules prom/prometheus \
  promtool check rules /rules/faro-core.yml
```

### Activar el perfil de alertas

**Dónde ejecutarlo:** en la raíz del proyecto.

```bash
# habilitar el flag en .env
sed -i 's/^ALERTS_ENABLED=.*/ALERTS_ENABLED=true/' .env

# levantar servicios con el perfil 'alerts'
docker compose --profile alerts up -d
```

### Ver Prometheus y Alertmanager en salud

**Dónde ejecutarlo:** en la raíz del proyecto.

```bash
# listar grupos de reglas activos en Prometheus
curl -s http://127.0.0.1:9090/api/v1/rules | jq '.data.groups[].name'

# ver salud de Alertmanager
curl -s http://127.0.0.1:9093/-/healthy
```

> **Importante:** `prometheus/prometheus.yml` ya trae `scrape_configs` apuntando a `127.0.0.1` (geth/lighthouse/VC). Si tus puertos son distintos, ajustá ese archivo y reiniciá el servicio de Prometheus del compose.

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