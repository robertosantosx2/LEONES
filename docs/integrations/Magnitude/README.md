# Magnitude ↔ LEONES

**Perfil:** Asistente personal IA.

Magnitude es un agente de coding open source que incorpora su propio motor de inferencia local, perfila el hardware, recomienda modelos y configura la ejecución. Su CLI se instala con npm y funciona en Linux/macOS; Windows está disponible mediante WSL.

## Estado de versión (revisado el 2026-10-16)

- **Última versión estable publicada de `@magnitudedev/cli` verificada:** `0.2.9`.
- **Último commit observado en `magnitudedev/magnitude:main`:** `7f029060a37ed1f7884db038222dc8f36430a08e` (2026-10-16).
- El instalador de LEONES solicita `@latest` por defecto, para no quedarse anclado a una versión antigua. Para reproducir una instalación se puede fijar `MAGNITUDE_CLI_VERSION`, por ejemplo `MAGNITUDE_CLI_VERSION=0.2.9 ./scripts/integrations/install_magnitude.sh`.
- La versión instalada se imprime al final y el preflight registra la versión detectada; esto no prueba que el runtime/modelo haya funcionado.

Referencias primarias: [CLI releases](https://github.com/magnitudedev/magnitude/releases) · [código fuente](https://github.com/magnitudedev/magnitude).

## Qué aporta Magnitude

- instalación CLI sencilla;
- perfilado del hardware;
- recomendaciones por calidad/velocidad/memoria;
- motor propio de inferencia local;
- cálculo previo de requisitos de memoria;
- ajuste de aceleración, placement y batching;
- agente capaz de usar shell, editar archivos y ejecutar scripts;
- skills extensibles.

Magnitude permite ejecución local/offline; los servicios cloud dependen de la configuración elegida.

## Instalación controlada

```bash
./scripts/integrations/install_magnitude.sh
```

El script realiza un preflight de solo lectura y pide confirmación antes de instalar la CLI globalmente con npm. Para fijar una versión:

```bash
MAGNITUDE_CLI_VERSION=0.2.9 ./scripts/integrations/install_magnitude.sh
```

LEONES no descargará modelos grandes automáticamente. Antes de instalar modelos pesados se debe mostrar:

```text
modelo
repositorio/origen
fichero
cuantización
memoria prevista
espacio requerido
runtime
```

y exigir confirmación.

## Preflight

```text
Node.js → npm → arquitectura → CPU/RAM → GPU detectada → espacio libre en disco
```

El preflight registra la versión efectiva de Node/npm y de la CLI si está instalada, e intenta detectar herramientas de NVIDIA (`nvidia-smi`), ROCm (`rocm-smi`) o Vulkan (`vulkaninfo`). El espacio libre se mide en el directorio de trabajo. **No comprueba conectividad de red ni certifica que un modelo quepa o que la inferencia funcione.** La recomendación de Magnitude se conserva como `reported`/`estimated`; no se convierte en medición LEONES.

## Captura de configuración

Cuando Magnitude exponga la información, LEONES captura:

- versión CLI;
- versión/ref del agente;
- modelo;
- repositorio Hugging Face;
- fichero de pesos;
- cuantización;
- runtime/engine;
- configuración de contexto;
- aceleración/placement/batching;
- recomendación elegida;
- resultado del benchmark LEONES.

Si un dato no está expuesto, se conserva `unknown`.

## Validación del agente

La prueba E2E utiliza un directorio temporal y una tarea inocua:

1. crear `hello.py`;
2. pedir una modificación pequeña y verificable;
3. comprobar el diff;
4. ejecutar el test;
5. registrar tiempo y tokens si están disponibles;
6. eliminar el proyecto temporal.

No se permite que la prueba acceda a archivos personales.

## Skills governance

Las skills son parte del comportamiento del agente y deben registrarse como metadatos, no como código de confianza automática:

```text
skill_id
source
version/ref
permissions
network_access
filesystem_scope
installed_at
consent
```

Una skill que requiera navegador, credenciales o acceso de red debe quedar fuera del benchmark base salvo consentimiento explícito.

## Privacidad

LEONES no captura prompts, contenido de repositorios, secretos, cookies ni rutas personales. Solo se conserva la información técnica necesaria para reproducibilidad y benchmarking.

## Encaje con Atlas

```text
Magnitude recommendation → reported/estimated
Magnitude selected config → observed
LEONES benchmark         → measured
```

La recomendación de Magnitude nunca sustituye a la evidencia técnica de Atlas.

## Fuentes primarias

- Magnitude: https://magnitude.dev/
- Magnitude GitHub: https://github.com/magnitudedev/magnitude
- Releases: https://github.com/magnitudedev/magnitude/releases
