# LEONES — Catálogo Agentic independiente

## Estado

**🟢 ARQUITECTURA CERRADA / CANDIDATOS PENDIENTES DE GATE OSI**

El ecosistema agentic se mantiene como un elemento independiente del catálogo de LLMs. Un agente, harness, framework, protocolo o herramienta no entra automáticamente en Atlas por ser conocido, popular o útil.

## Regla principal

```text
DESCUBRIMIENTO
    ↓
CATÁLOGO AGENTIC (independiente)
    ↓
GATE OSI
    ↓
EVIDENCIA + CLASIFICACIÓN
    ↓
ATLAS
```

**Todo elemento agentic debe pasar por el Gate OSI antes de incorporarse al Atlas canónico.**

## Qué entra en el catálogo independiente

- agentes y coding agents;
- harnesses de ejecución/evaluación;
- frameworks y SDKs agentivos;
- protocolos de interoperabilidad;
- sistemas de herramientas y tool runtimes;
- sandboxes y mecanismos de aislamiento relevantes para agentes;
- memoria, checkpointing y recuperación cuando formen parte del sistema agentivo;
- observabilidad/tracing específicos del agente;
- evaluadores y suites agentivas.

No se mezclan estas categorías con `LLM`, `model_family`, `hardware_profile` ni `benchmark`.

## Identidad mínima

Cada candidato debe disponer de:

- `agentic_id` estable;
- nombre canónico;
- tipo (`agent`, `harness`, `framework`, `protocol`, `tool_runtime`, `sandbox`, `evaluator`);
- organización/proyecto;
- repositorio o sitio primario;
- versión/release comprobada;
- fecha de descubrimiento;
- estado OSI;
- licencia;
- fuente primaria;
- fecha de última verificación.

## Gate OSI obligatorio

El Gate OSI es una **barrera de entrada**, no una puntuación de calidad.

```text
CANDIDATO
   ↓
¿identidad inequívoca?
   ↓ sí
¿fuente primaria?
   ↓ sí
¿licencia identificable?
   ↓ sí
¿cumple el criterio OSI definido por LEONES?
   ↓ sí
EVIDENCIA / QUALITY GATE
   ↓
ATLAS
```

Si el Gate OSI no puede resolverse con evidencia suficiente, el elemento permanece fuera del Atlas canónico como `unverified`/`pending`.

**No se convierte una licencia desconocida en OSI-compatible por inferencia.** Tampoco se confunde "open source" comercial, open weights, código visible o disponibilidad gratuita con una aprobación automática del Gate.

## Separación de estados

```text
DISCOVERED
    ↓
IDENTIFIED
    ↓
OSI_PENDING
    ↓
OSI_PASS / OSI_FAIL / OSI_UNKNOWN
    ↓
EVIDENCE_PENDING
    ↓
ATLAS_ELIGIBLE
    ↓
ATLAS_VERIFIED
```

`OSI_FAIL` y `OSI_UNKNOWN` no se promocionan al Atlas canónico.

## Relación con Atlas

Atlas recibe únicamente elementos que hayan superado los controles requeridos. El catálogo agentic puede contener muchos más candidatos que Atlas.

```text
AGENTIC CATALOGUE ≠ ATLAS

catalogue = descubrimiento + candidatos + estados
Atlas      = conocimiento aceptado y trazable
```

Esto permite investigar herramientas propietarias o de licencia incompatible sin perderlas del radar, pero impide que aparezcan como componentes aceptados del ecosistema abierto de LEONES.

## Relación con el recomendador

El recomendador no debe consultar directamente candidatos `DISCOVERED`, `OSI_PENDING`, `OSI_FAIL` u `OSI_UNKNOWN` como si fueran opciones verificadas.

```text
Agentic catalogue
       ↓
     Gate OSI
       ↓
 Evidence/quality gate
       ↓
 Atlas
       ↓
 Router / recomendador
```

## No concurrencia

Todo workflow que modifique el catálogo agentic o Atlas debe respetar la regla global de LEONES: un único grupo escritor `leones-main-writers` y `cancel-in-progress: false`.

No se crean escritores paralelos para agentes, frameworks o protocolos.

## Inventario inicial

El inventario de `docs/AGENTIC-INVENTORY-2026.md` constituye la lista inicial de candidatos, no una lista de elementos ya aceptados. Cada entrada deberá pasar individualmente por este contrato.

## Criterio de cierre

La arquitectura queda cerrada cuando:

1. el catálogo agentic permanece separado;
2. el Gate OSI es obligatorio;
3. Atlas solo recibe candidatos que superan el gate y los controles posteriores;
4. los estados negativos/desconocidos se conservan;
5. la procedencia queda registrada;
6. ningún workflow rompe la regla de no concurrencia.

La validación individual de cada candidato es trabajo de evidencia posterior y no se simula aquí.
