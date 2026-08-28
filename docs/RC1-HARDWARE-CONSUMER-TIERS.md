# RC1 — Tiers de hardware de consumo

> **Estado: contrato de clasificación inicial**

## Principio

El hardware de consumo es el objetivo principal de LEONES. Un tier sirve para organizar la búsqueda; **no garantiza rendimiento**.

La realidad física medida por LEONES prevalece sobre cualquier clasificación.

## Tiers

| Tier | Perfil | Uso orientativo |
|---|---|---|
| T0 | CPU-only / iGPU básica, ~8 GB RAM o menos | modelos pequeños, tareas ligeras |
| T1 | portátil de entrada, 8–16 GB RAM | asistente ligero |
| T2 | portátil/desktop medio, 16–32 GB RAM | modelos medianos cuantizados |
| T3 | GPU de consumo, típicamente 8–16 GB VRAM, 32 GB+ RAM preferible | asistente local competente |
| T4 | consumo alto / workstation doméstica | modelos grandes cuantizados y agentes exigentes |

## Dimensiones que deben conservarse

Un perfil no debe reducirse a `CPU + RAM` cuando existan datos mejores. Se deben conservar, cuando estén disponibles:

- CPU/modelo;
- arquitectura;
- cores/threads;
- RAM total y disponible;
- GPU;
- VRAM;
- iGPU/shared memory;
- ancho de banda de memoria;
- PCIe cuando sea relevante;
- sistema operativo;
- runtime;
- cuantización;
- contexto objetivo.

## Relación con LLMFit

LLMFit puede ayudar a determinar el **fit inicial** del modelo para el perfil.

```text
perfil hardware
      ↓
LLMFit
      ↓
fit estimado
      ↓
LEONES
      ↓
plan
      ↓
medición
```

No se debe crear en LEONES un segundo motor de estimación de memoria/rendimiento que duplique innecesariamente LLMFit.

## Relación con la medición

Un T2 medido con 25 tok/s no define que todos los T2 produzcan 25 tok/s.

La unidad de evidencia es la ejecución concreta:

```text
hardware_id
+ modelo
+ cuantización
+ runtime
+ configuración
+ ejecución
= evidencia
```

## Evolución

Los límites numéricos de los tiers podrán refinarse cuando aparezcan suficientes mediciones físicas. Cambiar los límites requiere documentación y tests; no se ajustarán para hacer encajar resultados retrospectivamente.
