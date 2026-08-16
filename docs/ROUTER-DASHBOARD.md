# LEONES — Router y cuadro de mandos

## Estado

**🟢 Contrato funcional cerrado · implementación UI pendiente**

El Router de LEONES dispone de un cuadro de mandos pensado desde el principio para poder publicarse como WebApp. LEONES proporciona valores predefinidos; el usuario puede afinarlos sin modificar las reglas del sistema.

## Principio

```text
LEONES DEFAULTS
      ↓
PRESET
      ↓
CUADRO DE MANDOS
      ↓
PREFERENCIAS DEL USUARIO
      ↓
PERFIL EFECTIVO
      ↓
RESTRICCIONES + EVIDENCIA
      ↓
ROUTER
      ↓
RECOMENDACIÓN EXPLICABLE
```

## Apertura: única decisión del usuario

**OSI no es un parámetro configurable.** El usuario no puede modificar el Gate OSI, sus estados ni sus requisitos.

La interfaz solo ofrece:

- **Open (todos)** — utilizar todos los candidatos que sean elegibles según las reglas de LEONES.
- **Forzar Copyleft** — exigir el filtro Copyleft definido por LEONES.

No existe slider, peso ni checkbox de OSI. El usuario tampoco puede convertir `OSI_UNKNOWN` o `OSI_FAIL` en candidatos válidos.

## Parámetros configurables

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
- preferencia CABE (1–<10 tok/s);
- preferencia RULA (10–100 tok/s).

Los valores medidos de tok/s son evidencia; el usuario no puede alterar una medición.

### Hardware

- CPU disponible;
- RAM disponible;
- GPU disponible;
- VRAM disponible;
- CPU-only permitido;
- restricciones de recursos.

### Economía

- presupuesto máximo;
- coste por ejecución/token cuando exista evidencia;
- rendimiento/precio;
- TCO.

### Agentic

- permitir uso agentic;
- agente/harness preferido;
- herramientas permitidas;
- MCP;
- memoria;
- autonomía;
- sandbox;
- recuperación ante errores.

Solo se consideran componentes Agentic que hayan superado los controles de LEONES aplicables.

## Presets LEONES

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

Los presets son puntos de partida y nunca modifican los defaults globales.

## Restricciones no editables

El usuario nunca puede modificar:

- Gate OSI;
- identidad y trazabilidad;
- requisitos mínimos de evidencia;
- estados `verified`, `unknown` o `unverified`;
- seguridad/integridad;
- datos históricos;
- reglas de no concurrencia.

## UX preparada para WebApp

La UI debe ser responsive y estar desacoplada del motor:

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

Boceto funcional:

```text
┌──────────────────────────────────────┐
│ ¿Qué necesitas?                      │
│ [ Equilibrado LEONES ▼ ]             │
├──────────────────────────────────────┤
│ Velocidad       ─────●────           │
│ Calidad         ─────────●─           │
│ Coste           ───●──────           │
│ Privacidad      ─────────●─           │
├──────────────────────────────────────┤
│ Hardware                             │
│ RAM             [ 32 GB ▼ ]          │
│ GPU             [ RTX 4060 ▼ ]       │
│ VRAM            [ 8 GB ▼ ]           │
├──────────────────────────────────────┤
│ Apertura                             │
│ (●) Open (todos)                     │
│ ( ) Forzar Copyleft                  │
├──────────────────────────────────────┤
│ Agentic                               │
│ [✓] Permitir                         │
│ Autonomía       ─────●────           │
│ Herramientas    ─────●────           │
├──────────────────────────────────────┤
│          [ RECOMENDAR ]              │
└──────────────────────────────────────┘
```

Los valores del boceto son ilustrativos; los defaults oficiales los define LEONES.

## Explicabilidad

El resultado debe incluir **Por qué**:

1. preferencias aplicadas;
2. restricciones de hardware;
3. política de apertura elegida;
4. candidatos considerados;
5. candidatos excluidos y motivo;
6. evidencia utilizada;
7. datos medidos frente a estimados;
8. compatibilidad Agentic;
9. nivel de confianza.

El Router no debe reducir la decisión a un score opaco.

## Restricciones, preferencias y políticas

La UI debe distinguir visualmente:

- **restricciones duras** — eliminan candidatos;
- **preferencias** — influyen en el ranking;
- **políticas LEONES** — no editables;
- **evidencia** — determina qué afirmaciones pueden sostenerse.

Ejemplo:

```text
VRAM insuficiente        → EXCLUIR
OSI / evidencia inválida → EXCLUIR
latencia preferida       → ponderar
precio preferido         → ponderar
benchmark relevante      → ponderar
```

## Persistencia

```text
LEONES_DEFAULTS
      +
USER_PREFERENCES
      ↓
EFFECTIVE_PROFILE
```

Personalizar un perfil nunca modifica los valores oficiales de LEONES.

## No concurrencia

Los workflows que escriban perfiles, presets o resultados canónicos utilizarán exclusivamente `leones-main-writers` y `cancel-in-progress: false`.

## Criterio de cierre

La especificación del cuadro de mandos queda cerrada y preparada para WebApp. La implementación visual debe conservar la separación entre preferencias editables y políticas no editables, especialmente el Gate OSI.
