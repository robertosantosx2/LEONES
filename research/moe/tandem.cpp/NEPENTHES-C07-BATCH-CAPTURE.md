# NEPENTHES C07 — receta de captura física batch NVTX + Nsight

**Estado:** runbook preparado en GitHub; todavía no ejecutado en el MSI.  
**Autoridad:** \`research/moe/tandem.cpp/NEPENTHES-INDEX.md\` e issue [#212](https://github.com/robertosantosx2/LEONES/issues/212).  
**Objetivo:** obtener, en una única ejecución, el JSONL del productor Tandem.cpp y el SQLite exportado por Nsight Systems, y comprobar el enlace explícito NVTX batch → actividad CUDA con proceso, hilo y ventana únicos.

## 1. Identidad de código que debe conservarse

- Tandem.cpp main / PR #7 fusionada: \`7c4300eb754d94737c6aa8d7ffa0077aac7ddcb9\`.
- Base llama.cpp fijada por el workflow de PR #7: \`f5222f25c18da062ab2b8a2dbbfbf4feae398566\`.
- La CI exacta de PR #7 validó el hook C++17, NVTX opcional, sink JSONL, aplicación de patches y compilación CUDA SM86. No validó captura NVTX física ni overhead.
- Aplicar las capas en este orden, como indica \`tandem.cpp/nepenthes/README.md\`: \`tandem.patch\`, \`nepenthes/runtime.patch\`, y después \`python3 nepenthes/apply_runtime_probes.py LLAMA_CPP_ROOT\`. El applier usa anclas exactas y falla cerrado ante drift.

No aplicar patches sobre un checkout distinto de la base fijada sin reconciliar primero el diff. Construir en un directorio separado; no sobrescribir la instalación existente.

## 2. Build instrumentado SM86

Desde los checkouts ya disponibles, sin descargar otro modelo:

\`\`\`bash
set -euo pipefail

TANDEM_SRC="$HOME/tandem.cpp"
LLAMA_SRC="$HOME/nepenthes-validation/llama.cpp-pr10"
BUILD="$LLAMA_SRC/build-nepenthes-sm86"

git -C "$TANDEM_SRC" checkout 7c4300eb754d94737c6aa8d7ffa0077aac7ddcb9
git -C "$LLAMA_SRC" checkout f5222f25c18da062ab2b8a2dbbfbf4feae398566

git -C "$LLAMA_SRC" apply --check "$TANDEM_SRC/tandem.patch"
git -C "$LLAMA_SRC" apply "$TANDEM_SRC/tandem.patch"
git -C "$LLAMA_SRC" apply --check "$TANDEM_SRC/nepenthes/runtime.patch"
git -C "$LLAMA_SRC" apply "$TANDEM_SRC/nepenthes/runtime.patch"
python3 "$TANDEM_SRC/nepenthes/apply_runtime_probes.py" "$LLAMA_SRC"

cmake -S "$LLAMA_SRC" -B "$BUILD" \
  -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_CURL=OFF \
  -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD" --target llama-server -j2

SERVER_BIN="$BUILD/bin/llama-server"
test -x "$SERVER_BIN"
sha256sum "$SERVER_BIN" "$TANDEM_SRC/tandem.patch" "$TANDEM_SRC/nepenthes/runtime.patch"
\`\`\`

Conservar los SHA-256 y los dos commits en el registro de campaña. Si el checkout local ya tiene un build equivalente, comparar primero sus commits y hashes; no recompilar ni cambiar el build existente innecesariamente.

## 3. Terminal A — iniciar una captura paired obligatoria

El wrapper configura \`NEPENTHES_TRACE_JSONL\` y \`NEPENTHES_RUN_ID\`, inicia Nsight sobre el mismo proceso y después importa el SQLite. **\`NEPENTHES_NVTX=1\` debe estar exportada antes de iniciar el servidor**; sin ella, los marcadores batch permanecen desactivados.

\`\`\`bash
set -euo pipefail

SERVER_BIN="$HOME/nepenthes-validation/llama.cpp-pr10/build-nepenthes-sm86/bin/llama-server"
MODEL_PATH="$HOME/models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf"

test -x "$SERVER_BIN"
test -f "$MODEL_PATH"
nepenthes doctor

export NEPENTHES_NVTX=1
export LLAMA_MOE_CPU=auto

nepenthes run \
  --profile full \
  --nsys required \
  --output "$HOME/NEPENTHES-runs" \
  --name c07-batch-qwen35 \
  -- "$SERVER_BIN" \
     -m "$MODEL_PATH" \
     -c 1024 -np 2 -b 128 -ub 64 -t 8 \
     --host 127.0.0.1 --port 18080
\`\`\`

\`--nsys required\` debe fallar antes del arranque si Nsight no está disponible. El wrapper usa \`nsys profile --trace=cuda,nvtx,osrt --export=sqlite\`; no ejecutar Nsight en una segunda sesión ni combinar capturas de ejecuciones distintas.

## 4. Terminal B — producir batches con más de un miembro

Esperar a que el servidor responda y enviar solicitudes concurrentes al endpoint local. La concurrencia de solicitudes es necesaria para observar al menos un batch con dos o más \`request_id\` distintos.

\`\`\`bash
python3 - <<'PY'
import concurrent.futures
import json
import time
import urllib.request

health = "http://127.0.0.1:18080/health"
for _ in range(90):
    try:
        with urllib.request.urlopen(health, timeout=2) as response:
            if response.status == 200:
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("llama-server no llegó a healthy")

url = "http://127.0.0.1:18080/v1/chat/completions"

def send(i):
    payload = {
        "messages": [{"role": "user", "content": f"NEPENTHES C07 batch probe {i}: explica brevemente la diferencia entre prefill y decode."}],
        "max_tokens": 64,
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        body = response.read()
        return {"request": i, "status": response.status, "bytes": len(body)}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(send, range(8)))

for result in results:
    print(json.dumps(result, sort_keys=True))
if any(item["status"] != 200 for item in results):
    raise SystemExit("una o más solicitudes no terminaron con HTTP 200")
PY
\`\`\`

Cuando las solicitudes hayan terminado, detener el servidor desde la Terminal A con Ctrl-C y dejar que \`nepenthes run\` cierre el sink, drene el JSONL, finalice Nsight y ejecute la importación. No matar procesos GPU ajenos ni borrar artefactos intermedios.

## 5. Verificación del bundle

Seleccionar el bundle recién creado y ejecutar el verificador:

\`\`\`bash
RUN_DIR="$(find "$HOME/NEPENTHES-runs" -mindepth 1 -maxdepth 1 -type d \
  -name '*c07-batch-qwen35*' -printf '%T@ %p\\n' | sort -nr | head -1 | cut -d' ' -f2-)"
test -n "$RUN_DIR"
nepenthes verify "$RUN_DIR"
\`\`\`

Comprobar en el JSON de salida:

- \`ok=true\`, \`checks.nsys_import=true\` y \`checks.correlation_contract=true\`.
- \`acceptance.c07_request=passed\` conserva el gate request-level independiente.
- \`acceptance.c07_batch=passed\` y \`checks.c07_batch_correlation=true\`.
- \`correlation.batch_multi_member_tokens\` es mayor que cero.
- \`batch_gpu_activity_token_ids\` coincide con \`correlation.batch_nvtx_token_ids\`.
- \`batch_gpu_activity_count\` es al menos el número de tokens batch validados.
- \`functional_complete\` seguirá siendo false mientras C08 no tenga su informe paired aceptado. C07 no demuestra overhead.

## 6. Consultas SQLite de auditoría

\`\`\`bash
DB="$RUN_DIR/data/nepenthes-import.sqlite"

sqlite3 "$DB" <<'SQL'
PRAGMA integrity_check;

SELECT nvtx_marker_scope, nvtx_marker_phase,
       COUNT(*) AS marker_rows,
       COUNT(DISTINCT nvtx_correlation_token) AS tokens
FROM nsys_activities
WHERE activity_kind='nvtx_event'
GROUP BY nvtx_marker_scope, nvtx_marker_phase
ORDER BY nvtx_marker_scope, nvtx_marker_phase;

SELECT nvtx_correlation_token,
       SUM(nvtx_marker_phase='start') AS starts,
       SUM(nvtx_marker_phase='end') AS ends
FROM nsys_activities
WHERE activity_kind='nvtx_event' AND nvtx_marker_scope='batch'
GROUP BY nvtx_correlation_token
ORDER BY nvtx_correlation_token;

SELECT batch_attribution_status, batch_attribution_level, COUNT(*)
FROM nsys_activities
WHERE activity_kind IN ('cuda_kernel','cuda_memcpy','cuda_memset')
GROUP BY batch_attribution_status, batch_attribution_level
ORDER BY batch_attribution_status, batch_attribution_level;

SELECT nvtx_marker_scope, nvtx_marker_phase, global_pid,
       json_extract(raw_json,'$.globalTid') AS global_tid,
       nvtx_correlation_token
FROM nsys_activities
WHERE activity_kind='nvtx_event'
ORDER BY start_ns;

SELECT correlation_token, activity_id, request_id, slot_id, task_id,
       batch_attribution_level
FROM nepenthes_batch_activity_membership
ORDER BY correlation_token, activity_id, request_id;
SQL
\`\`\`

La última consulta debe mostrar una relación many-to-many: una actividad CUDA puede aparecer asociada a varios miembros del mismo batch, y cada miembro conserva su \`request_id\`, slot y task. No reducirla a una fila por request ni seleccionar un propietario arbitrario.

Guardar también hashes de los artefactos de origen y del import:

\`\`\`bash
sha256sum \
  "$RUN_DIR/manifest.json" \
  "$RUN_DIR/checksums.sha256" \
  "$RUN_DIR/raw/events.jsonl" \
  "$RUN_DIR/raw/nsys.sqlite" \
  "$RUN_DIR/data/nepenthes-import.sqlite"
\`\`\`

## 7. Interpretación fail-closed

- Sin \`batch.start/end\` en JSONL: comprobar \`NEPENTHES_NVTX=1\`, el build aplicado y la disponibilidad de \`libnvToolsExt.so.1\`. No convertir ausencia de marcadores en correlación inferida.
- Sin pareja NVTX en Nsight: la calibración batch queda incompleta; no compensar con timestamps aproximados.
- Sin dos miembros distintos para algún batch: la ejecución no demuestra batching multi-request; repetir la carga concurrente, manteniendo constantes modelo y configuración.
- Sin actividad CUDA \`windowed\` para un token: revisar proceso, \`globalTid\`, hilo y contención temporal. No relajar el guard ni usar el hilo más cercano.
- Ventanas solapadas, identidad ausente o token discrepante: mantener la actividad no atribuida.

\`windowed\` significa contención temporal única bajo proceso e hilo explícitos; no demuestra causalidad GPU ni propiedad de un kernel por un request. C08 sigue siendo una campaña separada de overhead con al menos tres pares baseline/tratamiento según el INDEX maestro.
