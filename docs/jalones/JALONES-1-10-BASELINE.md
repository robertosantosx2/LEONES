# LEONES — Baseline consolidada JALONES 1–10

**Estado:** FIJADO  
**Fecha de consolidación:** 29 de agosto de 2026  
**Ámbito:** trabajo realizado desde el 27 de agosto de 2026  
**Rama:** `rc1-minimal-script-cleanup`

## Propósito

Este documento es el mapa de recuperación de la fase. Su función es impedir que el proyecto vuelva a repartir una misma responsabilidad entre varios mecanismos.

La regla general es sencilla: **un contrato, una responsabilidad, una evidencia y una ruta canónica**.

## Cadena canónica

```text
selection
  ↓
runtime selection / registry
  ↓
execution authorization
  ↓
physical execution (cuando corresponda)
  ↓
measurement
  ↓
runtime-benchmark.v1
  ↓
runtime-benchmark-evidence.v1.1
  ↓
ODS / Magnitude decision bridge
  ↓
validation
  ↓
promotion
  ↓
publication
  ↓
recommendation
  ↓
faithful recommendation output
  ↓
E2E trace
```

## Estado de los jalones

| Jalón | Responsabilidad cerrada | Naturaleza | Ejecución física | Estado |
|---|---|---|---:|---|
| 1 | base y CI | fundacional | No | **CERRADO** |
| 2 | runtime físico + evidencia real | operacional | Sí | **CERRADO** |
| 3 | protocolo de medición real + evidencia v1.1 | operacional | Sí | **CERRADO** |
| 4 | taxonomía de runtimes + adapters | contractual | No | **CERRADO DECLARATIVO** |
| 5 | contrato de decisión ODS/Magnitude + bridge | contractual | No | **CERRADO CONTRACTUAL** |
| 6 | gate de recomendación/evidencia | contractual | No | **CERRADO DECLARATIVO** |
| 7 | validation → promotion → publication | contractual | No | **CERRADO DECLARATIVO** |
| 8 | trazabilidad E2E | contractual | No para el contrato | **CERRADO DECLARATIVO** |
| 9 | recomendación canónica | contractual | No | **CERRADO** |
| 10 | salida fiel de recomendación | contractual | No | **CERRADO** |

## Hitos técnicos que no deben perderse

### Runtime V1.1

La arquitectura consolidó una interfaz común para runtimes y adapters. La expansión declarativa incluye vLLM, SGLang, MLX/MLX-LM, ExLlama, OpenVINO, ONNX Runtime GenAI y TensorRT-LLM, además de los runtimes ya existentes.

La presencia declarativa de un adapter **no equivale** a evidencia de ejecución física. La autorización para ejecutar debe permanecer vinculada al runner confiable y al host apropiado.

### Evidencia real

La medición física queda separada de cualquier estimación. El contrato de evidencia conserva identidad del modelo, revisión, cuantización, artefacto, hash, contexto, runtime, versión, comando, hardware, protocolo, warm-up, iteraciones, identidad de ejecución y marcas temporales.

El resultado físico de JALÓN 2 que queda como referencia es la ejecución real de `llama.cpp` con Qwen3 0.6B Instruct Awq, Q4_K_M, CPU y 4 hilos, con cinco ejecuciones medidas y evidencia conservada.

### ODS / Magnitude

La decisión de hardware/runtimes se apoya en las señales que el contrato asigna a ODS y Magnitude. Esas señales no se deben convertir silenciosamente en una segunda medición local ni mezclarse con evidencia física.

### Recomendación

JALÓN 6 establece la frontera: la recomendación necesita evidencia y no introduce otro motor de scoring. JALÓN 9 produce la recomendación canónica y JALÓN 10 la convierte en una salida fiel, sin volver a decidir ni medir.

### Trazabilidad

JALÓN 8 fija una única traza de ciclo de vida. La traza sirve para demostrar cómo una selección llega a una recomendación; no debe convertirse en una segunda fuente de decisión.

## Reglas de conservación

1. No rediseñar retroactivamente JALONES 1–10.
2. No crear un segundo benchmark, scoring o motor de recomendación.
3. No confundir una señal externa con evidencia medida localmente.
4. No confundir un adapter declarado con una ejecución validada.
5. No convertir los runners de auditoría en lógica de negocio.
6. Mantener los artefactos históricos que expliquen decisiones o evidencias.
7. Mover a `deprecated/` sólo lo que esté realmente fuera de la ruta canónica y conservar su documentación de migración.
8. Documentar toda nueva superficie con comentarios pedagógicos y `.md` de uso.
9. Reservar Ubuntu para las operaciones que necesiten ejecución física.
10. Toda nueva etapa debe añadir la mínima superficie contractual necesaria.

## Criterio para la siguiente etapa

La fase siguiente no consiste en inventar otro sistema. Consiste en **conectar de forma operacional los contratos ya cerrados**, ejecutar los casos que requieran hardware real, recoger evidencia y comprobar que la recomendación final es trazable hasta la decisión y sus fuentes.

## Frase de recuperación

> **JALONES 1–10 están fijados: no rediseñar; limpiar, documentar, integrar, ejecutar cuando sea necesario, medir, evidenciar, decidir, validar, publicar, recomendar y trazar.**