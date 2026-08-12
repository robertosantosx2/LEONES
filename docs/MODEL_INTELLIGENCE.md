# Model Intelligence

## Objetivo

Model Intelligence describe modelos que LEONES puede considerar. No descarga ni ejecuta modelos.

## Registro mínimo

Cada modelo puede registrar:

- `model_id`
- familia
- revisión
- formato
- cuantización
- tamaño aproximado
- capacidades
- licencia
- fuente

## Separación de responsabilidades

```text
Model Intelligence → describe
Model Store        → persiste
Model Downloader   → descargará en una fase posterior
Runtime             → ejecutará
Router              → decidirá
```

Esta separación evita que un script de registro termine convirtiéndose en un instalador, gestor de modelos y runtime a la vez.

## CLI inicial

```bash
python -m leones.model_register --atlas leones_atlas.sqlite \
  --id qwen3-8b --family Qwen3 --format GGUF \
  --quant Q4_K_M --size 5.0 --license Apache-2.0
```

El comando registra exclusivamente los datos proporcionados explícitamente. No se afirma que sean correctos por el mero hecho de registrarlos: la procedencia y el estado de evidencia se incorporarán al catálogo de Atlas.
