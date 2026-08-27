# V1 — prueba real A01 en Debian CPU-only

## Objetivo

Convertir la prueba `fixture-runtime` ya cerrada en una medición real:

`selector → runtime-selection.v1 → Ollama → modelo real → A01 → grader → runtime-benchmark.v1 → evidence.v1 → Router`

La máquina de referencia de esta validación es un portátil con:

- Intel Core i5-1035G1, 8 hilos.
- 8 GiB de RAM instalados; la medición aportada mostró aproximadamente 7 GiB utilizables.
- Intel Iris Plus Graphics G1 integrada.
- Sin NVIDIA GPU/CUDA detectada.
- Aproximadamente 101 GiB libres en `/home`.

Esta máquina se considera **CPU-only para V1**. No se debe instalar un stack CUDA ni tratar la Iris integrada como una GPU de inferencia NVIDIA.

## Runtime de referencia

Para la primera prueba real se utiliza Ollama en `127.0.0.1:11434`. Ollama expone una API local y soporta tool calling. La instalación Linux oficial es:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Si se prefiere ejecutar el servicio manualmente:

```bash
ollama serve
```

En otra terminal se puede comprobar:

```bash
ollama -v
curl -s http://127.0.0.1:11434/api/tags
```

## Modelo de prueba

La primera prueba debe usar un modelo deliberadamente pequeño para no convertir la validación de V1 en una prueba de capacidad máxima de la máquina.

Referencia:

```text
qwen2.5:0.5b-instruct-q4_K_M
```

Su tamaño publicado es aproximadamente 398 MB y corresponde a Q4_K_M. La variante instruct es preferible porque el experimento necesita seguir instrucciones y producir llamadas de herramientas.

## Preparación

Después de instalar Ollama:

```bash
ollama pull qwen2.5:0.5b-instruct-q4_K_M
ollama ps
```

`ollama ps` debe utilizarse como evidencia adicional para confirmar que el modelo está cargado en CPU y no atribuir accidentalmente rendimiento a una GPU.

Antes de la prueba:

```bash
free -h
python3 scripts/leones-runtime.py
```

El último comando debe pasar de `no_runtime` a `ok` y mostrar el endpoint `11434` como alcanzable.

## Prueba directa del puente Ollama → A01

El repositorio contiene `scripts/ollama_a01_runtime.py`, que adapta el tool calling de Ollama al contrato JSONL canónico de A01 y conserva la medición de tokens/segundo reportada por Ollama.

Comprobar primero el puente sin pasar todavía por el selector:

```bash
python3 scripts/ollama_a01_runtime.py \
  --model qwen2.5:0.5b-instruct-q4_K_M \
  'Execute A01. Use the selected model and write the report.'
```

La salida válida debe contener, en este orden:

```json
{"tool":"lookup_model","arguments":{"model_id":"qwen2.5:0.5b-instruct-q4_K_M"}}
{"tool":"write_report","arguments":{"path":"report.txt"}}
{"measured_tps":0.0}
```

El valor `measured_tps` será el real producido por Ollama; el ejemplo `0.0` es solamente ilustrativo.

## Selector real

Crear un selector de prueba real:

```bash
cat > artifacts/real-a01-selection.json <<'EOF'
{
  "schema_version": "1.0",
  "candidates": [
    {
      "model_id": "qwen2.5:0.5b-instruct-q4_K_M",
      "model_name": "qwen2.5:0.5b-instruct-q4_K_M",
      "runtime": "ollama",
      "runtime_version": "local",
      "quantization": "Q4_K_M",
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

Crear el comando confiable:

```bash
cat > artifacts/real-a01-runtime-commands.json <<'EOF'
{
  "ollama": [
    "python3",
    "scripts/ollama_a01_runtime.py",
    "--model",
    "qwen2.5:0.5b-instruct-q4_K_M"
  ]
}
EOF
```

Y ejecutar el camino canónico:

```bash
python3 scripts/a01_runtime_benchmark.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/a01-real-workspace \
  --prompt 'Execute A01. Return only JSONL tool calls.' \
  --out artifacts/a01-real-runtime-benchmark.v1.json
```

## Evidencia que debe quedar

```bash
python3 -m json.tool artifacts/a01-real-runtime-benchmark.v1.json >/dev/null
cat artifacts/a01-real-runtime-benchmark.v1.json
cat .leones/a01-real-workspace/report.txt
```

El cierre de la prueba exige simultáneamente:

- `runtime_benchmark.status == "measured"`.
- `runtime_benchmark.task == "A01"`.
- `runtime_benchmark.grader_pass == true`.
- `runtime_benchmark.runtime == "ollama"`.
- `runtime_benchmark.model` igual al modelo ejecutado.
- `runtime_benchmark.measured_tps` distinto de `null`.
- `router.decision == "evidence_supported"`.
- `router.primary_evidence.runtime_benchmark_measured == true`.
- `router.primary_evidence.model_match == true`.
- `router.primary_evidence.runtime_match == true`.
- `report.txt` contiene el nombre del modelo seleccionado.

## Importante: qué demuestra y qué no demuestra

Esta prueba es una **prueba real CPU-only de integración y medición**, no una afirmación de que el portátil sea adecuado para modelos grandes.

El resultado debe conservar el hardware observado, el modelo exacto, la cuantización, el runtime, el tiempo de pared y los tokens/segundo reportados. No se debe rellenar ningún valor desconocido con una estimación.

La prueba con `fixture-runtime` sigue siendo válida como contrato CI porque no depende de descargar un modelo. La prueba Ollama es la evidencia física de Debian y debe mantenerse separada de la regresión determinista de GitHub Actions.
