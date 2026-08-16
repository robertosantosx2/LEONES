# H08 — Matriz de hardware

## Estado

**🟢 Infraestructura de matriz terminada y limpia.**

La matriz genera perfiles CPU × RAM × GPU y reutiliza el recomendador oficial. No debe interpretarse como una batería de benchmarks físicos: sus filas son compatibilidad/recomendación derivada, no mediciones de tok/s.

## Qué hace

El generador recorre automáticamente:

- Intel Core i3/i5/i7/i9;
- AMD Ryzen 3/5/7/9;
- 2, 4, 8, 16, 32, 64 y 128 GB de RAM;
- CPU-only;
- GPUs NVIDIA presentes en `data/hardware/nvidia_ai_gpus.csv`.

La RAM del sistema y la VRAM de la GPU permanecen separadas.

## Flujo

```text
catálogo GPU + perfiles CPU/RAM
              ↓
       atlas_hardware_matrix.py
              ↓
   recomendador oficial Atlas
              ↓
 compatibilidad / contexto / runtime
              ↓
       matriz hardware CSV
```

## Regla de contexto

El contexto objetivo del perfil se deriva de la RAM disponible como política de recomendación. No significa que el modelo soporte automáticamente ese contexto.

El script limita `context_target_tokens` al contexto que el propio registro del modelo demuestra cuando está disponible. No inventa capacidad de contexto.

## Separación de rendimiento

`tokens_per_second` puede aparecer en el contrato de salida, pero H08 no convierte esa columna en una medición. La evidencia empírica real sigue el circuito documentado en [`BENCHMARK-MEASURED-EVIDENCE.md`](BENCHMARK-MEASURED-EVIDENCE.md).

Por tanto:

```text
H08 = compatibilidad / recomendación de hardware
Benchmark = rendimiento observado
```

No deben mezclarse.

## Publicación segura

La matriz se construye en un directorio temporal y se publica al final de la generación. Si no se obtiene ninguna fila, el script produce diagnóstico y termina con error en vez de publicar una matriz vacía.

El diagnóstico separa, entre otras causas:

- perfil técnico insuficiente;
- memoria;
- contexto;
- runtime;
- cuantización/pesos;
- hardware;
- workload;
- filas que sí encajan.

## Tests

`tests/test_atlas_hardware_matrix.py` comprueba el contrato del diagnóstico: perfiles fuera de T2/T3, workload, hardware, memoria y coincidencias válidas se contabilizan de forma independiente.

## Criterio de cierre

H08 queda cerrado como **infraestructura de matriz** porque:

1. la cobertura de perfiles está automatizada;
2. CPU-only y GPU están contemplados;
3. RAM y VRAM están separadas;
4. la lógica de recomendación se reutiliza en lugar de duplicarse;
5. el contexto no se inventa;
6. la publicación vacía se bloquea;
7. existe diagnóstico de exclusiones;
8. existe prueba automatizada;
9. la documentación distingue claramente matriz de compatibilidad y benchmark empírico.

## Pendiente fuera del cierre

Queda pendiente ampliar la **validación empírica sobre hardware físico real**. Esa tarea pertenece al bloque de benchmarks medidos y no debe usarse como motivo para etiquetar la matriz de compatibilidad como una medición.

## Mantenimiento

Cuando se añadan nuevas familias CPU, RAM, GPU o políticas de contexto, deben actualizarse el script, sus tests y este documento. Todo workflow que escriba resultados en `main` debe respetar la regla global de no concurrencia de LEONES.
