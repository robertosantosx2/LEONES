# LEONES Lab Agent

Agente local autocontenido en Rust para diagnóstico, inventario de modelos y herramientas, y preparación de investigación reproducible dentro de LEONES.

**Versión:** 0.3.0.  
**Estado:** inventario local de solo lectura.  
**Plataforma:** Linux x86_64 (objetivo inicial).  
**Licencia:** AGPL-3.0-only.

## Requisitos de diseño

- Cero crates externos: el bloque [dependencies] permanece vacío.
- Solo biblioteca estándar de Rust (std) y código propio integrado en el repositorio.
- Sin Python, Node.js ni conexión a Internet; el modo ask solo abre HTTP en loopback (127.0.0.1/localhost).
- Sin lectura de secretos ni archivos .env.
- Sin instalaciones, descargas, ejecución de modelos o cambios en servicios.
- Inventario basado en evidencia: una ruta o entrada de caché no se presenta como modelo cargable o ejecutado.
- El código no copia ni incorpora código de terceros; por tanto, no introduce dependencias de licencia adicionales.

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
| lab-agent report [RUTA] | Genera un informe Markdown |
| lab-agent version | Versión |

## Asistente local

El comando ask se conecta a un servidor compatible con OpenAI Chat Completions que escuche en loopback. No acepta HTTPS ni hosts remotos y no envía claves API. Ejemplo:

    lab-agent ask --endpoint http://127.0.0.1:8080/v1/chat/completions --model Qwen3.5-4B "Resume el hardware y los modelos disponibles"

El agente puede solicitar tres herramientas integradas: get_system_info, get_local_inventory y get_detected_tools. No existe herramienta de shell ni ejecución arbitraria. Las llamadas están limitadas a cuatro rondas por consulta. El servidor de inferencia debe estar iniciado por el usuario; Lab Agent no lo arranca ni carga modelos.

La implementación HTTP y el parser/serializador JSON están escritos en el propio proyecto y usan exclusivamente std. Esta primera interfaz solo soporta HTTP local sin TLS; no se conecta a Gemini ni a proveedores remotos.

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

La versión actual solo asigna los dos primeros estados. No infiere estados superiores.

## Esquema de salida JSON

La estructura de `inventory --json`, `models --json` y `doctor --json` está documentada en `docs/inventory-schema-v1.md`. Los consumidores deben comprobar `schema_version` e ignorar campos desconocidos.

## Seguridad y límites

- Solo lectura salvo el fichero de informe solicitado explícitamente.
- No ejecuta modelos ni benchmarks.
- No llama a APIs de proveedores.
- No lee secretos, .env, tokens ni contraseñas.
- No inicia, detiene ni reinicia servicios.
- La ausencia de un resultado de detección no demuestra que un componente no exista fuera de las rutas inspeccionadas.
- WEIGHTS_PRESENT no garantiza compatibilidad con un motor ni que el archivo sea íntegro.
- Los resultados de servicios no consultables se muestran como desconocidos, no como inexistentes.

## Verificación automatizada

El workflow .github/workflows/lab-agent.yml comprueba formato, tests, árbol de dependencias y compilación x86_64-unknown-linux-musl. El artefacto estático se publica como artefacto de GitHub Actions cuando el workflow termina correctamente. No se afirmará que un binario se ha probado en el MSI hasta ejecutar pruebas allí.

## Desarrollo

    cargo fmt
    cargo test
    cargo build --release
