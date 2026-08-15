# Atlas ingestion v0.2

El Atlas permanece vacío de conocimiento oficial hasta incorporar datos con procedencia y un estado de evidencia adecuado.

## Capas de entrada

### 1. `external_evidence`

La primera evidencia de descubrimiento de modelos debe buscarse prioritariamente en:

1. Hugging Face
2. LM Arena
3. Artificial Analysis
4. sitio/blog oficial del fabricante

Estas fuentes sirven para descubrimiento, contraste e investigación. No convierten automáticamente una afirmación en una medición LEONES ni en conocimiento `verified`.

### 2. MANADA

MANADA aporta perfiles y experimentos de máquinas y ejecuciones locales. Los datos entran como `reported` y solo pasan a `reproducible`/`verified` cuando se conserva información suficiente y se realiza la comprobación correspondiente.

## Fuente mínima de un registro

Cada registro debe cumplir `atlas/schema.json` y contener:

- `id`, `kind`, `name`;
- estado de evidencia: `reported`, `reproducible`, `verified` o `rejected`;
- fuentes y fecha de recuperación cuando estén disponibles;
- clasificación de apertura separada de cualquier puntuación;
- identidad separada de hosting/forge;
- si existe compatibilidad de ejecución: modelo × artefacto × cuantización × runtime × versión × hardware;
- si existe una medición: método, contexto, workload y procedencia.

## Hardware

Un perfil de hardware no se reduce a CPU/GPU/RAM. Siempre que sea posible se registran:

- compute/FLOPS medidos o estimados;
- memoria y bandwidth teórico/medido;
- almacenamiento, protocolo, bus, enlace y rendimiento;
- rutas de transferencia relevantes e interconexiones.

## Privacidad

No se incorporan identidad del operador, hostname, número de serie, UUID, MAC/IP, ubicación exacta, credenciales, tokens ni rutas privadas.

## Flujo

```text
Prospección
   ↓
external_evidence / MANADA
   ↓
extracción
   ↓
normalización
   ↓
quality flags
   ↓
revisión
   ↓
Atlas
   ↓
Router
```

Los datos descubiertos automáticamente no se consideran verificados por el mero hecho de aparecer en una fuente.
