# LEONES — Protocolo de documentación por fases

**Estado:** baseline aceptado como norma de proyecto.

## 1. Propósito

LEONES no considera terminada una fase únicamente porque el código funcione. Una fase queda **completada y aceptada** cuando su implementación, documentación y validación correspondiente han quedado trazadas.

Este protocolo convierte la documentación en parte del ciclo de ingeniería, no en una tarea posterior.

```text
DISEÑO → IMPLEMENTACIÓN → PRUEBA/VALIDACIÓN → ACEPTACIÓN EXPLÍCITA
                                      ↓
                         DOCUMENTACIÓN PROFUNDA
                                      ↓
                             ENLACE DESDE README
                                      ↓
                                FASE CERRADA
```

## 2. Disparador obligatorio

El protocolo se activa cuando una fase importante es declarada explícitamente **completada y aceptada**.

Mientras una fase esté en desarrollo o pendiente de validación, su documentación debe identificarse como **PROVISIONAL** y no puede presentar sus resultados como definitivos.

## 3. Paquete documental de cada fase aceptada

Cada fase debe disponer, cuando sea aplicable, de un directorio estable:

`docs/phases/<phase-id>/`

El paquete debe contener:

1. **Objetivos y alcance** — qué problema resuelve y qué queda fuera.
2. **Estado** — propuesta, desarrollo, validación, aceptada, sustituida o archivada.
3. **Arquitectura** — componentes, límites y responsabilidades.
4. **Esquemas y diagramas** — flujos de datos, dependencias, decisiones y secuencias.
5. **Reglas e invariantes** — aquello que el sistema debe respetar siempre.
6. **Decisiones y motivación** — qué se decidió, cuándo y por qué.
7. **Alternativas consideradas** — opciones descartadas y motivo.
8. **Interfaces y dependencias** — scripts, datos, APIs, workflows y contratos.
9. **Operación** — cómo ejecutar, comprobar, mantener y extender la fase.
10. **Validación** — tests, ejecuciones, evidencias y criterios de aceptación.
11. **Limitaciones conocidas** — lo que todavía no está demostrado.
12. **Evolución futura** — próximos pasos y deuda técnica.
13. **Trazabilidad** — commits, workflows, issues y artefactos.
14. **Índice documental** — enlaces a todo lo relacionado.

## 4. Hecho, evidencia e hipótesis

```text
HECHO IMPLEMENTADO
 ├─ código existente
 └─ comportamiento observado

EVIDENCIA
 ├─ test
 ├─ workflow
 ├─ medición
 └─ fuente externa

HIPÓTESIS / PLAN
 └─ todavía no demostrado
```

Una hipótesis no se convierte en hecho por aparecer en un README.

## 5. Regla de aceptación

Una fase solo puede pasar a **ACEPTADA** cuando exista evidencia suficiente para el criterio definido por la propia fase.

La frase «el código está» no es un criterio de aceptación.

Evidencia posible: workflow exitoso, test automatizado, salida generada y revisada, comparación antes/después, validación de esquema o prueba reproducible documentada.

## 6. Diagramas como artefactos mantenidos

Los diagramas deben explicar arquitectura, flujo o reglas y mantenerse sincronizados con el sistema. Una fase compleja debe incluir, como mínimo:

- diagrama de arquitectura;
- diagrama de flujo de datos/proceso;
- esquema de decisiones/invariantes cuando exista lógica de decisión.

Mermaid en Markdown es válido cuando resulte suficiente.

## 7. Decisiones e invariantes

Toda decisión estructural relevante debe conservar:

```text
DECISIÓN
├── contexto
├── problema
├── opciones
├── decisión adoptada
├── motivación
├── consecuencias
└── cómo verificarla
```

Las reglas que no deben romperse se documentan como **invariantes**.

## 8. Descubribilidad

```text
README raíz
   ↓
docs/README.md
   ↓
docs/phases/README.md
   ↓
docs/phases/<phase-id>/README.md
   ↓
artefactos técnicos / tests / commits
```

Los README de los componentes afectados también deben enlazar el paquete de fase correspondiente.

## 9. Convención

- Fase: `docs/phases/YYYY-MM-<slug>/`
- Entrada: `README.md`
- Arquitectura: `ARCHITECTURE.md`
- Decisiones: `DECISIONS.md`
- Validación: `VALIDATION.md`
- Diagramas: `DIAGRAMS.md`

## 10. Regla permanente

A partir de ahora, cada cierre de fase debe seguir obligatoriamente:

**implementar → validar → aceptar → documentar profusamente → enlazar → cerrar**.

El incumplimiento de la documentación impide considerar la fase completamente cerrada.

## 11. Relación

- [`docs/phases/README.md`](phases/README.md) — índice de fases.
- [`LEONES_DECISION_LOG.md`](../LEONES_DECISION_LOG.md) — decisiones históricas.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — arquitectura global.
- [`docs/ROADMAP.md`](ROADMAP.md) — evolución prevista.
