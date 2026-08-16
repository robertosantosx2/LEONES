# LEONES — Quality Gate

## Estado

**🟢 Arquitectura funcional cerrada · implementación pendiente**

QUALITY GATE es la capa que determina si una entidad o afirmación dispone de evidencia suficiente para pasar de conocimiento recopilado a conocimiento aceptado por LEONES.

No sustituye al Gate OSI ni a EVIDENCIA: consume sus resultados.

## Flujo canónico

```text
CANDIDATO / AFIRMACIÓN
        ↓
IDENTIDAD
        ↓
EVIDENCIA
        ↓
POLÍTICAS OBLIGATORIAS
        ↓
QUALITY GATE
   ┌────┼─────┐
 PASS REVIEW FAIL
   ↓      ↓     ↓
ATLAS   PEND.  FUERA
```

## Regla fundamental

El Quality Gate **no inventa ni completa datos faltantes**. Si la evidencia no permite sostener una afirmación, el estado debe reflejar esa incertidumbre.

## Dimensiones

### 1. Identidad

- entidad inequívoca;
- versión identificada cuando sea relevante;
- organización/proyecto identificado;
- ausencia de duplicado no resuelto.

### 2. Procedencia

- fuente primaria identificable;
- URL/artefacto conservado;
- fecha de consulta;
- procedencia de cada dato relevante.

### 3. Licencia y apertura

- licencia identificada;
- alcance comprobado;
- Gate OSI superado cuando aplique;
- componentes de terceros considerados.

### 4. Evidencia técnica

- metodología suficiente;
- versión del modelo/software;
- configuración relevante;
- hardware para mediciones físicas;
- separación entre medido, documentado y estimado.

### 5. Reproducibilidad

- procedimiento disponible;
- artefacto o resultado conservado cuando sea posible;
- parámetros suficientes para repetir la prueba;
- limitaciones documentadas.

### 6. Frescura

- fecha de verificación;
- vigencia apropiada al dato;
- detección de evidencia obsoleta;
- revisión necesaria cuando cambien versión, precio, licencia o rendimiento.

### 7. Consistencia

- ausencia de contradicción crítica;
- discrepancias registradas;
- no sobrescritura silenciosa;
- resolución o estado `DISPUTED` cuando proceda.

## Estados

```text
PENDING
PASS
REVIEW
FAIL
DISPUTED
SUPERSEDED
```

`PASS` significa que se cumplen los requisitos definidos para esa clase de dato. No significa que el elemento sea universalmente correcto ni que tenga máxima calidad técnica.

## Clases de evidencia

El gate aplica requisitos diferentes según la afirmación:

| Afirmación | Evidencia preferida |
|---|---|
| licencia | fuente primaria + texto de licencia |
| benchmark | benchmark reproducible + versión/configuración |
| tok/s | medición física reproducible |
| compatibilidad hardware | prueba o evidencia específica |
| capacidad Agentic | integración/versiones verificables |
| precio/TCO | fuente actual y fecha |
| recomendación | conjunto de evidencias + restricciones |

## Evidencia física por modelo

Una estimación no puede superar el gate como medición.

```text
estimación → ESTIMATED
medición reproducible → MEASURED
```

Para afirmaciones de rendimiento por modelo/hardware, si no existe evidencia física suficiente, el dato permanece marcado y no se presenta como medición real.

## Gate por niveles

```text
LEVEL 0 — descubierto
LEVEL 1 — identificado
LEVEL 2 — evidencia básica
LEVEL 3 — verificado
LEVEL 4 — físicamente validado
```

Los niveles describen cobertura de evidencia, no una puntuación de calidad del modelo.

## Promoción a Atlas

```text
Agentic → Gate OSI → Quality Gate → Atlas
LLM     → Evidencia → Quality Gate → Atlas
```

El Quality Gate no puede saltarse el Gate OSI cuando este sea obligatorio.

## Router

El Router solo trata como verificadas las entidades/datos que cumplan el estado requerido. Los estados de incertidumbre deben permanecer visibles en la explicación cuando afecten a la recomendación.

## MANADA

Los resultados generados por una MANADA no pasan automáticamente el gate. La coincidencia de varios participantes no sustituye la evidencia externa o la prueba requerida.

## Observabilidad

Cada evaluación debe conservar, cuando proceda, `trace_id`, `run_id` y referencias a las evidencias usadas.

## Revisión humana

Cuando una afirmación crítica no pueda resolverse automáticamente, el estado será `REVIEW` y se conservará el motivo. La revisión humana no debe borrar la evidencia anterior ni ocultar la incertidumbre.

## No concurrencia

Los evaluadores pueden ejecutar comprobaciones en paralelo, pero la promoción o modificación de registros canónicos utiliza exclusivamente `leones-main-writers` con `cancel-in-progress: false`.

## Criterio de cierre

El Quality Gate queda definido como mecanismo de aceptación de evidencia. La implementación posterior debe parametrizar los requisitos por tipo de entidad/afirmación sin convertir el gate en un score opaco.
