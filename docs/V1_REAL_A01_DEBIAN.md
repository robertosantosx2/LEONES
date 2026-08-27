# V1 — prueba real A01 en Debian

Esta prueba reutiliza exactamente el camino canónico de V1:

`selector → runtime-selection.v1 → runtime autorizado → A01 → grader → runtime-benchmark.v1 → evidence.v1 → Router`

La diferencia respecto al fixture es que el runtime ahora consulta un modelo local real mediante un endpoint **OpenAI-compatible de loopback**. No se envía el prompt a Internet.

## 1. Actualizar el repositorio

```bash
cd ~/leones-work/LEONES
git pull --ff-only
```

## 2. Comprobar el runtime local

LEONES ya incluye un detector para endpoints locales:

```bash
python3 scripts/leones-runtime.py
```

Debe aparecer al menos un endpoint `reachable: true`. El adaptador incluido usa por defecto:

```text
http://127.0.0.1:8080/v1/chat/completions
```

Si tu servidor utiliza otro puerto, se puede cambiar en `runtime-commands.json`.

## 3. Identificar el modelo

El `model_id` debe ser exactamente el identificador que acepta tu runtime local. Por ejemplo, si `/v1/models` devuelve `Qwen/...`, ese mismo valor debe utilizarse en la selección y en el comando del runtime.

No pongas un valor estimado: el identificador debe proceder del runtime local.

## 4. Crear la selección real

```bash
mkdir -p artifacts .leones/a01-real-workspace

cat > artifacts/real-selector-output.json <<'EOF'
{
  "schema_version": "1.0",
  "candidates": [
    {
      "model_id": "CAMBIA_ESTO_POR_EL_MODEL_ID_REAL",
      "model_name": "CAMBIA_ESTO_POR_EL_NOMBRE_REAL",
      "runtime": "local-openai-compatible",
      "runtime_version": "local",
      "quantization": "local",
      "optimization_families": [],
      "selection_status": "TOP_N",
      "rank": 1,
      "fit_score": 1.0,
      "evidence_level": "estimated",
      "llmfit": {}
    }
  ]
}
EOF
```

## 5. Crear el comando de runtime confiable

Sustituye `MODEL_ID_REAL` por el mismo identificador anterior. El comando se almacena como **argv**, no como shell command.

```bash
cat > artifacts/real-runtime-commands.json <<'EOF'
{
  "local-openai-compatible": [
    "python3",
    "scripts/local/a01_openai_runtime.py",
    "--url",
    "http://127.0.0.1:8080/v1/chat/completions",
    "--model",
    "MODEL_ID_REAL"
  ]
}
EOF
```

## 6. Ejecutar la prueba real

```bash
python3 scripts/a01_runtime_benchmark.py \
  --selection artifacts/real-selector-output.json \
  --runtime-commands artifacts/real-runtime-commands.json \
  --workspace .leones/a01-real-workspace \
  --out artifacts/a01-real-runtime-benchmark.v1.json
```

## 7. Verificación obligatoria

```bash
python3 -m json.tool artifacts/a01-real-runtime-benchmark.v1.json >/dev/null \
  && echo "A01 REAL JSON OK"

python3 - <<'PY'
import json
p = json.load(open("artifacts/a01-real-runtime-benchmark.v1.json", encoding="utf-8"))
b = p["evidence"]["runtime_benchmark"]
r = p["router"]
print("=== A01 REAL ===")
print("status:", b["status"])
print("task:", b["task"])
print("model:", b["model"])
print("runtime:", b["runtime"])
print("grader_pass:", b["grader_pass"])
print("wall_seconds:", b["wall_seconds"])
print("measured_tps:", b["measured_tps"])
print()
print("=== ROUTER ===")
print("decision:", r["decision"])
print("decision_type:", r["decision_type"])
print("primary_evidence.type:", r["primary_evidence"]["type"])
print("runtime_benchmark_measured:", r["primary_evidence"]["runtime_benchmark_measured"])
print("model_match:", r["primary_evidence"]["model_match"])
print("runtime_match:", r["primary_evidence"]["runtime_match"])
PY
```

### Resultado que buscamos

```text
status: measured
runtime: local-openai-compatible
grader_pass: True
...
decision: evidence_supported
runtime_benchmark_measured: True
model_match: True
runtime_match: True
```

`measured_tps` puede seguir siendo `null` si el endpoint no devuelve un contador de tokens compatible. Eso **no debe rellenarse a mano**. La medición de latencia seguirá siendo real; el throughput solo se promociona cuando existe una medición de tokens válida.

## 8. Si falla A01

No se debe modificar el grader para hacer pasar el modelo. El fallo debe diagnosticarse en este orden:

1. `/v1/models` confirma el `model_id`.
2. El runtime responde al endpoint `/v1/chat/completions`.
3. La respuesta contiene exactamente dos JSONL de herramientas.
4. El primer tool call es `lookup_model` con el `model_id` seleccionado.
5. El segundo es `write_report` con `report.txt`.
6. El artefacto queda dentro de `.leones/a01-real-workspace`.
7. El grader pasa.
8. El benchmark y la evidencia se generan.
9. Router recibe la evidencia medida y devuelve `evidence_supported`.

Esta prueba no descarga modelos ni instala runtimes: presupone que el runtime local ya está operativo en Debian.
