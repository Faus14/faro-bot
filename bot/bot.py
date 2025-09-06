import os, time, re
import requests
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ===== Env =====
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BOT_NAME = os.getenv("BOT_PUBLIC_NAME", "@FaroBot")
BRAND = os.getenv("BRAND_NAME", "Faro")

DEFAULT_ALIAS = os.getenv("DEFAULT_ALIAS", "LOCAL")
VALIDATOR_INDEX_ENV = os.getenv("VALIDATOR_INDEX", "")

ENABLE_EL = os.getenv("ENABLE_EL", "true").lower() == "true"
ENABLE_BN = os.getenv("ENABLE_BN", "true").lower() == "true"
ENABLE_VC = os.getenv("ENABLE_VC", "true").lower() == "true"

EL_METRICS_HOSTPORT = os.getenv("EL_METRICS_HOSTPORT", "127.0.0.1:6060")
EL_METRICS_PATH = os.getenv("EL_METRICS_PATH", "/debug/metrics")

BN_METRICS_HOSTPORT = os.getenv("BN_METRICS_HOSTPORT", "127.0.0.1:5054")
BN_METRICS_PATH = os.getenv("BN_METRICS_PATH", "/metrics")
BN_REST_BASE = os.getenv("BN_REST_BASE", "http://127.0.0.1:5052")

VC_METRICS_HOSTPORT = os.getenv("VC_METRICS_HOSTPORT", "127.0.0.1:5064")
VC_METRICS_PATH = os.getenv("VC_METRICS_PATH", "/metrics")

HUDI_API_BASE = os.getenv("HUDI_API_BASE", "https://hoodi.beaconcha.in/api/v1")

if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN no está seteado en .env — el bot no puede arrancar.")

DEFAULT_EL_URL = f"http://{EL_METRICS_HOSTPORT}{EL_METRICS_PATH}"
DEFAULT_BN_REST_BASE = BN_REST_BASE
DEFAULT_VC_METRICS_URL = f"http://{VC_METRICS_HOSTPORT}{VC_METRICS_PATH}"

STATE: Dict[str, Any] = {}
if VALIDATOR_INDEX_ENV.strip().isdigit():
    STATE[DEFAULT_ALIAS] = {"validator_index": int(VALIDATOR_INDEX_ENV.strip())}

# ===== HTTP helpers =====
def http_json(url: str, timeout: float = 6.0) -> Optional[dict]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def http_text(url: str, timeout: float = 6.0) -> Optional[str]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception:
        return None

# ===== Host metrics (sin Node Exporter para /host) =====
HOST_PROC = "/host/proc" if Path("/host/proc").exists() else "/proc"
HOST_ROOT = "/host" if Path("/host").exists() else "/"

def cpu_used_pct() -> int:
    try:
        def read_cpu():
            with open(f"{HOST_PROC}/stat", "r") as f:
                parts = f.readline().split()
            vals = list(map(int, parts[1:8]))
            idle = vals[3] + vals[4]
            total = sum(vals)
            return idle, total
        idle1, total1 = read_cpu()
        time.sleep(0.8)
        idle2, total2 = read_cpu()
        dt_idle = idle2 - idle1
        dt_total = total2 - total1
        if dt_total <= 0: return 0
        return int(round((1 - (dt_idle / dt_total)) * 100))
    except Exception:
        return 0

def ram_used_pct() -> int:
    try:
        memtotal = memavail = 0
        with open(f"{HOST_PROC}/meminfo","r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    memtotal = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    memavail = int(line.split()[1])
        if memtotal <= 0: return 0
        return int(round(100 - (memavail / memtotal * 100)))
    except Exception:
        return 0

def disk_used_pct() -> int:
    try:
        s = os.statvfs(HOST_ROOT)
        size = s.f_blocks * s.f_frsize
        free = s.f_bfree * s.f_frsize
        if size <= 0: return 0
        return int(round((1 - (free/size)) * 100))
    except Exception:
        return 0

# ===== Node queries / reachability =====
def vc_status() -> Tuple[str, str]:
    """
    Returns (icon, text): ('ℹ️','N/A') if disabled,
                          ('❌','DOWN') if enabled but unreachable,
                          ('✅','OK') if metrics endpoint responds.
    """
    if not ENABLE_VC:
        return "ℹ️", "N/A"
    txt = http_text(DEFAULT_VC_METRICS_URL, timeout=3)
    return ("✅","OK") if txt else ("❌","DOWN")

def el_status_and_peers() -> Tuple[str, str]:
    """
    Returns (icon+status_text): peers_str and status ('ℹ️ N/A' | '❌ DOWN' | '✅ OK').
    """
    if not ENABLE_EL:
        return "N/A", "ℹ️ N/A"
    txt = http_text(DEFAULT_EL_URL, timeout=3)
    if not txt:
        return "N/A", "❌ DOWN"
    # parse peers
    m = re.search(r"^geth_peers\s+(\d+)", txt, re.M)  # Geth
    if not m: m = re.search(r"^nethermind_peers\s+(\d+)", txt, re.M)  # Nethermind
    if not m: m = re.search(r"^besu_peers\s+(\d+)", txt, re.M)        # Besu
    if not m: m = re.search(r'^"p2p/peers"\s+(\d+)', txt, re.M)       # fallback
    peers = m.group(1) if m else "N/A"
    return peers, "✅ OK"

def bn_status_info() -> Tuple[str, Dict[str, Any]]:
    """
    Returns (status_text, info_dict) where status is:
    'ℹ️ N/A' if disabled,
    '❌ DOWN' if enabled but REST no responde,
    '✅ OK' if REST responde (con peers/sync).
    """
    if not ENABLE_BN:
        return "ℹ️ N/A", {"is_syncing":"N/A", "peers":"N/A", "head_slot":"N/A"}
    js_sync = http_json(f"{DEFAULT_BN_REST_BASE}/eth/v1/node/syncing", timeout=4)
    js_peers = http_json(f"{DEFAULT_BN_REST_BASE}/eth/v1/node/peer_count", timeout=4)
    if not js_sync and not js_peers:
        return "❌ DOWN", {"is_syncing":"N/A", "peers":"N/A", "head_slot":"N/A"}
    out = {"is_syncing":"N/A", "peers":"N/A", "head_slot":"N/A"}
    if js_sync:
        src = js_sync.get("data", js_sync)
        out["is_syncing"] = src.get("is_syncing", "N/A")
        out["head_slot"]  = src.get("head_slot", "N/A")
    if js_peers:
        src = js_peers.get("data", js_peers)
        out["peers"] = src.get("connected", "N/A")
    return "✅ OK", out

# ===== Handlers =====
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"👋 Hola! Soy {BRAND} {BOT_NAME}\n\n"
        "Comandos:\n"
        f"• /nodo [{DEFAULT_ALIAS}] — estado VC/BN/EL\n"
        f"• /host [{DEFAULT_ALIAS}] — CPU/RAM/Disco\n"
        f"• /atesta [{DEFAULT_ALIAS}] — última attestation + eficiencia\n"
        "• /nodes — lista alias (en modo simple verás 1)\n"
    )
    await update.message.reply_text(msg)

def _alias(args) -> str:
    return (args[0].strip() if args else DEFAULT_ALIAS)

async def cmd_nodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not STATE:
        return await update.message.reply_text("No hay validador configurado. Definí VALIDATOR_INDEX en el .env y reiniciá el bot.")
    lines = [f"• {k} → index {v.get('validator_index','?')}" for k,v in STATE.items()]
    await update.message.reply_text("🔖 Nodos registrados:\n" + "\n".join(lines))

async def cmd_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = _alias(context.args)
    if alias not in STATE:
        return await update.message.reply_text(f"Alias '{alias}' no encontrado. Usá /nodes.")
    cpu, ram, dsk = cpu_used_pct(), ram_used_pct(), disk_used_pct()
    await update.message.reply_text(f"🖥️ CPU {cpu}% • RAM {ram}% • Disco {dsk}% (usado)")

async def cmd_nodo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = _alias(context.args)
    if alias not in STATE:
        return await update.message.reply_text(f"Alias '{alias}' no encontrado. Usá /nodes.")

    vc_icon, vc_txt = vc_status()
    bn_txt, bn = bn_status_info()
    el_peers, el_txt = el_status_and_peers()

    # syncing texto
    sync = bn.get("is_syncing", "N/A")
    if str(sync).lower() in ("false","0"): sync_txt = "Sí"
    elif str(sync).lower() in ("true","1"): sync_txt = "No"
    else: sync_txt = "N/A"

    msg = (
        f"{vc_icon} VC: {vc_txt}\n"
        f"{'✅' if bn_txt=='✅ OK' else ('❌' if bn_txt=='❌ DOWN' else 'ℹ️')} BN: {bn_txt.split(' ',1)[1] if ' ' in bn_txt else bn_txt} • "
        f"conexiones {bn.get('peers','N/A')} • sincronizado {sync_txt}\n"
        f"{'✅' if el_txt=='✅ OK' else ('❌' if el_txt=='❌ DOWN' else 'ℹ️')} EL: {el_txt.split(' ',1)[1] if ' ' in el_txt else el_txt} • peers {el_peers}"
    )
    await update.message.reply_text(msg)

async def cmd_atesta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = _alias(context.args)
    node = STATE.get(alias)
    if not node:
        return await update.message.reply_text(f"Alias '{alias}' no encontrado. Usá /nodes.")
    vindex = node.get("validator_index")
    if not isinstance(vindex, int):
        return await update.message.reply_text("Falta VALIDATOR_INDEX en .env (número entero).")
    vjs = http_json(f"{HUDI_API_BASE}/validator/{vindex}", timeout=8)
    if not vjs or "data" not in vjs:
        return await update.message.reply_text("No pude consultar Hoodi para este validador.")
    data = vjs["data"]
    last_slot = data.get("lastattestationslot") or data.get("last_attestation_slot")
    status = data.get("status","N/A")
    epoch = (last_slot // 32) if isinstance(last_slot, int) else "N/A"
    last_slot_txt = last_slot if isinstance(last_slot, int) else "N/A"
    ejs = http_json(f"{HUDI_API_BASE}/validator/{vindex}/attestationefficiency", timeout=8) or {}
    eff_list = ejs.get("data") or []
    eff_val = (eff_list[0].get("attestation_efficiency") if eff_list and isinstance(eff_list, list) else None)
    eff_pct = f"{eff_val*100:.1f}" if isinstance(eff_val,(int,float)) else "N/A"
    eff_x   = f"{eff_val:.3f}"     if isinstance(eff_val,(int,float)) else "N/A"
    link = f"https://hoodi.beaconcha.in/validator/{vindex}"
    text = (
        f"📡 Atestaciones — validador {vindex}\n"
        f"• Última: epoch {epoch} • slot {last_slot_txt} — {status}\n"
        f"• Efectividad: {eff_pct}% ({eff_x}×)\n\n{link}"
    )
    await update.message.reply_text(text)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("nodes",  cmd_nodes))
    app.add_handler(CommandHandler("host",   cmd_host))
    app.add_handler(CommandHandler("nodo",   cmd_nodo))
    app.add_handler(CommandHandler("atesta", cmd_atesta))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
