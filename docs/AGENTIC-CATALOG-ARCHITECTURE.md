# LEONES — Catálogo Agentic independiente

## Estado

**🟢 Arquitectura cerrada · 🟡 candidatos pendientes de Gate OSI**

Agentic es un catálogo independiente del catálogo de LLMs. Un elemento no entra en Atlas por ser conocido, popular o útil: primero debe superar el Gate OSI y después los controles de evidencia.

## Flujo canónico

```text
DESCUBRIMIENTO → CATÁLOGO AGENTIC → GATE OSI → EVIDENCIA → ATLAS → ROUTER
```

## Alcance

El catálogo puede registrar:

- `agent`
- `harness`
- `framework`
- `protocol`
- `tool_runtime`
- `sandbox`
- `evaluator`
- memoria, checkpointing, recuperación y observabilidad cuando formen parte del sistema agentivo

Estas entidades no se mezclan con `LLM`, `model_family`, `hardware_profile` ni `benchmark`.

## Identidad mínima

Cada candidato conserva `agentic_id`, nombre canónico, tipo, organización/proyecto, fuente primaria, repositorio cuando exista, versión comprobada, fecha de descubrimiento, licencia, estado OSI, evidencia OSI y fecha de última verificación.

## Gate OSI

El Gate OSI es una **barrera de elegibilidad**, no una puntuación de calidad.

```text
CANDIDATO → IDENTIDAD → FUENTE PRIMARIA → LICENCIA → GATE OSI
                                                  ↓
                                      PASS / UNKNOWN / FAIL
                                                  ↓
                                      EVIDENCIA + QUALITY GATE
                                                  ↓
                                                ATLAS
```

`OSI_FAIL` y `OSI_UNKNOWN` permanecen fuera del Atlas canónico. Una licencia desconocida no se convierte en PASS por inferencia. Tampoco equivalen automáticamente a OSI: open weights, source available, gratuidad, código público sin licencia o documentación abierta.

## Estados

```text
DISCOVERED → IDENTIFIED → OSI_PENDING
                         ↙    ↓      ↘
                      FAIL UNKNOWN   PASS
                       ↓       ↓       ↓
                     FUERA    FUERA  EVIDENCIA
                                      ↓
                                QUALITY GATE
                                      ↓
                                ATLAS_ELIGIBLE
                                      ↓
                                ATLAS_VERIFIED
```

## Relación con Atlas y Router

`AGENTIC CATALOGUE ≠ ATLAS`.

El catálogo conserva el radar y sus estados; Atlas contiene conocimiento aceptado y trazable. El Router/recomendador no debe tratar candidatos `DISCOVERED`, `OSI_PENDING`, `OSI_FAIL` u `OSI_UNKNOWN` como opciones verificadas.

## No concurrencia

Todo workflow que modifique catálogo Agentic o Atlas debe usar exclusivamente `leones-main-writers` y `cancel-in-progress: false`. No se crean escritores paralelos por categoría.

## Cierre

La arquitectura y el contrato de promoción están cerrados. La aplicación del Gate a cada candidato es trabajo de evidencia posterior y no se simula ni se declara completada sin fuentes verificables.
