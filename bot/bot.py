import os, sqlite3, time, re, shutil
from datetime import datetime
from urllib.parse import urljoin
import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# ===== ENV =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_NAME = os.getenv("BOT_PUBLIC_NAME", "@FaroBot")
BRAND = os.getenv("BRAND_NAME", "Faro")
DEFAULT_EL_URL = os.getenv("DEFAULT_EL_URL", "http://127.0.0.1:6060/debug/metrics")
DEFAULT_BN_REST_BASE = os.getenv("DEFAULT_BN_REST_BASE", "http://127.0.0.1:5052")
DEFAULT_VC_METRICS_URL = os.getenv("DEFAULT_VC_METRICS_URL", "http://127.0.0.1:5064/metrics")
DEFAULT_HOST_METRICS_URL = os.getenv("DEFAULT_HOST_METRICS_URL", "")
HUDI_API_BASE = os.getenv("HUDI_API_BASE", "https://hoodi.beaconcha.in/api/v1")
DB_PATH = "/app/storage.sqlite"
TIMEOUT = 3
HDRS = {"User-Agent": f"{BRAND}-bot/1.0"}

# ===== DB =====
SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
  chat_id TEXT NOT NULL,
  alias   TEXT NOT NULL,
  network TEXT NOT NULL,
  el_url  TEXT NOT NULL,
  bn_rest_base TEXT NOT NULL,
  vc_metrics_url TEXT NOT NULL,
  host_metrics_url TEXT,
  validator_index TEXT,
  validator_pubkey TEXT,
  created_at TEXT,
  UNIQUE(chat_id, alias)
);
"""
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn
with db() as conn:
    conn.execute(SCHEMA); conn.commit()

# ===== helpers =====
def _get(url):
    return requests.get(url, timeout=TIMEOUT, headers=HDRS)

def _find_metric_value(text, pattern):
    m = re.search(pattern, text, re.M)
    return m.group(1) if m else None

def get_geth_peers(url):
    try:
        r = _get(url); r.raise_for_status()
        m = re.search(r"^geth_peers\s+(\d+(?:\.\d+)?)$", r.text, re.M)
        return int(float(m.group(1))) if m else None
    except Exception:
        return None

def bn_peer_count(bn_base):
    try:
        r = _get(urljoin(bn_base, "/eth/v1/node/peer_count")); r.raise_for_status()
        return int(r.json().get("data", {}).get("connected", 0))
    except Exception:
        return None

def bn_is_syncing(bn_base):
    try:
        r = _get(urljoin(bn_base, "/eth/v1/node/syncing")); r.raise_for_status()
        data = r.json().get("data", {})
        val = data.get("is_syncing") if isinstance(data, dict) else r.json().get("is_syncing")
        return bool(val)
    except Exception:
        return None

def vc_up(vc_url):
    try:
        r = _get(vc_url)
        return r.status_code == 200
    except Exception:
        return False

def host_metrics(host_url=None):
    # 1) Node Exporter si se configuró (opcional)
    if host_url:
        try:
            r = _get(host_url); r.raise_for_status(); text = r.text
            mem_total = _find_metric_value(text, r"^node_memory_MemTotal_bytes\s+(\d+)$")
            mem_avail = _find_metric_value(text, r"^node_memory_MemAvailable_bytes\s+(\d+)$")
            ram_pct = round(100 - (int(mem_avail) * 100 / int(mem_total)), 1) if mem_total and mem_avail else None
            fs_size = _find_metric_value(text, r'^node_filesystem_size_bytes\{[^}]*mountpoint="/"[^}]*\}\s+(\d+)$')
            fs_avail = _find_metric_value(text, r'^node_filesystem_avail_bytes\{[^}]*mountpoint="/"[^}]*\}\s+(\d+)$')
            disk_pct = round(100 - (int(fs_avail) * 100 / int(fs_size)), 1) if fs_size and fs_avail else None
            return {"cpu_pct": None, "ram_pct": ram_pct, "disk_root_pct": disk_pct}
        except Exception:
            pass
    # 2) /proc y /
    try:
        meminfo = open("/host/proc/meminfo", "r").read()
        import re as _re
        def _first_int(pat):
            m = _re.search(pat, meminfo, _re.M); return int(m.group(1)) if m else None
        mt = _first_int(r"MemTotal:\s+(\d+)\s+kB")
        ma = _first_int(r"MemAvailable:\s+(\d+)\s+kB")
        ram_pct = round(100 - (ma * 100 / mt), 1) if (mt and ma) else None
        # CPU
        def read_cpu():
            with open("/host/proc/stat") as f:
                parts = f.readline().split()
            idle = int(parts[4]); total = sum(map(int, parts[1:8]))
            return idle, total
        i1, t1 = read_cpu(); time.sleep(0.4); i2, t2 = read_cpu()
        d_total = max(t2 - t1, 1); d_idle = max(i2 - i1, 0)
        cpu_pct = round(100 * (1 - d_idle / d_total), 1)
        # Disco
        usage = shutil.disk_usage("/host")
        disk_pct = round(100 * (1 - usage.free / usage.total), 1)
        return {"cpu_pct": cpu_pct, "ram_pct": ram_pct, "disk_root_pct": disk_pct}
    except Exception:
        return {"cpu_pct": None, "ram_pct": None, "disk_root_pct": None}

def hudi_attestation(validator_index=None, validator_pubkey=None):
    if validator_index:
        base = f"{HUDI_API_BASE}/validator/{validator_index}"
        eff = f"{HUDI_API_BASE}/validator/{validator_index}/attestationefficiency"
    elif validator_pubkey:
        base = f"{HUDI_API_BASE}/validator/{validator_pubkey}"
        eff = f"{HUDI_API_BASE}/validator/{validator_pubkey}/attestationefficiency"
    else:
        return None
    try:
        r1 = requests.get(base, timeout=TIMEOUT, headers=HDRS); r1.raise_for_status()
        data = r1.json().get("data", {})
        last_slot = data.get("lastattestationslot") or data.get("last_attestation_slot")
        status = data.get("status", "?")
        epoch = int(last_slot) // 32 if str(last_slot).isdigit() else None
        r2 = requests.get(eff, timeout=TIMEOUT, headers=HDRS); r2.raise_for_status()
        arr = r2.json().get("data", []); eff_v = arr[0].get("attestation_efficiency") if arr else None
        return {"last_slot": last_slot, "epoch": epoch, "status": status, "efficiency": eff_v}
    except Exception:
        return None

# ===== Handlers =====
HELP = (
    "<b>Comandos</b>\n"
    "/addlocal <alias> <validator_index> — registra un nodo local (EL/BN/VC por defecto)\n"
    "/nodes — lista tus nodos\n"
    "/nodo <alias> — estado VC/BN/EL\n"
    "/host <alias> — CPU/RAM/Disco\n"
    "/atesta <alias> — última attestation + eficiencia\n"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"👋 Bienvenido a <b>{BRAND}</b>.\n\n{HELP}", parse_mode=ParseMode.HTML)

def _insert_local(chat_id, alias, vindex):
    with db() as conn:
        conn.execute(
            "INSERT INTO nodes(chat_id, alias, network, el_url, bn_rest_base, vc_metrics_url, host_metrics_url, validator_index, created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (str(chat_id), alias, "hoodi", DEFAULT_EL_URL, DEFAULT_BN_REST_BASE, DEFAULT_VC_METRICS_URL,
             DEFAULT_HOST_METRICS_URL or "", vindex, datetime.utcnow().isoformat())
        ); conn.commit()

async def addlocal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /addlocal <alias> <validator_index>")
        return
    alias, vindex = args[0], args[1]
    try:
        _insert_local(chat_id, alias, vindex)
        await update.message.reply_text(f"✅ Nodo <b>{alias}</b> agregado con endpoints locales.", parse_mode=ParseMode.HTML)
    except sqlite3.IntegrityError:
        await update.message.reply_text("Ese alias ya existe. Usá otro o /nodes para listar.")
        return

def _find_node(chat_id, alias):
    with db() as conn:
        cur = conn.execute("SELECT * FROM nodes WHERE chat_id=? AND alias=?", (str(chat_id), alias))
        return cur.fetchone()

def _list_nodes(chat_id):
    with db() as conn:
        return conn.execute("SELECT alias, network FROM nodes WHERE chat_id=? ORDER BY alias", (str(chat_id),)).fetchall()

async def nodes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = _list_nodes(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("No tenés nodos. Usá /addlocal <alias> <validator_index>.")
        return
    await update.message.reply_text("\n".join([f"• <b>{a}</b> — {n}" for a, n in rows]), parse_mode=ParseMode.HTML)

async def nodo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /nodo <alias>")
        return
    alias = context.args[0]
    row = _find_node(update.effective_chat.id, alias)
    if not row:
        await update.message.reply_text("Alias no encontrado. /nodes para listar.")
        return
    (_chat, _alias, network, el_url, bn_base, vc_url, host_url, vindex, vpub, created_at) = row
    vc = vc_up(vc_url); bn_peers = bn_peer_count(bn_base); syncing = bn_is_syncing(bn_base); el_peers = get_geth_peers(el_url)
    lines = [f"🔎 Nodo <b>{alias}</b> ({network})"]
    lines.append(f"{'✅' if vc else '❌'} VC: {'OK' if vc else 'DOWN'}")
    lines.append(f"✅ BN: peers {bn_peers if bn_peers is not None else '?'} • sincronizado {'No' if syncing else 'Sí' if syncing is not None else '?'}")
    lines.append(f"✅ EL: peers {el_peers if el_peers is not None else '?'}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def host_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /host <alias>")
        return
    alias = context.args[0]
    row = _find_node(update.effective_chat.id, alias)
    if not row:
        await update.message.reply_text("Alias no encontrado. /nodes para listar.")
        return
    (_chat, _alias, _network, _el, _bn, _vc, host_url, *_rest) = row
    m = host_metrics(host_url or None)
    cpu = f"{m['cpu_pct']}%" if m['cpu_pct'] is not None else "?%"
    ram = f"{m['ram_pct']}%" if m['ram_pct'] is not None else "?%"
    dsk = f"{m['disk_root_pct']}%" if m['disk_root_pct'] is not None else "?%"
    await update.message.reply_text(f"🖥️ CPU {cpu} • RAM {ram} • Disco {dsk}")

async def atesta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /atesta <alias>")
        return
    alias = context.args[0]
    row = _find_node(update.effective_chat.id, alias)
    if not row:
        await update.message.reply_text("Alias no encontrado. /nodes para listar.")
        return
    (_chat, _alias, _network, *_urls, _host, vindex, vpub, _created) = row
    data = hudi_attestation(validator_index=vindex, validator_pubkey=vpub)
    if not data:
        await update.message.reply_text("No pude obtener datos de Hoodi.")
        return
    eff = data.get("efficiency"); eff_pct = f"{round(eff*100,1)}%" if isinstance(eff, (int,float)) else "N/A"
    epoch = data.get("epoch"); slot = data.get("last_slot"); status = data.get("status")
    txt = (f"📡 Atestaciones — <b>{alias}</b>\n"
           f"• Última: epoch {epoch if epoch is not None else '?'} • slot {slot} — {status}\n"
           f"• Eficiencia: {eff_pct}")
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def main():
    if not TOKEN:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en .env")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("addlocal", addlocal))
    app.add_handler(CommandHandler("nodes", nodes_cmd))
    app.add_handler(CommandHandler("nodo", nodo_cmd))
    app.add_handler(CommandHandler("host", host_cmd))
    app.add_handler(CommandHandler("atesta", atesta_cmd))
    await app.initialize(); await app.start(); await app.updater.start_polling(); await app.updater.idle()

if __name__ == "__main__":
    import asyncio; asyncio.run(main())
