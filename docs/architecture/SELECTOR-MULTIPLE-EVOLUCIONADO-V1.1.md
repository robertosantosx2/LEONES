# Selector múltiple evolucionado — V1.1

## Estado
**CONGELADO PARA V1.1**

Este documento fija el camino evolutivo del Selector de LLM sin sustituir el selector operativo actual de V1.

## Nombre canónico
**Selector múltiple evolucionado**

## Selector operativo actual (V1)
V1 continúa utilizando el camino existente basado en `model_selector.py`, feed de modelos y restricciones de hardware, con la información disponible actualmente.

## Camino congelado para V1.1
```text
caso de uso
  ↓
hardware
  ↓
runtime de inferencia
  ↓
técnicas de optimización
  ↓
Dense / MoE
  ↓
6 estimadores
  ↓
6 modelos × texto
6 modelos × imagen
6 modelos × vídeo
  ↓
108 candidatos
  ↓
normalización de parámetros
  ↓
Dense → total_parameters_m
MoE   → active_parameters_m
  ↓
menor + medio + mayor
  ↓
3 texto + 3 imagen + 3 vídeo
  ↓
9 candidatos
  ↓
runtime-selection.v1
  ↓
executor → grader → benchmark
  ↓
medición LEONES
```

## Reglas congeladas
1. El caso de uso del usuario se determina antes de valorar modelos.
2. El hardware real se determina antes de valorar modelos.
3. El runtime de inferencia se decide antes de valorar modelos.
4. Las técnicas de optimización compatibles se deciden antes de valorar modelos.
5. Dense y MoE se tratan de forma distinta.
6. Dense selecciona por `total_parameters_m`.
7. MoE selecciona por `active_parameters_m`; el total se conserva para memoria/almacenamiento.
8. Un MoE sin parámetros activos verificables no se sustituye silenciosamente por el total.
9. Cada uno de los seis estimadores debe aportar seis modelos por categoría.
10. Las categorías son texto, imagen y vídeo.
11. La salida externa esperada es 108 candidatos: 6 × 6 × 3.
12. La reducción conserva tres representantes por categoría: menor, medio y mayor según el parámetro de selección correspondiente.
13. La salida del selector es 9 candidatos: 3 texto, 3 imagen y 3 vídeo.
14. Un resultado externo estimado nunca se convierte automáticamente en medición LEONES.
15. La validación definitiva pasa por `runtime-selection.v1`, executor, grader y benchmark.
16. El candidato efectivo es una configuración: modelo + arquitectura + parámetros + cuantización + runtime + optimización + hardware + workload.

## No hacer durante V1
- No sustituir el selector operativo actual.
- No exigir todavía los seis adaptadores reales como condición para ejecutar V1.
- No introducir rankings alternativos paralelos.
- No mezclar `estimated_*` con `measured_*`.
- No usar el total de parámetros de un MoE como sustituto de sus parámetros activos.

## Evolución posterior a V1.1
El camino queda congelado hasta que exista una ejecución real de los seis estimadores, validación de sus adaptadores, cobertura de las tres categorías y benchmark controlado de las configuraciones seleccionadas.

## Relación documental
La capa de optimización de inferencia y el contrato Dense/MoE forman parte de este diseño, pero permanecen como fuentes de conocimiento independientes y no se duplican aquí.
