# RC1 — Pre-Ubuntu checklist

> **Estado: 🟢 PRE-Ubuntu cerrado.**

Este documento marca el punto exacto en el que la arquitectura deja de ser objeto de diseño y Ubuntu pasa a ser el siguiente instrumento de validación.

## Cerrado antes de Ubuntu

- [x] LEONES Rules canónicas.
- [x] Rules STRICT: poco código, responsabilidad única, comentarios de decisiones y README operativo.
- [x] JALÓN 3: contrato de medición real cerrado.
- [x] Ruta conceptual `LLMFit → LEONES → ODS/Magnitude → runtime → benchmark → evidencia → MANADA`.
- [x] ODS identificado como ruta SOHO.
- [x] Magnitude identificado como ruta de asistente personal.
- [x] Hermes permanece dentro de ODS y no se duplica.
- [x] LLMFit queda como primera capa de fit y no se duplica.
- [x] AirLLM y FreeToken quedan bajo regla upstream-first.
- [x] Diferencia entre fit estimado y medición real fijada.
- [x] Benchmark de runtime separado del benchmark de tarea/agente.
- [x] MANADA definido como destino de conocimiento validado.

## Lo que solo puede cerrarse físicamente

```text
hardware efectivo
runtime instalado
ODS / Magnitude instalable
modelo realmente cargable
backend realmente utilizado
memoria / VRAM efectiva
rendimiento real
comportamiento agentivo
```

## Primera sesión Ubuntu

No instalar todo.

Primero:

1. capturar hardware;
2. capturar software base;
3. ejecutar LLMFit en modo diagnóstico/recomendación;
4. determinar si la máquina es un candidato razonable para ODS, Magnitude o ambos;
5. elegir **una** ruta;
6. instalar solo esa ruta;
7. identificar el runtime que realmente ejecuta;
8. probar un modelo pequeño;
9. ejecutar una tarea RC1;
10. conservar evidencia;
11. decidir si se continúa con benchmark repetido.

## Regla de parada

Si la primera instalación revela incompatibilidad o una diferencia arquitectónica importante, **no se parchea LEONES en caliente**. Se conserva la evidencia, se documenta la decisión y se vuelve a GitHub.

## Después de una primera ejecución válida

```text
hardware observado
      ↓
LLMFit observado
      ↓
selección LEONES
      ↓
ODS/Magnitude
      ↓
runtime real
      ↓
tarea RC1
      ↓
medición repetida
      ↓
evidencia
      ↓
MANADA
```

Solo después se amplían tiers, modelos o runtimes.

## Gate

**El siguiente paso necesita Ubuntu.**

No queda ninguna decisión arquitectónica imprescindible que deba resolverse allí. La sesión física debe limitarse a comprobar la realidad y producir evidencia.
