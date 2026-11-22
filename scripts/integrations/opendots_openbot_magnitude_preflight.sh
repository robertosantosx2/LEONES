#!/usr/bin/env bash
# Read-only preflight for OpenDots + OpenBot computer services + Magnitude.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPENDOTS_DIR="${1:-${OPENDOTS_DIR:-$HOME/.local/share/leones/opendots}}"
ICN_URL="${MAGNITUDE_ICN_URL:-http://127.0.0.1:8080}"
PROXY_URL="${OPENDOTS_MAGNITUDE_URL:-http://127.0.0.1:10101}"
MODEL_ALIAS="${OPENAI_MODEL:-local}"
INSTANCE_ID="${MAGNITUDE_MODEL_INSTANCE_ID:-}"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || fail "falta comando requerido: $1"; }

need curl
need python3

[[ -d "$OPENDOTS_DIR" ]] || fail "no existe el checkout OpenDots: $OPENDOTS_DIR"
[[ -f "$OPENDOTS_DIR/.env" ]] || fail "falta $OPENDOTS_DIR/.env"
[[ -f "$OPENDOTS_DIR/compose.computers.yml" ]] || fail "no existe compose.computers.yml; revisa el checkout OpenDots"
[[ -f "$OPENDOTS_DIR/compose.computers-app.yml" ]] || fail "no existe compose.computers-app.yml; revisa el checkout OpenDots"

PINNED_OPENBOT='b6932d31a8d6e7896c15139dfc27a6c6911deb27'
grep -Fq "$PINNED_OPENBOT" "$OPENDOTS_DIR/compose.computers.yml" || fail "OpenDots no fija la revisión OpenBot auditada ($PINNED_OPENBOT); revisa los cambios antes de continuar"
pass "checkout OpenDots y revisión OpenBot fijada"

python3 - "$OPENDOTS_DIR/.env" "$MODEL_ALIAS" "$PROXY_URL" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlparse

env_path, alias, proxy_url = sys.argv[1:]
values = {}
for raw in Path(env_path).read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    values[key.strip()] = value

def require_any(keys, label):
    if not any(values.get(k, "").strip() for k in keys):
        raise SystemExit(f"FAIL: falta {label} en .env (no se muestran valores secretos)")

require_any(("INTELLIGENCE_API_KEY", "CPK_INTELLIGENCE_API_KEY"), "clave de CopilotKit Intelligence")
require_any(("COMPUTER_SUPERVISOR_TOKEN",), "COMPUTER_SUPERVISOR_TOKEN")
require_any(("COMPUTER_TOKEN",), "COMPUTER_TOKEN")
if values.get("COMPUTER_SUPERVISOR_TOKEN") == values.get("COMPUTER_TOKEN"):
    raise SystemExit("FAIL: COMPUTER_SUPERVISOR_TOKEN y COMPUTER_TOKEN deben ser diferentes")
require_any(("COMPUTER_SUPERVISOR_URL",), "COMPUTER_SUPERVISOR_URL")
if values.get("OPENAI_BASE_URL", "").rstrip("/") != proxy_url.rstrip("/") + "/v1":
    raise SystemExit(f"FAIL: OPENAI_BASE_URL debe apuntar a {proxy_url.rstrip('/')}/v1")
if values.get("OPENAI_MODEL", "") != alias:
    raise SystemExit(f"FAIL: OPENAI_MODEL de OpenDots debe coincidir con alias {alias!r}")
if not values.get("OPENAI_API_KEY", "").strip():
    raise SystemExit("FAIL: falta OPENAI_API_KEY (usa el marcador local documentado; no se enviará al proxy)")
u = urlparse(values["COMPUTER_SUPERVISOR_URL"])
if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost"):
    raise SystemExit("FAIL: esta preflight local exige COMPUTER_SUPERVISOR_URL en loopback HTTP")
print("PASS: variables requeridas presentes; secretos no mostrados; proveedor apunta a la fachada")
if values.get("WEB_SEARCH_PROVIDER", "parallel").strip().lower() != "disabled":
    print("WARN: WEB_SEARCH_PROVIDER no está desactivado; las búsquedas pueden contactar servicios externos.")
telemetry_off = values.get("COPILOTKIT_TELEMETRY_DISABLED", "").strip().lower() == "true" or values.get("DO_NOT_TRACK", "").strip() == "1"
if not telemetry_off:
    print("WARN: no se detecta una desactivación explícita de telemetría CopilotKit.")
if values.get("VOICE_API_KEY", "").strip():
    print("WARN: VOICE_API_KEY está configurada; la voz puede usar un servicio externo.")
if not any(values.get(k, "").strip() for k in ("INTELLIGENCE_API_URL", "INTELLIGENCE_GATEWAY_WS_URL", "INTELLIGENCE_WS_URL")):
    print("WARN: no se puede verificar que CopilotKit Intelligence sea local; revisa la configuración de conexión.")
PY

curl -fsS --max-time 5 "$PROXY_URL/health" | python3 -c '
import json,sys
d=json.load(sys.stdin)
assert d.get("status") == "ok", "proxy no indica status=ok"
print("PASS: fachada LEONES saludable")
'
OPENAI_MODEL="$MODEL_ALIAS" curl -fsS --max-time 5 "$PROXY_URL/v1/models" | OPENAI_MODEL="$MODEL_ALIAS" python3 -c '
import json,os,sys
alias=os.environ.get("OPENAI_MODEL","local")
d=json.load(sys.stdin)
ids=[x.get("id") for x in d.get("data",[]) if isinstance(x,dict)]
assert alias in ids, f"alias {alias!r} no publicado por la fachada"
print("PASS: alias OpenAI publicado")
'

[[ -n "$INSTANCE_ID" ]] || fail "define MAGNITUDE_MODEL_INSTANCE_ID con el ID exacto de la instancia Ready"
MAGNITUDE_MODEL_INSTANCE_ID="$INSTANCE_ID" curl -fsS --max-time 5 "$ICN_URL/v1/models/instances" | MAGNITUDE_MODEL_INSTANCE_ID="$INSTANCE_ID" python3 -c '
import json,os,sys
wanted=os.environ["MAGNITUDE_MODEL_INSTANCE_ID"]
d=json.load(sys.stdin)
items=d.get("instances",[])
i=next((x for x in items if x.get("id")==wanted),None)
assert i is not None, "ID de instancia no encontrado en Magnitude ICN"
assert (i.get("lifecycle") or {}).get("_tag") == "Ready", "instancia Magnitude no está en estado Ready"
print("PASS: instancia Magnitude Ready")
'

SUPERVISOR_URL="$(python3 - "$OPENDOTS_DIR/.env" <<'PY'
import sys
from pathlib import Path
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line=raw.strip()
    if line.startswith("COMPUTER_SUPERVISOR_URL="):
        print(line.split("=",1)[1].strip().strip("\"'"))
        break
PY
)"
curl -fsS --max-time 5 "${SUPERVISOR_URL%/}/health" | python3 -c '
import json,sys
d=json.load(sys.stdin)
assert d.get("docker"), "supervisor no confirma acceso al motor Docker"
print("PASS: supervisor OpenBot saludable")
'
printf '\nPreflight completada. No se ha generado una respuesta del modelo ni ejecutado herramientas de un Dot.\n'
printf 'Siguiente: OPENAI_MODEL=%s bash "%s/scripts/integrations/opendots_magnitude_smoke.sh"\n' "$MODEL_ALIAS" "$ROOT_DIR"
