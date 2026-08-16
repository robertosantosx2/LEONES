# H08 — Matriz completa de hardware

**Estado: 🟡 IMPLEMENTADA EN H10 · EN CONSOLIDACIÓN COMO CAPACIDAD INDEPENDIENTE.**

## Objetivo

Construir una matriz reproducible que relacione configuraciones de hardware con las posibilidades de ejecución/recomendación de los modelos del Atlas, sin confundir compatibilidad estimada con medición física.

## Evidencia existente

El cierre de H10 ya demuestra una matriz no vacía de **32.128 filas**. La ejecución generó perfiles para Intel i3/i5/i7/i9 y AMD Ryzen 3/5/7/9 en 2/4/8/16/32/64/128 GB, además de perfiles concretos como `cpu-i5-16gb`, `cpu-i7-64gb` y `rtx4060-8gb`. fileciteturn210file0L2-L2

Esto demuestra que la capacidad existe y funciona dentro del pipeline diario. **No demuestra todavía que H08 esté aceptada como producto independiente**, porque falta auditar su cobertura, reglas, duplicados, unidades, procedencia y correspondencia con hardware real.

## Principio

La matriz debe responder:

> ¿Qué configuración de hardware se está evaluando y qué sabemos realmente sobre su capacidad para este modelo, variante, runtime y workload?

Debe mantener separados:

```text
hardware disponible
        ≠
compatibilidad teórica
        ≠
CABE
        ≠
RULA
        ≠
medición real
```

## Dimensiones mínimas

- CPU: fabricante, familia, modelo y generación cuando estén disponibles.
- RAM: capacidad y tipo cuando estén disponibles.
- GPU: fabricante, familia/modelo y VRAM.
- almacenamiento cuando sea relevante para el runtime/modelo.
- sistema operativo/runtime cuando afecten a la ejecución.
- modelo, variante, artefacto y cuantización.
- contexto/workload.
- evidencia y procedencia.
- estado de incertidumbre.

## Reglas

1. No inventar capacidad cuando falta evidencia.
2. Mantener `unknown` cuando no se pueda determinar.
3. No convertir un score en una medición.
4. No usar precio para alterar la viabilidad técnica.
5. No mezclar hardware con identidad del modelo.
6. No registrar PII, hostname, seriales, MAC/IP, tokens o rutas privadas.
7. Una medición física debe conservar método, runtime, versión, hardware y workload.

## Auditoría H08

La fase se divide en:

- **H08.1 — Inventario de perfiles** 🔵
- **H08.2 — Normalización hardware** ⚪
- **H08.3 — Cobertura de CPU/RAM/GPU** ⚪
- **H08.4 — Reglas de compatibilidad** ⚪
- **H08.5 — Calidad y duplicados** ⚪
- **H08.6 — Conexión con evidencia/CABE/RULA** ⚪
- **H08.7 — Validación independiente** ⚪
- **H08.8 — Documentación y aceptación** ⚪

## Criterio de cierre

H08 solo será 🟢 cuando una ejecución independiente pueda demostrar:

- generación reproducible de la matriz;
- inventario de perfiles documentado;
- ausencia de duplicados críticos;
- reglas de correspondencia auditadas;
- unidades y capacidades coherentes;
- procedencia de datos relevantes;
- separación entre estimación y medición;
- validación automática del contrato;
- integración con H09 sin mezclar responsabilidades;
- documentación pedagógica de los scripts.

## Relación con H10

H10 es la evidencia de que la matriz ya funciona dentro del flujo completo. H08 la convierte en una capacidad mantenible y auditable por sí misma.

Referencia: [`../2026-08-atlas-recommendation-pipeline/VALIDATION.md`](../2026-08-atlas-recommendation-pipeline/VALIDATION.md).
