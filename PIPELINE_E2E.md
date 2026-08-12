# 🦁 LEONES · recorrido extremo a extremo

El MVP operativo debe recorrer, sin saltos conceptuales:

1. Hardware Intelligence → `leones-hardware.py`
2. Model Identity → `leones-model.py`
3. Task Intelligence → `leones-task.py`
4. Atlas → `atlas/schema.json` + catálogo con evidencia
5. Router → `leones-router.py`
6. Runtime → `leones-runtime.py`
7. Inferencia → `leones-infer.py`
8. LOTB → `leones-lotb.py`
9. Report → `leones-report.py`
10. Privacy → `leones-privacy.py`
11. Publish/Manada → `leones-publish.py`

## Regla

Un paso puede recomendar al siguiente, pero no debe declarar que el siguiente se ha ejecutado hasta disponer de su resultado.

## Primer objetivo reproducible

Con un runtime local real y un modelo accesible:

`hardware + model + task → router → runtime → inference → LOTB → report`

Después de revisión de privacidad, el resultado podrá convertirse en evidencia publicable.

## Estado

Los componentes individuales existen en distintos niveles de madurez. El recorrido completo todavía requiere una ejecución real sobre una máquina con runtime/modelo local.
