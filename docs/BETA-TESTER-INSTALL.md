# LEONES — Manual de instalación para beta testers

> **Objetivo:** preparar un host Linux y ejecutar la primera prueba real de LEONES A01 con Ollama.
>
> **Importante:** este manual produce evidencia nueva. Los valores de otras ejecuciones no deben copiarse como mediciones propias.

## 1. Qué vas a probar

La prueba beta recorre la cadena canónica de LEONES:

```text
selección autorizada
        ↓
runtime gate
        ↓
runner A01
        ↓
Ollama local
        ↓
Qwen 0.5B Q4_K_M
        ↓
A01 + grader
        ↓
medición real
        ↓
artifacts/rc1-effective-execution.json
```

La prueba de referencia de RC1 utilizó:

- modelo: `qwen2.5:0.5b-instruct-q4_K_M`
- runtime: `ollama`
- tarea: `A01`
- comando runtime confiable: `python3 scripts/ollama_a01_runtime.py --model qwen2.5:0.5b-instruct-q4_K_M`

## 2. Requisitos

### Hardware

No se prescribe un hardware concreto para la beta. La finalidad de la prueba es registrar lo que realmente ocurra en tu máquina.

Necesitas suficiente RAM para cargar el modelo y espacio de almacenamiento para Git, Ollama y el modelo.

### Sistema operativo

El flujo soportado para esta beta es **Linux**, preferentemente Ubuntu LTS.

### Software

Necesitas:

- Git
- Python 3
- `python3-venv`
- Ollama
- acceso local a `127.0.0.1:11434`

## 3. Instalar dependencias del sistema

En Ubuntu:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv curl
```

## 4. Instalar Ollama

Instala Ollama siguiendo su instalador oficial para Linux:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Comprueba la instalación:

```bash
ollama --version
```

Si tu sistema no inicia automáticamente el servicio de Ollama, arráncalo con el mecanismo de servicio disponible en tu distribución. Después comprueba que la API responde:

```bash
curl -fsS http://127.0.0.1:11434/api/tags
```

Si el comando devuelve JSON, el servicio está accesible.

## 5. Descargar el modelo de la prueba A01

```bash
ollama pull qwen2.5:0.5b-instruct-q4_K_M
```

Comprueba que está disponible:

```bash
ollama list
```

Debe aparecer el identificador exacto:

```text
qwen2.5:0.5b-instruct-q4_K_M
```

No sustituyas silenciosamente el modelo por otro si quieres reproducir esta prueba.

## 6. Clonar LEONES

```bash
git clone https://github.com/robertosantosx2/LEONES.git
cd LEONES
```

Comprueba que estás en una copia limpia:

```bash
git status --short
```

La salida esperada antes de empezar es vacía.

## 7. Crear el entorno Python

```bash
python3 -m venv .venv
source .venv/bin/activate
python --version
```

RC1 está diseñado para poder ejecutar el runner mediante el Python del entorno virtual:

```bash
.venv/bin/python
```

## 8. Preparar los artefactos de selección

El runner separa deliberadamente la selección del comando confiable del runtime. Para una ejecución beta se necesitan dos entradas:

```text
artifacts/real-a01-selection.json
artifacts/real-a01-runtime-commands.json
```

Estas entradas pertenecen al plan de selección y ejecución de la beta; **no contienen una medición nueva**.

Si estás usando un paquete beta proporcionado por el equipo de LEONES, conserva esos dos archivos exactamente como fueron entregados. No edites el modelo, runtime o comando para intentar mejorar el resultado.

## 9. Ejecutar A01

Con Ollama funcionando y los dos artefactos presentes:

```bash
cd /home/roberto/leones-work/LEONES

.venv/bin/python scripts/run_a01_selected.py \
  --selection artifacts/real-a01-selection.json \
  --runtime-commands artifacts/real-a01-runtime-commands.json \
  --workspace .leones/rc1-effective-execution \
  --out artifacts/rc1-effective-execution.json
```

En una ejecución correcta verás:

```text
A01 status=success evidence=measured -> artifacts/rc1-effective-execution.json
```

**No añadas parámetros ni cambies el comando durante la prueba de referencia.**

## 10. Qué comprobar después

Inspecciona la evidencia producida:

```bash
cat artifacts/rc1-effective-execution.json
```

Comprueba especialmente:

```text
status=reported
 evidence.evidence_type=measured
 evidence.measurement_kind=real
 agentic.outcome.status=success
 agentic.grader.status=passed
 agentic.metrics.measured_tps=<valor nuevo>
 runtime_selection.execution_plans[0].execution_authorized=true
```

Comprueba también que existe un `execution_id` nuevo y un `measured_at` nuevo.

Obtén el hash del artefacto:

```bash
sha256sum artifacts/rc1-effective-execution.json
```

Y conserva el resultado completo para el informe beta.

## 11. Qué NO debes hacer

No:

- reutilices un `execution_id` de otra ejecución;
- copies un `tok/s` publicado y lo presentes como medición propia;
- edites `rc1-effective-execution.json` después de la ejecución;
- cambies el modelo sin registrarlo;
- cambies el runtime sin registrarlo;
- conviertas una estimación en medición;
- ejecutes el benchmark desde otro runner y lo presentes como ejecución RC1;
- publiques credenciales, tokens o información personal en los resultados.

## 12. Si falla

Conserva el error completo. No intentes "arreglar" la evidencia editando el JSON.

Recoge:

```bash
ollama --version
python --version
git rev-parse HEAD
ollama list
curl -fsS http://127.0.0.1:11434/api/tags

git status --short
```

Después guarda:

```bash
cat artifacts/rc1-effective-execution.json
```

si el archivo llegó a generarse.

Para un issue o informe beta incluye:

1. sistema operativo;
2. CPU;
3. RAM;
4. GPU/VRAM si existe;
5. versión de Ollama;
6. commit de LEONES;
7. comando exacto ejecutado;
8. salida completa;
9. artefacto de evidencia, si existe;
10. hash SHA-256 del artefacto.

## 13. Qué significa el resultado

`success` significa que A01 completó correctamente su contrato funcional.

`evidence=measured` significa que el runtime informó una medición real durante la ejecución.

El número `tok/s` es **local a esa ejecución y a esas condiciones**. No debe interpretarse como una promesa universal de rendimiento del modelo.

La selección sigue siendo una decisión previa; la medición física es la evidencia posterior.

## 14. Resultado de referencia de RC1

La ejecución canónica que cerró RC1 produjo:

```text
execution_id=e07822d0-d991-4e9b-985b-b9afea0c13c0
model=qwen2.5:0.5b-instruct-q4_K_M
runtime=ollama
A01=success
grade=passed
measurement_kind=real
measured_tps=53.3795
```

Ese valor es **histórico y no debe copiarse como resultado del beta tester**. Cada máquina y cada ejecución deben producir su propia evidencia.

## 15. Para enviar un resultado beta

Entrega como mínimo:

```text
- nombre/identificador del participante (sin datos personales innecesarios)
- OS
- CPU
- RAM
- GPU/VRAM
- Ollama version
- LEONES commit
- model id
- runtime
- execution_id
- measured_at
- measured_tps
- outcome
- grader status
- SHA-256 del artefacto
```

Si el proyecto proporciona un formulario o issue específico para la campaña beta, utiliza ese canal y adjunta el artefacto sin modificarlo.

## 16. Principio de la beta

La beta no busca demostrar que todas las máquinas obtienen el mismo número. Busca construir **evidencia comparable y reproducible bajo condiciones explícitas**.

> **Ejecuta. Mide. Conserva el artefacto. No inventes el resultado.**

## Referencias

- [`README.md`](../README.md)
- [`docs/completed/RC1-EFFECTIVE-EXECUTION.md`](completed/RC1-EFFECTIVE-EXECUTION.md)
- [`docs/RESULT_SCHEMA.md`](RESULT_SCHEMA.md)
- [`CONTRIBUTING.md`](../CONTRIBUTING.md)
