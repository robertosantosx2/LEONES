# NEPENTHES — índice de implementación, validación y evidencias

**Corte de estado:** 2026-11-15 (validación histórica Nsight-only real completada).  
**Estado global:** CLI funcional, motor CUDA instrumentado compilado sobre base pinned, primera inferencia real con JSONL del motor y validación E2E de importación Nsight-only sobre captura histórica real completadas. Aún falta la captura emparejada con Nsight, correlación robusta y auditoría de cobertura/overhead de una ejecución instrumentada.


## Inicio rápido: instalar, ejecutar y recoger resultados

> **Estado de distribución:** esta versión del instalador vive dentro del árbol de LEONES. Para instalarla hoy hay que disponer de ese árbol; todavía no existe aquí una distribución autónoma publicada de NEPENTHES que permita instalarlo sin descargar LEONES. La instalación es user-space y no exige clonar ni compilar los motores que se quieran ejecutar. La separación en un repositorio/release independiente es un trabajo posterior.

### 1. Requisitos

- Linux.
- Python 3.10 o superior.
- Un motor ejecutable y sus dependencias habituales.
- Para telemetría NVIDIA: `nvidia-smi` disponible.
- Para capturas CUDA detalladas: Nsight Systems (`nsys`) compatible con el driver y el entorno.
- Para eventos internos: un binario del motor compilado con las sondas NEPENTHES. Un binario normal sigue pudiendo ejecutarse, pero no emite eventos internos.

La instalación no necesita root, no instala drivers ni CUDA y no parchea ni recompila el motor.

### 2. Instalar

Desde la raíz del checkout de LEONES que contiene el instalador:

```bash
./scripts/install_nepenthes.sh
export PATH="$HOME/.local/bin:$PATH"
nepenthes doctor
nepenthes self-test
```

El comando instala el ejecutable en `~/.local/bin/nepenthes` y los recursos en `~/.local/share/nepenthes`. `doctor` comprueba las herramientas y capacidades detectables; `self-test` genera una captura de prueba y comprueba sus artefactos. No sustituyen una ejecución real del motor.

### 3. Ejecutar un motor

Ejemplo con llama.cpp; sustituye las rutas y argumentos por los de tu instalación:

```bash
nepenthes run --profile full --nsys auto -- \
  /ruta/a/llama-server \
  -m /ruta/al/modelo.gguf \
  -c 1024
```

Todo lo que aparece después de `--` es el comando del motor y sus argumentos. NEPENTHES lanza el proceso, conserva su salida estándar y de error en el paquete de sesión, muestrea CPU/RSS del árbol de procesos y recoge telemetría NVIDIA global si `nvidia-smi` está disponible. Propaga el código de salida del motor.

Perfiles disponibles: `smoke` (ligero), `standard` (predeterminado) y `full` (muestreo más frecuente y Nsight automático cuando está disponible). Para controlar Nsight se puede usar `--nsys auto`, `--nsys required` o `--nsys off`. Con `required`, la ejecución falla antes de lanzar el motor si Nsight no está disponible.

**Importante:** NEPENTHES no instrumenta por sí solo el interior de un motor. Los eventos internos requieren un binario compilado con las sondas NEPENTHES. Sin ellas se obtienen únicamente las fuentes de telemetría externas disponibles (host y, si existe, NVIDIA). La disponibilidad de Nsight tampoco garantiza que todas las clases de actividad estén presentes.

### 4. Qué resultados genera

Cada ejecución crea un directorio de sesión (RUN_ID). La ruta concreta se muestra/queda registrada por la ejecución; consérvala como `RUN_DIR`. El paquete puede contener:

| Ruta | Contenido |
|---|---|
| `manifest.json` | Identidad de ejecución, configuración y procedencia |
| `session.log` | Salida y errores del proceso lanzado |
| `environment/` | Datos del entorno recogidos |
| `raw/engine-events.jsonl` | Eventos internos del motor instrumentado, si los emite |
| `raw/host-events.jsonl` | Muestras y eventos del recolector de host |
| `raw/events.jsonl` | Flujo consolidado de eventos, cuando se genera |
| `raw/nsys.sqlite`, `raw/nsys.nsys-rep` | Captura Nsight, si se ha activado y completado |
| `data/samples.csv` | Muestras tabulares |
| `data/observations.sqlite` | Observaciones estructuradas |
| `data/summary.json` | Resumen de la ejecución |
| `data/nsys-import.json`, `data/nepenthes-import.sqlite` | Resultados de importación Nsight, cuando proceda |
| `reports/index.html`, `reports/report.md` | Informe navegable HTML y resumen Markdown |
| `checksums.sha256` | Checksums de los artefactos incluidos |

Los artefactos opcionales solo aparecen cuando su fuente está disponible y la captura se completa. No se deben interpretar archivos ausentes como valores cero ni como evidencia de que una actividad no ocurrió.

### 5. Verificar y recoger el paquete

Usa la ruta real de la sesión creada por NEPENTHES:

```bash
RUN_DIR="/ruta/real/al/RUN_ID"
nepenthes verify "$RUN_DIR"
```

Si la verificación termina correctamente, conserva el directorio completo: incluye manifiesto, datos primarios, informes y checksums. Para compartirlo o archivarlo sin alterar los originales:

```bash
tar -czf "nepenthes-$(basename "$RUN_DIR").tar.gz" \
  -C "$(dirname "$RUN_DIR")" "$(basename "$RUN_DIR")"
sha256sum "nepenthes-$(basename "$RUN_DIR").tar.gz"
```

Entrega preferentemente el archivo comprimido completo, su SHA-256 y el código de salida de `nepenthes verify`. Para análisis técnico, conserva también el modelo/identificador y cuantización, argumentos exactos del motor, versión/commit del binario, perfil de captura y cualquier limitación de Nsight. No compartas pesos del modelo salvo que sea necesario y tengas derecho a distribuirlos.

### 6. Qué se puede concluir

- **Motor instrumentado:** permite analizar eventos internos emitidos por las sondas, además de la telemetría externa disponible.
- **Motor no instrumentado:** permite recoger proceso, host y telemetría NVIDIA global disponible; no permite atribuir eventos internos del motor que no emite.
- **Nsight-only:** permite importar y analizar las actividades presentes en la captura Nsight sin inventar una ejecución NEPENTHES ni correlaciones con JSONL ausente.
- **Informe:** refleja únicamente los datos recogidos. Las métricas globales de `nvidia-smi` son del dispositivo, no necesariamente del proceso; la correlación entre relojes o identificadores distintos solo se declara cuando existe un mecanismo validado.

Consulta [NEPENTHES-CLI.md](NEPENTHES-CLI.md) para las opciones completas y [NEPENTHES-IMPORTER.md](NEPENTHES-IMPORTER.md) para el contrato de importación.


## Resumen ejecutivo

NEPENTHES ya dispone de cuatro bloques de trabajo en LEONES y una integración de instrumentación en Tandem.cpp:

1. Instrumentación universal y sink JSONL en Tandem.cpp (PR #1).
2. Importador LEONES para JSONL + Nsight/CUPTI (PR #151).
3. Instalador user-space, CLI de una línea, captura de host/GPU y paquete de informes (PR #152).
4. Importación histórica Nsight-only con procedencia aislada (PR #153).

Estado remoto de las PR: LEONES #150 sigue abierto y actualmente no es mergeable; #151 está cerrado e integrado en la rama `research/nepenthes-universal-collector-20261115` (no en `main`); #152 y #153 están cerrados e integrados en `main`. Tandem.cpp #1 sigue abierto y sin fusionar. La cadena histórica de desarrollo no debe confundirse con el estado actual de integración.

**Validación física MSI completada hasta ahora:**
- Build CUDA local del motor instrumentado sobre llama.cpp pinned `f5222f25c18da062ab2b8a2dbbfbf4feae398566`, tras aplicar `tandem.patch`, `runtime.patch` y el aplicador determinista de probes.
- Primera inferencia real con Qwen3.5-4B Q4_K_M mediante servidor instrumentado, CPU-only, capturada por `nepenthes run`; 3.683 eventos del motor y 3.117 dentro de la ventana request_start/request_end.
- 49 eventos KV cache dentro de la petición; 2.540 transferencias, 290 kernels y 226 sincronizaciones dentro de la ventana.
- Tiempo de petición monotónico 1,864918 s, consistente con los 1.864,85 ms del servidor; 10 tokens prompt, 16 generados, prefill 21,50 tok/s y decode 10,72 tok/s.
- El `request_id` de todos los eventos de la ventana es 0; la segmentación es temporal y no una correlación robusta por petición.
- Instalación user-space correcta.
- `nepenthes doctor`: entorno detectado correctamente.
- `nepenthes self-test`: correcto; 3 eventos, 1 muestra, HTML, checksums e integridad de eventos válidos.
- Inspección del SQLite Nsight histórico y posterior importación standalone: 151.039 actividades.
- Revalidación E2E desde el `main` de LEONES en `d548a37cc4f05632eba946495ad9d98bdf862c63`: CLI `--nsys-only` con código de salida 0 y destino independiente `qwen35-nsys-only.sqlite` (~90 MiB).
- Auditoría independiente del destino: distribución exacta de las ocho familias CUPTI, 151.039 IDs únicos, pares tabla/actividad únicos, SHA-256 y procedencia coincidentes, cero filas no soportadas, `integrity_check=ok` y `foreign_key_check` vacío.
- Import ID de la revalidación: `qwen35-real-nsys-only-20261115`; `run_id=null`, `jsonl=null`, sin correlación NEPENTHES inventada.
- La fuente Nsight conserva SHA-256 `30df43c0a1b235cc25987e2af87e5cf19e5f900f324c26fa22f28cd83144e4fc`; no se modificó.

**Aún no demostrado:** cobertura de todas las sondas, captura Nsight en la misma ejecución, importación emparejada JSONL+Nsight, correlación request-kernel, medición del overhead y recomendaciones cuantitativas de optimización.

## Fuente de verdad y cambios

| Área | PR / rama | Estado actual |
|---|---|---|
| Instrumentación universal Tandem.cpp | [Tandem.cpp #1](https://github.com/robertosantosx2/tandem.cpp/pull/1), `nepenthes/universal-observability-20261114` | Abierto, sin fusionar |
| Índice y documentación | [LEONES #150](https://github.com/robertosantosx2/LEONES/pull/150), `research/nepenthes-universal-collector-20261115` | Abierto; GitHub informa `mergeable=false` |
| Importador JSONL + Nsight | [LEONES #151](https://github.com/robertosantosx2/LEONES/pull/151), `feat/nepenthes-nsys-importer-20261115` | Fusionado en rama de investigación, no en `main` |
| Instalador y CLI | [LEONES #152](https://github.com/robertosantosx2/LEONES/pull/152), `feat/nepenthes-cli-installer-20261115` | Fusionado en `main` |
| Importador Nsight-only | [LEONES #153](https://github.com/robertosantosx2/LEONES/pull/153), `feat/nepenthes-nsys-only-20261115` | Fusionado en `main` (merge `838de99`); CI 7/7 en HEAD funcional `9e0383e` |

Los siete workflows asociados al HEAD funcional `9e0383e7d84334bb2935c229722c9b7a80ac02af` de LEONES #153 terminaron en `success`. Los commits posteriores de esta rama solo corrigen documentación; GitHub no ha asociado nuevos workflows a esos commits. Los estados de #150, #151 y #152 se indican por separado arriba. CI valida los contratos automatizados, no sustituye las pruebas físicas del motor.

## Estado por capacidad

| Capacidad | Estado | Evidencia / límite |
|---|---|---|
| Contrato de evento universal y sink JSONL | Implementado | Tandem.cpp PR #1; CI success |
| Barrera de apagado y concurrencia del sink | Implementado y probado en CI | No implica captura real MSI |
| Aplicación determinista de sondas en Tandem.cpp | Implementada en el parche | Compilación CUDA CI; falta medir cobertura en ejecución |
| Instalador user-space | Implementado y ejecutado | MSI: instalación correcta en `~/.local` |
| CLI de una línea `nepenthes run` | Implementado y probado con motor instrumentado | Qwen3.5-4B real: JSONL del motor, exit code 0 y 3.683 eventos; Nsight desactivado en esta prueba |
| Doctor y self-test | Ejecutados correctamente | MSI: 3 eventos, 1 muestra, reporte HTML |
| Muestreo CPU/RSS del árbol de procesos | Implementado | Self-test; falta perfil real de motor |
| Muestreo NVIDIA global con nvidia-smi | Implementado | Doctor detecta nvidia-smi; falta captura integral de inferencia |
| Captura Nsight opcional/obligatoria/off | Implementada | Falta ejecutar wrapper real con Nsight en MSI |
| Paquete CSV/JSONL/SQLite/Markdown/HTML/SVG | Implementado; aceptación de inferencia parcial | Captura de motor JSONL real; falta `nepenthes verify` y auditoría completa del paquete de inferencia |
| Verificación de hashes y estructura | Implementada | Self-test correcto; falta `verify` sobre captura real |
| Importador emparejado JSONL + Nsight | Implementado y CI | Falta validar un par real de una misma ejecución |
| Inspección de esquema Nsight | Implementada y ejecutada | MSI: 8 tablas CUPTI reconocidas |
| Importación Nsight-only | Implementada, CI success y E2E histórico real superado | MSI: 151.039 filas; 8/8 tablas CUPTI detectadas importadas; 0 filas no soportadas; auditoría de procedencia, unicidad e integridad correcta |
| Procedencia, hashes y cobertura parcial | Implementado | Import standalone con `run_id=null`, sin JSONL |
| Correlación request-kernel entre relojes | No implementada deliberadamente | Requiere IDs comunes y calibración; no se debe inferir por proximidad |
| Informe histórico Qwen3.5-35B | Construido en documentación | Nsight-only histórico, sin JSONL emparejado |\n| Primera captura Qwen3.5-4B | Capturada; informe de campaña | Inferencia real CPU-only con motor instrumentado; Nsight off; request_id=0 |
| Matriz de cobertura de sondas por ejecución | Parcial | Qwen3.5-4B confirma request, routing, KV, transfer, kernel, sync y allocation; MoE/workers/prefetch/OOM aún no aceptados |
| Batería repetible y comparación entre ejecuciones | Pendiente | Requiere capturas emparejadas y manifiestos |

## Roadmap

El roadmap operativo detallado está en [NEPENTHES-ROADMAP.md](NEPENTHES-ROADMAP.md).

1. **Cerrar el árbol de PRs:** revisión, resolver comentarios y fusionar en orden de dependencias con autorización explícita.
2. **Prueba de extremo a extremo MSI:** `doctor`, `self-test`, `run --profile smoke` con un comando inocuo y después motor instrumentado; verificar logs, exit code y paquete.
3. **Captura real instrumentada:** Qwen3.5 u otro motor Tandem parcheado, JSONL del motor + host + Nsight en el mismo RUN_ID; validar pérdidas y overhead.
4. **Importación emparejada:** validar tablas, hashes, cobertura y límites de correlación en LEONES.
5. **Cobertura de sondas:** matriz para request/graph, KV, MoE cache, workers, prefetch, alloc/free, OOM/fallback y transferencias.
6. **Informes comparativos:** tablas y gráficas con series temporales, kernels, transferencias, memoria y rendimiento, distinguiendo observación, estimación y medición.
7. **Release reproducible:** instalación limpia, pruebas, documentación, manifiesto, checksums y procedimiento de desinstalación/actualización.

## Captura histórica Qwen3.5-35B

Informe completo: [NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md).

La importación Nsight-only del MSI contiene 151.039 actividades:
- kernel 8.982; memcpy 44.488; memset 9; runtime 84.116;
- graph trace 5.207; synchronization 7.864; CUDA event 262; overhead 111.

Cobertura declarada: `complete_for_detected_cupti_tables`, con 8 tablas detectadas, 151.039 filas importadas y cero filas/tablas no soportadas. No significa que todas las categorías que Nsight pudiera producir estén presentes en el archivo. La auditoría independiente confirmó 151.039 IDs únicos, 151.039 pares tabla/actividad únicos, `integrity_check=ok` y `foreign_key_check` vacío. Los 262 CUDA_EVENT tienen `timestamp=0` en el SQLite fuente y en el importado; se conservan como eventos puntuales sin intervalo temporal. No se usan para reconstruir duración.

## Reglas de evidencia

- `CI_PASS` significa que las pruebas automatizadas del commit pasaron.
- `INSTALLED` significa que el instalador terminó en el MSI.
- `SELF_TEST_PASS` significa que el autodiagnóstico produjo su paquete de prueba válido.
- `CAPTURED` exige una ejecución real del motor y artefactos conservados.
- `MEASURED` solo se usa para valores derivados de una captura real identificada.
- `ESTIMATED` nunca se presenta como medida.
- No unir `request_id` con `correlationId` CUPTI ni relojes monotónicos con timestamps Nsight sin un mecanismo demostrado de correlación.
- La utilización/memoria GPU de `nvidia-smi` es device-wide; no atribuirla al proceso sin evidencia.
- Los spans de submission host no son duración de ejecución GPU.
