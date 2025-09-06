#!/bin/sh
set -e

# Render templates con variables de entorno
envsubst < /etc/prometheus/prometheus.yml.tmpl > /etc/prometheus/prometheus.yml
# para las rules usamos 'gomplate'-like con env en alert text; envsubst no procesa {{ }}.
# Pero Prometheus ignora {{ .. }} en 'annotations' y no en expr. Para expr usamos envsubst simple:
envsubst < /etc/prometheus/rules/faro-core.yml.tmpl > /etc/prometheus/rules/faro-core.yml

exec /bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.listen-address=0.0.0.0:9090
