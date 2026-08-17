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
4. **Esquemas** — flujos de datos, dependencias, decisiones y secuencias en ASCII.
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

## 6. Documentación pedagógica de componentes terminados

Además del paquete normativo de fase, los componentes aceptados disponen de una guía en [`docs/completed/`](completed/).

Estas guías responden a una pregunta diferente: **«¿cómo puede una persona con conocimientos básicos de programación entender y mantener esta parte del sistema?»**

Cada guía debe explicar:

- propósito del componente;
- flujo de datos;
- entradas y salidas;
- función de los scripts principales;
- significado de las decisiones importantes;
- invariantes que no deben romperse;
- relación con los workflows;
- procedimiento de mantenimiento;
- límites que siguen abiertos.

Cuando un script sea central para una fase terminada, su código debe contener comentarios y docstrings pedagógicos que expliquen el porqué de las operaciones, no simplemente repetir qué hace una línea.

## 7. Limpieza de componentes terminados

Una fase terminada no debe conservar trazas de depuración, borradores obsoletos, archivos temporales ni experimentos abandonados.

Pero **fixture, ejemplo, dato sintético o artefacto histórico útil para reproducibilidad no es basura**. Debe conservarse y explicarse.

Antes de borrar algo hay que comprobar si participa en tests, workflows, documentación o reproducibilidad.

## 8. Esquemas ASCII como artefactos canónicos

Los mapas, esquemas, diagramas de arquitectura y flujos técnicos de LEONES son **artefactos de texto en ASCII**.

Esta es una decisión congelada del proyecto:

> **Los esquemas de LEONES se escriben, mantienen y publican en ASCII. No deben sustituirse por SVG, Mermaid ni otros formatos gráficos de diagramación.**

El ASCII es la representación canónica porque es legible directamente en el repositorio, versionable, accesible, independiente de recursos gráficos y fácil de revisar mediante diff.

Cuando un esquema necesite actualización, se modifica su bloque ASCII y se revisa su correspondencia con el sistema. No se crea una segunda representación gráfica que pueda divergir.

Los SVG siguen siendo válidos para **identidad gráfica, logos e iconografía** cuando corresponda. Esta norma afecta a mapas, esquemas y diagramas técnicos, no a los recursos de identidad visual.

## 9. Decisiones e invariantes

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

## 10. Descubribilidad

```text
README raíz
   ↓
docs/README.md
   ↓
docs/phases/README.md
   ↓
docs/phases/<phase-id>/README.md
   ↓
docs/completed/<component>.md
   ↓
artefactos técnicos / tests / commits
```

Los README de los componentes afectados también deben enlazar el paquete de fase correspondiente y, cuando proceda, la guía pedagógica.

## 11. Referencias locales y artefactos físicos

Toda referencia a un archivo local —imagen, SVG, script, CSS, dato, diagrama o documento— debe apuntar a un artefacto que exista físicamente en el repositorio en el momento del cierre.

Esto incluye especialmente catálogos y manifiestos: **no basta con documentar un nombre de archivo; el archivo debe estar presente y ser resoluble desde la ruta usada por la aplicación o la documentación.**

La comprobación automática se realiza con:

`scripts/validate_web_assets.py`

El control valida las referencias locales de la web y la documentación y comprueba que todos los logos declarados en `web/assets/graphics/logos/manifest.json` existen físicamente.

## 12. Convención

- Fase: `docs/phases/YYYY-MM-<slug>/`
- Entrada: `README.md`
- Arquitectura: `ARCHITECTURE.md`
- Decisiones: `DECISIONS.md`
- Validación: `VALIDATION.md`
- Esquemas: `DIAGRAMS.md` usando ASCII
- Guía pedagógica de componente terminado: `docs/completed/<component>.md`

## 13. Regla permanente

A partir de ahora, cada cierre de fase debe seguir obligatoriamente:

**implementar → validar → aceptar → documentar profusamente → enlazar → limpiar, fijar y dar esplendor → cerrar**.

El incumplimiento de la documentación impide considerar la fase completamente cerrada.

## 14. Relación

- [`docs/phases/README.md`](phases/README.md) — índice de fases.
- [`docs/completed/README.md`](completed/README.md) — índice de guías de mantenimiento.
- [`LEONES_DECISION_LOG.md`](../LEONES_DECISION_LOG.md) — decisiones históricas.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — arquitectura global.
- [`docs/ROADMAP.md`](ROADMAP.md) — evolución prevista.
- [`web/assets/graphics/logos/README.md`](../web/assets/graphics/logos/README.md) — contrato documental de logos funcionales.
