# LEONES — LLM Smoke Test

Primera prueba local de referencia para el catálogo de `scripts/local/`.

## Objetivo

Comprobar de forma rápida que un runtime local puede cargar un modelo y producir una respuesta, dejando una base común para futuras pruebas de rendimiento.

Esta primera versión es deliberadamente pequeña: **no pretende ser todavía un benchmark oficial**.

## Alcance

Mide:

- carga correcta del runtime/modelo;
- tiempo de ejecución de una solicitud;
- longitud aproximada de la respuesta;
- información básica del entorno cuando está disponible.

No pretende medir de forma rigurosa:

- calidad del modelo;
- posición en un benchmark público;
- rendimiento entre hardware distinto;
- consumo energético;
- VRAM/RAM exacta;
- tokens/segundo reproducibles entre runtimes.

## Privacidad

El script no envía datos a LEONES. La entrada se procesa localmente mediante el runtime que el usuario configure.

## Estado

`EXPERIMENTAL` — patrón inicial del paquete local.

Antes de considerarlo benchmark oficial deberán definirse el runtime, formato de resultados, metodología, repetición, warm-up y control de variables.

## Estructura prevista

```text
llm-smoke-test/
├── README.md
├── run.py
└── examples/
```

## Requisitos

Python 3.11+ recomendado.

El runtime del modelo se instalará por separado según el modelo que quiera probar el usuario. Esta prueba no instala ni descarga automáticamente modelos.

## Ejecución

```bash
python run.py --help
```

La implementación inicial sólo debe incorporar dependencias de Python estándar.

## Principio de diseño

Este paquete debe poder copiarse fuera del repositorio LEONES y seguir siendo comprensible y ejecutable. No puede importar `atlas`, `agents`, workflows ni módulos internos.
