#!/bin/sh
set -e

SRC_CFG="/etc/prometheus/prometheus.yml.src"
DST_CFG="/etc/prometheus/prometheus.yml"
SRC_RULE="/etc/prometheus/rules/faro-core.yml.src"
DST_RULE="/etc/prometheus/rules/faro-core.yml"

mkdir -p /etc/prometheus/rules

# Render genérico: reemplaza cualquier ${VAR} por ENVIRON["VAR"] (si no existe, lo deja igual)
render() {
  in="$1"; out="$2"
  awk '
  {
    line = $0
    # Reemplazar repetidamente todas las ocurrencias ${VAR} (A-Z,0-9,_)
    while (match(line, /\$\{[A-Z0-9_]+\}/)) {
      var = substr(line, RSTART+2, RLENGTH-3)
      val = ENVIRON[var]
      # si la variable no existe en el entorno, se deja el placeholder tal cual
      if (val == "") { val = "${" var "}" }
      line = substr(line, 1, RSTART-1) val substr(line, RSTART+RLENGTH)
    }
    print line
  }' "$in" > "$out"
}

render "$SRC_CFG"  "$DST_CFG"
render "$SRC_RULE" "$DST_RULE"

# Validación
if command -v promtool >/dev/null 2>&1; then
  promtool check config "$DST_CFG"
  promtool check rules  "$DST_RULE"
fi

# Ejecutar Prometheus
exec /bin/prometheus \
  --config.file="$DST_CFG" \
  --storage.tsdb.path=/prometheus \
  --web.listen-address="${PROM_LISTEN}"
