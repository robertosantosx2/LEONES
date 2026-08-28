# RC1 — Execution Gate

> **Objetivo:** llevar LEONES hasta el primer recorrido operativo real con la mínima cantidad de código y sin improvisar en Ubuntu.

## 1. Regla de entrada

Este documento aplica `docs/LEONES-Rules.md` y, de forma estricta, `docs/LEONES-Rules-STRICT.md`.

> **Poco código, cada pieza con una responsabilidad, comentarios que expliquen decisiones y README que explique cómo utilizarla.**

No se abre una sesión física para diseñar arquitectura. Ubuntu es el último gate de validación.

## 2. Camino canónico RC1

```text
conocimiento / Atlas
        ↓
perfil hardware real
        ↓
LLMFit
        ↓
LEONES selection
        ↓
ODS (SOHO) o Magnitude (asistente personal)
        ↓
runtime realmente usado por el sistema elegido
        ↓
tarea real
        ↓
benchmark LEONES
        ↓
evidencia
        ↓
MANADA
```

`llama.cpp` continúa como referencia física mínima para el contrato de ejecución/medición cuando ODS o Magnitude todavía no sean la ruta que debamos probar.

## 3. Trabajo que debe terminar antes de Ubuntu

### A. Contratos

- [x] Rules congeladas.
- [x] Regla STRICT de implementación fijada.
- [x] JALÓN 3 de medición cerrado.
- [x] Diferencia entre `estimated`, `reported`, `observed`, `measured` y `verified` fijada.
- [ ] Contrato de integración RC1 ODS/Magnitude validado contra las interfaces actuales.

### B. Núcleo mínimo

- [x] `hardware_profile.py` como observador.
- [x] `selection_pipeline.py` como decisión.
- [x] adapter/runner de llama.cpp como referencia mínima.
- [x] evidencia de benchmark.
- [ ] auditoría final de consumidores del núcleo.
- [ ] retirar del camino canónico los duplicados confirmados.
- [ ] dejar cada script núcleo con docstring, comentarios de decisiones, README y tests.

### C. ODS / Magnitude

- [ ] confirmar instalación y punto de entrada reales de ODS.
- [ ] confirmar instalación y punto de entrada reales de Magnitude.
- [ ] identificar qué hace cada uno por sí mismo: agente, herramientas, Hermes, motor de inferencia, selección y/o gestión del modelo.
- [ ] no duplicar esas funciones en LEONES.
- [ ] definir el contrato mínimo de entrada/salida que LEONES necesita.
- [ ] decidir qué ruta probar primero según el escenario RC1.

### D. LLMFit y tiers de consumo

- [ ] comprobar el formato real que produce LLMFit.
- [ ] mapearlo al perfil hardware de LEONES sin crear un segundo sistema de fit.
- [ ] conservar los tiers de hardware como clasificación operativa, no como benchmark.
- [ ] priorizar CPU-only, iGPU, portátiles y GPU de consumo.
- [ ] documentar qué datos son estimados y cuáles medidos.

### E. Benchmark de tarea

- [ ] elegir una única tarea RC1 representativa.
- [ ] fijar prompt/protocolo antes de ejecutarla.
- [ ] fijar warm-up y número de repeticiones.
- [ ] fijar criterio de éxito de la tarea.
- [ ] separar resultado de agente de throughput del runtime.
- [ ] definir exactamente qué artefactos se conservarán.

### F. Publicación

- [ ] definir el payload mínimo que MANADA recibirá.
- [ ] conservar procedencia y `execution_id`.
- [ ] impedir que una estimación entre como medición.
- [ ] preparar publicación sin convertir MANADA en otra fuente de verdad.

## 4. Lo que NO debe hacerse antes de Ubuntu

No construir:

- otro motor de inferencia;
- otro Hermes;
- otro sistema general de hardware-fit;
- otra base de modelos paralela a Atlas;
- otro benchmark que mezcle runtime y agente;
- un gran framework de adapters;
- código de instalación automática que oculte qué se está probando.

Si aparece una necesidad nueva, primero se responde: **¿ya la hace ODS, Magnitude, LLMFit, Atlas o el runtime?**

## 5. Criterio exacto para pedir Ubuntu

Se avisará al usuario cuando todo lo anterior que no requiera hardware esté cerrado y la siguiente acción necesite una de estas comprobaciones reales:

```text
hardware efectivo
runtime instalado
compatibilidad real
modelo realmente cargable
memoria / VRAM efectiva
rendimiento físico
comportamiento agentivo real
consumo
```

En ese momento la sesión Ubuntu será un procedimiento cerrado:

```text
comprobar entorno
→ instalar solo lo imprescindible
→ ejecutar
→ medir
→ conservar stdout/stderr
→ generar evidencia
→ validar
→ comparar
→ decidir siguiente paso
```

## 6. Primera prueba física prevista

La primera ejecución física debe ser pequeña y diagnóstica, no una batería masiva.

Orden:

1. identificar hardware real;
2. identificar sistema operativo y runtime;
3. verificar modelo y cuantización;
4. ejecutar una tarea mínima;
5. repetir según protocolo;
6. registrar throughput y métricas agentivas pertinentes;
7. generar evidencia;
8. comprobar reproducibilidad;
9. decidir si la ruta merece convertirse en benchmark RC1.

Solo después de superar esta prueba se amplía a otros modelos, runtimes o tiers.

## 7. Criterio de éxito de RC1

RC1 estará operativamente demostrada cuando exista al menos **una ruta completa**:

```text
hardware real
  ↓
LLMFit / fit inicial
  ↓
LEONES decide
  ↓
ODS o Magnitude
  ↓
runtime real
  ↓
tarea real
  ↓
benchmark LEONES
  ↓
evidencia reproducible
  ↓
recomendación
  ↓
MANADA
```

No es necesario que todos los componentes estén soportados para declarar la primera ruta operativa. Sí es necesario que la ruta elegida sea real, trazable y documentada.

## 8. Estado

**Pre-Ubuntu.**

El trabajo pendiente de esta fase es principalmente documental, contractual, de auditoría y de integración en GitHub. Ubuntu se solicitará únicamente cuando el siguiente dato no pueda demostrarse de otra forma.
