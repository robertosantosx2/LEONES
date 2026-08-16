# LEONES — Gate OSI del catálogo Agentic

## Estado

**🟢 CONTRATO CERRADO / APLICACIÓN A CANDIDATOS PENDIENTE**

Este gate es obligatorio para cualquier agente, harness, framework, protocolo, runtime, sandbox o evaluador que pretenda incorporarse al Atlas.

## Flujo

```text
INVENTARIO AGENTIC
       ↓
IDENTIDAD + FUENTE PRIMARIA
       ↓
LICENCIA / COPYRIGHT / NOTICE
       ↓
GATE OSI
   ┌───┼────┐
 PASS UNKNOWN FAIL
   ↓     ↓     ↓
 EVID.  FUERA  FUERA
   ↓
QUALITY GATE
   ↓
ATLAS
```

## Regla de promoción

Solo `OSI_PASS` permite continuar hacia el quality gate de Atlas. `OSI_UNKNOWN` y `OSI_FAIL` permanecen en el catálogo Agentic, pero no pueden entrar en el Atlas canónico.

El gate **no evalúa calidad técnica** ni preferencia. Solo determina elegibilidad según el criterio OSI definido por LEONES y la evidencia disponible.

## Evidencia requerida

Para `OSI_PASS` se debe conservar, como mínimo:

- identidad inequívoca del proyecto;
- fuente primaria;
- licencia exacta y versión cuando sea relevante;
- ubicación del texto de licencia;
- alcance de la licencia (software, documentación, modelos, assets u otros componentes);
- evidencia de que el componente que LEONES quiere catalogar está cubierto;
- fecha de comprobación;
- observaciones sobre componentes de terceros cuando puedan cambiar la conclusión.

## Casos que NO son PASS automático

- `open weights`;
- código público sin licencia identificada;
- repositorio público con componentes incompatibles;
- "source available";
- gratuidad;
- licencia comercial propietaria;
- licencia de datos/modelos distinta de la del software;
- documentación abierta con runtime cerrado;
- forks cuyo estado de licencia no esté comprobado.

## Tipos de candidato

El gate se aplica independientemente a:

- `agent`;
- `harness`;
- `framework`;
- `protocol`;
- `tool_runtime`;
- `sandbox`;
- `evaluator`.

Un protocolo puede tener especificación abierta y, aun así, sus implementaciones concretas deben evaluarse por separado.

## Estados

```text
OSI_PENDING
OSI_PASS
OSI_FAIL
OSI_UNKNOWN
```

Nunca se infiere `OSI_PASS` desde la reputación del proyecto.

## Relación con Atlas

```text
CATÁLOGO AGENTIC
   ├── OSI_FAIL    → permanece fuera
   ├── OSI_UNKNOWN → permanece fuera
   ├── OSI_PENDING → permanece fuera
   └── OSI_PASS
          ↓
      EVIDENCIA
          ↓
        ATLAS
```

La promoción a Atlas exige además superar los quality gates de identidad/evidencia correspondientes. Pasar OSI **no equivale** a quedar verificado en Atlas.

## No concurrencia

La aplicación automática del gate deberá escribir mediante el único grupo escritor permitido por LEONES: `leones-main-writers`, con `cancel-in-progress: false`.

## Criterio de cierre

El contrato del gate queda cerrado. La aplicación candidato por candidato se realizará como trabajo de evidencia, sin inventar resultados y sin saltarse el gate para ningún elemento del inventario.
