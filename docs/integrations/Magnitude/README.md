# Magnitude ↔ LEONES

**Perfil:** Asistente personal IA.

Magnitude es un agente de coding open source que incorpora su propio motor de inferencia local, perfila el hardware, recomienda modelos y configura la ejecución. Su CLI se instala con `npm install -g @magnitudedev/cli`; soporta macOS y Linux y Windows mediante WSL. citeturn0search1turn0search4

## Qué aporta Magnitude

- instalación CLI sencilla;
- perfilado del hardware;
- recomendaciones por calidad/velocidad/memoria;
- motor propio sobre llama.cpp;
- cálculo previo de requisitos de memoria;
- ajuste de aceleración, placement y batching;
- agente capaz de usar shell, editar archivos y ejecutar scripts;
- skills extensibles.

Magnitude declara que el uso local puede ser completamente privado/offline; el modo cloud es opcional. citeturn0search1turn0search5

## Instalación controlada

```bash
npm install -g @magnitudedev/cli
cd proyecto-de-prueba
magnitude
```

LEONES no ejecutará una descarga grande automáticamente. Antes de instalar modelos pesados se muestra:

```text
modelo
repositorio/origen
fichero
cuantización
memoria prevista
espacio requerido
runtime
```

y se exige confirmación.

## Preflight

```text
Node.js → npm → arquitectura → CPU/RAM → GPU → disco → red
```

El preflight debe registrar la versión efectiva de Node/npm y la versión instalada de la CLI. La recomendación de Magnitude se conserva como `reported`/`estimated`; no se convierte en medición LEONES.

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
