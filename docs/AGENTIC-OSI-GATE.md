# LEONES — Gate OSI del catálogo Agentic

## Estado

**🟢 Contrato cerrado · 🟡 aplicación candidato a candidato pendiente**

El Gate OSI es obligatorio para todo `agent`, `harness`, `framework`, `protocol`, `tool_runtime`, `sandbox` o `evaluator` que pretenda llegar al Atlas.

## Flujo

```text
INVENTARIO → IDENTIDAD → FUENTE PRIMARIA → LICENCIA → GATE OSI
                                                   ↓
                                      PASS / UNKNOWN / FAIL
                                                   ↓
                                      EVIDENCIA + QUALITY GATE
                                                   ↓
                                                 ATLAS
```

## Regla de promoción

Solo `OSI_PASS` puede continuar al quality gate. `OSI_UNKNOWN` y `OSI_FAIL` permanecen en el catálogo Agentic y no entran en el Atlas canónico.

El gate determina elegibilidad OSI; **no puntúa calidad, rendimiento ni preferencia**.

## Evidencia mínima para PASS

- identidad inequívoca;
- fuente primaria;
- licencia exacta y versión cuando corresponda;
- ubicación del texto de licencia;
- alcance de la licencia;
- evidencia de cobertura del componente catalogado;
- fecha de comprobación;
- componentes de terceros relevantes.

## No es PASS automático

`open weights`, código público sin licencia, `source available`, gratuidad, licencia propietaria, licencias distintas entre software/modelo/datos, documentación abierta con runtime cerrado y forks sin licencia comprobada.

Un protocolo puede tener especificación abierta y, aun así, sus implementaciones se evalúan por separado.

## Estados

```text
OSI_PENDING
OSI_PASS
OSI_FAIL
OSI_UNKNOWN
```

Nunca se infiere `OSI_PASS` por reputación o popularidad.

## Relación con Atlas

```text
OSI_FAIL / UNKNOWN / PENDING → FUERA
OSI_PASS → EVIDENCIA → QUALITY GATE → ATLAS
```

Pasar OSI **no equivale** a estar verificado en Atlas.

## No concurrencia

La aplicación automática utilizará exclusivamente `leones-main-writers` y `cancel-in-progress: false`. No habrá escritores paralelos por categoría.

## Cierre

El contrato queda cerrado. La aplicación candidato por candidato será trabajo de evidencia y no se declarará completada sin fuentes verificables.
