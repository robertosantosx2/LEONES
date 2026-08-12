# Autonomous Run

## Primer flujo autónomo de LEONES

`auto_run` conecta las piezas existentes sin absorber sus responsabilidades:

```text
Petición
   ↓
Leones Atlas
   ↓
Leones Router
   ↓
Decision
   ↓
Model Preparation
   ↓
Runtime
   ↓
respuesta
```

## Uso

```bash
python -m leones.auto_run --atlas leones_atlas.sqlite \
  "Write a Python function that adds two numbers"
```

## Regla importante

Esta primera versión solo puede trabajar con modelos **ya registrados y accesibles localmente**. No descarga modelos ni cambia archivos.

El objetivo es demostrar primero una cadena autónoma mínima y verificable. Después se añadirá selección basada en hardware y otros criterios, y posteriormente descarga/preparación automática cuando sea seguro hacerlo.

## Arquitectura

`auto_run` es un **orquestador fino**. Si una función empieza a adquirir una segunda responsabilidad, debe extraerse a otro módulo.
