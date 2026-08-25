# CanIRunThisModel

## Identidad
- **Fuente:** https://canirunthismodel.sefarai.com/
- **Capa LEONES:** preselector modelo → hardware/runtime.
- **Estado:** `research-candidate`.
- **Revisión:** 2026-08-25.

## Qué es
Herramienta orientada a la pregunta inversa de los selectores hardware-aware: dado un **modelo concreto**, determina si existe una configuración razonable para ejecutarlo en un hardware determinado y qué método/runtime utilizar.

## Problema que resuelve
Mientras LLMFit puede comenzar por el hardware y producir candidatos, aquí el flujo parte del modelo:

```text
modelo
  ↓
hardware
  ↓
memoria / compatibilidad
  ↓
runtime/método
  ↓
comando o configuración
```

Esto es necesario en LEONES porque el usuario puede llegar con una pregunta explícita: «quiero ejecutar este modelo».

## Evidencia
La herramienta se conserva como fuente externa de metodología de compatibilidad. No se heredan sus resultados como mediciones LEONES.

## Estimación
Memoria necesaria, compatibilidad y método recomendado son estimaciones externas. Una etiqueta `can run` no demuestra rendimiento ni éxito funcional.

## Relación con LLMFit y CanIRun.ai

```text
CanIRun.ai       → detecta hardware y personaliza fit
LLMFit           → hardware/intención → candidatos
CanIRunThisModel → modelo → ¿puede ejecutarse?
LEONES           → ambas direcciones + evidencia + runtime + medición
```

## Medición LEONES
Pendiente. La prueba debe tomar varios modelos de tamaños y arquitecturas diferentes y comprobar si el verdict externo coincide con:

- `runtime-selection.v1`;
- instalación real;
- arranque;
- contexto;
- memoria;
- TTFT/TPOT;
- grader funcional.

## Valor para LEONES
Alto como **segunda ruta de entrada del selector**. La UX de LEONES debería soportar tanto:

1. «Tengo este hardware, recomiéndame modelos»;
2. «Tengo este modelo, dime si puedo ejecutarlo».

## Limitaciones
- La compatibilidad no equivale a rendimiento.
- El método recomendado depende de versión del runtime.
- Los datos externos pueden quedar obsoletos.
- Un modelo puede arrancar y ser inútil por latencia o memoria.

## Integración

```text
MODEL REQUEST
     ↓
CanIRunThisModel estimate
     ↓
Atlas identity/evidence
     ↓
runtime-selection.v1
     ↓
executor → grader → benchmark
```

## Clasificación
`research-candidate`.

## Próximo paso
Contrastar 10 casos con LLMFit, CanIRun.ai, localmodel.run y VRAMBudget y convertir las discrepancias en tests de contrato.