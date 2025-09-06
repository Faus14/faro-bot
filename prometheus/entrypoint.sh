#!/bin/sh
set -e

# Render
envsubst < /etc/prometheus/prometheus.yml.src > /etc/prometheus/prometheus.yml
mkdir -p /etc/prometheus/rules
envsubst < /etc/prometheus/rules/faro-core.yml.src > /etc/prometheus/rules/faro-core.yml

# Validar sintaxis
if command -v promtool >/dev/null 2>&1; then
  promtool check config /etc/prometheus/prometheus.yml
  promtool check rules /etc/prometheus/rules/faro-core.yml
fi

# Run
exec /bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.listen-address="${PROM_LISTEN}"
