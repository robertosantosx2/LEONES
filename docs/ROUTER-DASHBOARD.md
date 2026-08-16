# LEONES — Router y cuadro de mandos

## Estado

**🟢 Contrato funcional cerrado · implementación UI pendiente**

El Router dispone de un cuadro de mandos preparado para una futura WebApp. LEONES aporta los valores iniciales y las políticas no editables; el usuario puede afinar sus preferencias.

## Flujo

```text
LEONES DEFAULTS → PRESET → CUADRO → USER_PREFERENCES
→ EFFECTIVE_PROFILE → RESTRICCIONES + EVIDENCIA → ROUTER
→ RECOMENDACIÓN EXPLICABLE
```

## Apertura

**OSI no es configurable.** El usuario solo puede elegir:

- **Open (todos)** — todos los candidatos elegibles por LEONES.
- **Forzar Copyleft** — aplicar el filtro Copyleft definido por LEONES.

No se expone OSI como slider, peso o selector técnico. El usuario no puede convertir `OSI_UNKNOWN`/`OSI_FAIL` en candidatos válidos.

## Preferencias configurables

### Objetivo

- Equilibrado LEONES
- Máxima velocidad
- Máxima calidad
- Mínimo coste
- Local / privado
- Coding
- Razonamiento
- Agentic

### Rendimiento

- prioridad latencia ↔ calidad;
- prioridad tokens/s;
- objetivo de tiempo de respuesta;
- preferencia CABE: **1–<10 tok/s**;
- preferencia RULA: **10–100 tok/s**.

Los tok/s medidos son evidencia y no pueden ser alterados desde la UI.

### Hardware

CPU, RAM, GPU, VRAM, CPU-only y restricciones de recursos.

### Economía

Presupuesto máximo, coste por ejecución/token cuando exista evidencia, rendimiento/precio y TCO.

### Agentic

Permitir agentic, agente/harness preferido, herramientas, MCP, memoria, autonomía, sandbox y recuperación ante errores.

Solo se consideran componentes Agentic aceptados por los controles de LEONES.

## Presets

| Preset | Objetivo |
|---|---|
| **Equilibrado LEONES** | equilibrio general |
| **Máxima velocidad** | minimizar latencia / maximizar tok/s |
| **CABE** | priorizar 1–<10 tok/s |
| **RULA** | priorizar 10–100 tok/s |
| **Calidad** | priorizar capacidad |
| **Local / privado** | priorizar ejecución local |
| **Económico** | priorizar valor/TCO |
| **Agentic** | priorizar herramientas y autonomía |

Los presets son puntos de partida y no modifican los defaults globales.

## No editables

El usuario no puede modificar Gate OSI, identidad/trazabilidad, requisitos mínimos de evidencia, estados de verificación, seguridad/integridad, datos históricos ni reglas de no concurrencia.

## Arquitectura WebApp

```text
WebApp UI
   ↓
Preference Schema versionado
   ↓
Router API / service
   ↓
Policy + evidence filters
   ↓
Atlas + catálogo Agentic
   ↓
Recommendation result
```

La UI no accede directamente a tablas canónicas ni las modifica. El esquema de preferencias se versiona para evitar romper clientes futuros.

## Explicabilidad

Toda recomendación debe poder mostrar **Por qué**:

1. preferencias aplicadas;
2. restricciones de hardware;
3. política de apertura;
4. candidatos considerados;
5. exclusiones y motivos;
6. evidencia utilizada;
7. datos medidos frente a estimados;
8. compatibilidad Agentic;
9. nivel de confianza.

El Router no se reduce a un score opaco.

## Modelo de decisión

La UI distingue:

- **restricciones duras** → eliminan candidatos;
- **preferencias** → influyen en el ranking;
- **políticas LEONES** → no editables;
- **evidencia** → limita las afirmaciones posibles.

Ejemplos: VRAM insuficiente → excluir; evidencia inválida → excluir; latencia preferida → ponderar; precio preferido → ponderar; benchmark relevante → ponderar.

## Persistencia

```text
LEONES_DEFAULTS + USER_PREFERENCES → EFFECTIVE_PROFILE
```

Personalizar un perfil nunca modifica los valores oficiales de LEONES.

## No concurrencia

Los workflows que escriban perfiles, presets o resultados canónicos utilizarán exclusivamente `leones-main-writers` y `cancel-in-progress: false`.

## Cierre

La especificación funcional queda cerrada y preparada para WebApp. La implementación debe conservar la separación entre preferencias editables y políticas no editables, especialmente el Gate OSI.
