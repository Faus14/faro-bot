#!/bin/sh
set -e
envsubst < /etc/alertmanager/alertmanager.yml.src > /etc/alertmanager/alertmanager.yml

# Validar
if command -v amtool >/dev/null 2>&1; then
  amtool check-config /etc/alertmanager/alertmanager.yml
fi

exec /bin/alertmanager \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --storage.path=/alertmanager \
  --web.listen-address="${AM_LISTEN}" \
  --log.level="${AM_LOG_LEVEL}"
