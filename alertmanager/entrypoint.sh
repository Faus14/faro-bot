#!/bin/sh
set -e

SRC="/etc/alertmanager/alertmanager.yml.src"
DST="/etc/alertmanager/alertmanager.yml"

render() {
  in="$1"; out="$2"
  VARS="
AM_GROUP_WAIT
AM_GROUP_INTERVAL
AM_REPEAT_INTERVAL
AM_LISTEN
AM_LOG_LEVEL
TELEGRAM_BOT_TOKEN
ALERTS_CHAT_ID
"
  sed_script=""
  for v in $VARS; do
    val="$(printenv "$v")"
    [ -z "$val" ] && val="\${$v}"
    val_esc=$(printf '%s' "$val" | sed -e 's/[\/&]/\\&/g')
    sed_script="$sed_script -e s/\\\${$v}/$val_esc/g"
  done
  # shellcheck disable=SC2086
  eval sed $sed_script -- "$in" > "$out"
}

render "$SRC" "$DST"

# Validación (amtool viene en la imagen prom/alertmanager)
if command -v amtool >/dev/null 2>&1; then
  amtool check-config "$DST"
fi

exec /bin/alertmanager \
  --config.file="$DST" \
  --storage.path=/alertmanager \
  --web.listen-address="${AM_LISTEN}" \
  --log.level="${AM_LOG_LEVEL}"
