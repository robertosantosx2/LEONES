# LEONES Lab Agent

Agente local autocontenido en Rust para diagnóstico, inventario de modelos y herramientas, y preparación de investigación reproducible dentro de LEONES.

**Versión:** 0.5.0.  
**Estado:** inventario de solo lectura por defecto; benchmarks locales solo con autorización explícita.  
**Plataforma:** Linux x86_64 (objetivo inicial).  
**Licencia:** AGPL-3.0-only.

## Requisitos de diseño

- Cero crates externos: el bloque [dependencies] permanece vacío.
- Solo biblioteca estándar de Rust (std) y código propio integrado en el repositorio.
- Sin Python, Node.js ni conexión a Internet; el modo ask solo abre HTTP en loopback (127.0.0.1/localhost).
- Sin lectura de secretos ni archivos .env.
- Sin instalaciones, descargas ni cambios en servicios. La única ejecución de modelos es el benchmark allowlist, bajo `--approve`.
- Inventario basado en evidencia: una ruta o entrada de caché no se presenta como modelo cargable o ejecutado.
- El código no copia ni incorpora código de terceros; incluye implementaciones propias de JSON, HTTP local y SHA-256, por lo que no introduce dependencias de licencia adicionales.

## Compilación de desarrollo

Con Rust estable instalado:

    cargo fmt --check
    cargo test
    cargo build --release

## Compilación estática para Linux x86_64

El objetivo estático utiliza musl:

    rustup target add x86_64-unknown-linux-musl

En Ubuntu se necesita el linker musl:

    sudo apt-get install musl-tools

Después, desde este directorio:

    sh scripts/build-static.sh

El resultado queda en:

    target/x86_64-unknown-linux-musl/release/lab-agent

El script comprueba formato, pruebas, compilación y ausencia de intérprete ELF dinámico. El workflow de GitHub Actions repite estas comprobaciones en un runner Linux limpio. El binario musl no depende de glibc del host. Esto no convierte en estáticas herramientas externas consultadas opcionalmente (por ejemplo nvidia-smi, systemctl o uname); el agente sigue funcionando si faltan, señalando datos no disponibles.

## Comandos

| Comando | Función |
|---|---|
| lab-agent doctor | SO, kernel, CPU, RAM, GPU NVIDIA y CUDA Toolkit |
| lab-agent doctor --json | Diagnóstico en JSON |
| lab-agent engines | Busca ejecutables conocidos en PATH y rutas locales conocidas |
| lab-agent models | Inventario de modelos/cachés conocidos |
| lab-agent models --json | Inventario de modelos en JSON |
| lab-agent inventory --json | Herramientas, modelos y componentes en JSON |
| lab-agent ask [OPCIONES] PREGUNTA | Consulta un LLM local y permite herramientas de inventario de solo lectura |
| lab-agent benchmark [OPCIONES] | Ejecuta llama-bench solo con autorización explícita |
| lab-agent report [RUTA] | Genera un informe Markdown |
| lab-agent version | Versión |

## Asistente local

El comando ask se conecta a un servidor compatible con OpenAI Chat Completions que escuche en loopback. No acepta HTTPS ni hosts remotos y no envía claves API. Ejemplo:

    lab-agent ask --endpoint http://127.0.0.1:8080/v1/chat/completions --model Qwen3.5-4B "Resume el hardware y los modelos disponibles"

El agente puede solicitar tres herramientas integradas: get_system_info, get_local_inventory y get_detected_tools. No existe herramienta de shell ni ejecución arbitraria. Las llamadas están limitadas a cuatro rondas por consulta. El servidor de inferencia debe estar iniciado por el usuario; Lab Agent no lo arranca ni carga modelos.

La implementación HTTP y el parser/serializador JSON están escritos en el propio proyecto y usan exclusivamente std. Esta primera interfaz solo soporta HTTP local sin TLS; no se conecta a Gemini ni a proveedores remotos.

## Benchmarks supervisados

El comando benchmark permite ejecutar exclusivamente llama-bench sobre un GGUF local. Primero realiza un dry-run y muestra el comando exacto; no ejecuta nada sin `--approve`:

    lab-agent benchmark --model /ruta/modelo.gguf --prompt-tokens 512 --gen-tokens 128 --repetitions 3
    lab-agent benchmark --model /ruta/modelo.gguf --approve

Límites: prompt/generación hasta 4096 tokens, 1–5 repeticiones y timeout de 30–1800 segundos. Comprueba la cabecera GGUF, no usa shell, limpia el entorno del proceso y solo conserva variables técnicas explícitas (PATH, HOME, LD_LIBRARY_PATH, CUDA_VISIBLE_DEVICES, CUDA_HOME y OMP_NUM_THREADS). No pasa tokens ni claves API.

Cada ejecución aprobada calcula SHA-256 del GGUF mediante una implementación streaming integrada y crea un directorio nuevo bajo `experiments/` con `manifest.json`, `stdout.json` y `stderr.log`. El estado `MEASURED` solo se asigna si el proceso termina correctamente y el JSON contiene métricas `avg_ts`, `stddev_ts` e identidad de modelo/backend/fecha. Si no se pueden validar, se conserva la evidencia como `RUN_COMPLETED_UNPARSED`, `FAILED` o `TIMEOUT`; nunca se inventan métricas.

El LLM de `ask` no tiene acceso a la herramienta de benchmark. La ejecución de experimentos queda fuera del ciclo conversacional y requiere que el usuario lance el comando con `--approve`.

## Benchmarks TensorFold (native)

TensorFold dispone de su propio protocolo de benchmark y recibo; no se trata como si fuera llama-bench ni se mezclan sus métricas. El runner `benchmark-tensorfold` invoca únicamente `tensorfold-native benchmark` con argumentos internos acotados.

    lab-agent benchmark-tensorfold --model owner/repo
    lab-agent benchmark-tensorfold --model owner/repo --tokens 256 --reps 3
    lab-agent benchmark-tensorfold --model owner/repo --approve

Sin `--approve` solo se muestra el plan. El checkpoint debe existir previamente en la caché local o ser un directorio completo ya descargado. El agente no ejecuta `pull`, no descarga ni publica recibos. El modelo se pasa como ID Hugging Face o ruta local; no se aceptan flags arbitrarios, URLs, revisiones inline ni shell.

Opciones: `--tokens` (1..4096, predeterminado 256), `--reps` (1..5, predeterminado 3), `--timeout` (30..1800 s, predeterminado 900), `--output` (directorio nuevo), `--approve`. La temperatura se fija a 0 para repetibilidad inicial.

La evidencia contiene el recibo original de TensorFold, `stdout.log`, `stderr.log` y `manifest.json` propio con argumentos, versión declarada, modelo, configuración, tiempo, código de salida y SHA-256 del recibo. El estado `RECEIPT_SAVED_UNVERIFIED` indica que el motor guardó un JSON; no se eleva a `MEASURED` hasta implementar un validador contra una versión concreta del esquema de recibos. No se publica automáticamente.

## tandem.cpp (parche MoE para llama.cpp)

También se contempla **[ewhacc/tandem.cpp](https://github.com/ewhacc/tandem.cpp)** como variante/parche de llama.cpp, no como un motor independiente ni como un ejecutable separado. El proyecto publica un conjunto de parches sobre una revisión concreta de llama.cpp; conserva los binarios y la interfaz de llama.cpp y añade, entre otras cosas, la opción `--moe-cache-mib` para controlar la caché de expertos MoE en VRAM.

Por tanto:
- En el inventario aparece como tecnología asociada a llama.cpp, sin duplicar una instalación como si fuera otro runtime.
- La mera presencia de `llama-server` o `llama-cli` no demuestra que el parche tandem.cpp esté aplicado; la sonda explícita consulta la capacidad anunciada por `llama-server`.
- `lab-agent engines --probe` ejecuta únicamente `llama-server --help` (sin shell, sin modelo y sin iniciar un servidor), recoge stdout/stderr y busca `--moe-cache-mib`. La sonda es opt-in, tiene un límite de 2 segundos y clasifica el resultado como `VERIFIED`, `NOT DETECTED` o `UNKNOWN` (binario ausente, error o timeout).
- `VERIFIED` significa que la ayuda anuncia la opción; no demuestra por sí solo que un modelo cargue correctamente ni valida rendimiento. `NOT DETECTED` no prueba de forma absoluta que sea upstream stock: puede ser otra build o una ayuda incompleta. La versión/commit y el hash del binario siguen siendo necesarios para trazabilidad.
- Los benchmarks deberán comparar llama.cpp base y tandem.cpp con el mismo modelo, cuantización, contexto, prompt, generación y condiciones de GPU/CPU. Se registrará el commit base y el hash del parche/build para evitar atribuir resultados a la variante equivocada.

La instalación y aplicación del parche quedan fuera de la detección automática: el agente no clona repositorios, no aplica parches ni recompila motores por su cuenta.

## Fuentes inspeccionadas

- Caché estándar de Hugging Face: ~/.cache/huggingface/hub.
- Directorio de modelos ODS: ~/ods/data/models.
- Ejecutables de TensorFold, llama.cpp, Mistral.rs, Hermes y Magnitude en PATH o ubicaciones locales conocidas.
- Estado del servicio Magnitude mediante systemctl is-active, sin iniciarlo.
- Información del sistema mediante /etc/os-release, /proc, uname, nvidia-smi y nvcc.

Las rutas son acotadas intencionadamente. No se recorren discos completos ni se inspeccionan variables de entorno de Docker Compose.

## Estados de evidencia

| Estado | Significado |
|---|---|
| CACHE_ENTRY | Entrada detectada, sin pesos confirmados |
| WEIGHTS_PRESENT | Archivos con extensiones de pesos conocidas localizados |
| AVAILABLE | Motor confirma que puede acceder al modelo |
| LOAD_VERIFIED | Carga confirmada por el motor |
| RUNNING | Ejecución confirmada |
| MEASURED | Benchmark con métricas y protocolo registrados |

El inventario solo asigna CACHE_ENTRY y WEIGHTS_PRESENT. El runner llama-bench puede asignar MEASURED tras validar sus métricas. TensorFold conserva RECEIPT_SAVED_UNVERIFIED hasta validar su esquema/versionado de recibo. AVAILABLE, LOAD_VERIFIED y RUNNING no se infieren.

## Esquema de salida JSON

La estructura de `inventory --json`, `models --json` y `doctor --json` está documentada en `docs/inventory-schema-v1.md`. Los manifiestos de benchmarks están definidos en `docs/benchmark-manifest-v1.md`. Los consumidores deben comprobar `schema_version` e ignorar campos desconocidos.

## Seguridad y límites

- Diagnóstico, inventario y ask son de solo lectura.
- El informe y los directorios de evidencia se escriben únicamente a petición del usuario.
- El comando ask no ejecuta benchmarks ni puede invocar el runner.
- Los runners solo ejecutan llama-bench (GGUF) o tensorfold-native benchmark (checkpoint ya local) con `--approve`, límites y argumentos allowlist.
- No llama a APIs de proveedores.
- No lee secretos, .env, tokens ni contraseñas.
- No inicia, detiene ni reinicia servicios.
- No se admite shell, comandos arbitrarios, descarga de modelos ni endpoints LLM remotos.
- La ausencia de un resultado de detección no demuestra que un componente no exista fuera de las rutas inspeccionadas.
- WEIGHTS_PRESENT no garantiza compatibilidad con un motor ni que el archivo sea íntegro.
- Los resultados de servicios no consultables se muestran como desconocidos, no como inexistentes.

## Verificación automatizada

El workflow .github/workflows/lab-agent.yml comprueba formato, tests, árbol de dependencias y compilación x86_64-unknown-linux-musl. El artefacto estático se publica como artefacto de GitHub Actions cuando el workflow termina correctamente. No se afirmará que un binario se ha probado en el MSI hasta ejecutar pruebas allí.

## Desarrollo

    cargo fmt
    cargo test
    cargo build --release
