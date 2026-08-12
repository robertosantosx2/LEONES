# E2E LEONES v0.1

Este directorio almacena artefactos de una ejecución extremo a extremo local.

## Flujo

Hardware → Model → Task → Router → Runtime → Inference → LOTB → Report → Evidence.

El orquestador `scripts/leones-e2e.py` prepara y ejecuta los probes disponibles. No inventa rendimiento ni declara capacidades sin evidencia.

## Criterio de cierre

El E2E solo se considera **demostrado** cuando existe una ejecución real con un modelo y runtime locales y un resultado LOTB reproducible. Hasta entonces, `manifest.json` puede quedar en estado `prepared`.
