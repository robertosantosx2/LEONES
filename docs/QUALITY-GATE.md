# LEONES — Quality Gate

## Estado

**🟢 Contrato cerrado · implementación pendiente**

QUALITY GATE determina si una entidad o afirmación tiene evidencia suficiente para pasar de conocimiento recopilado a conocimiento aceptado por LEONES. Consume los resultados de OSI y EVIDENCIA; no los sustituye.

## Flujo canónico

```text
CANDIDATO / AFIRMACIÓN
        ↓
IDENTIDAD → EVIDENCIA → POLÍTICAS
        ↓
   QUALITY GATE
   ↙    ↓     ↘
PASS  REVIEW   FAIL
 ↓       ↓       ↓
ATLAS  PEND.   FUERA
```

**Regla:** el gate no inventa, completa ni infiere datos faltantes. La incertidumbre se conserva explícitamente.

## Controles

1. **Identidad:** entidad inequívoca, versión relevante, organización/proyecto y duplicados resueltos.
2. **Procedencia:** fuente primaria, URL/artefacto, fecha de consulta y origen de cada dato.
3. **Licencia/apertura:** licencia y alcance comprobados, OSI cuando corresponda y terceros relevantes.
4. **Evidencia técnica:** metodología, versión, configuración, hardware y distinción entre medido/documentado/estimado.
5. **Reproducibilidad:** procedimiento, parámetros, artefactos y limitaciones.
6. **Frescura:** fecha de verificación, vigencia y revisión cuando cambien versión, precio, licencia o rendimiento.
7. **Consistencia:** contradicciones registradas y sin sobrescritura silenciosa.

## Estados

```text
PENDING · PASS · REVIEW · FAIL · DISPUTED · SUPERSEDED
```

`PASS` significa que se cumplen los requisitos definidos para esa clase de dato; no significa calidad máxima ni certeza universal.

## Evidencia según afirmación

| Afirmación | Evidencia preferida |
|---|---|
| Licencia | fuente primaria + texto de licencia |
| Benchmark | benchmark reproducible + versión/configuración |
| Tok/s | medición física reproducible |
| Compatibilidad | prueba o evidencia específica |
| Agentic | integración/versiones verificables |
| Precio/TCO | fuente actual + fecha |
| Recomendación | evidencias + restricciones aplicables |

## Evidencia física por modelo

```text
estimación              → ESTIMATED
medición reproducible   → MEASURED
```

Una estimación de hardware o arquitectura nunca se presenta como medición del modelo concreto. Si falta evidencia física suficiente, el dato permanece marcado como estimado/no verificado.

## Niveles de cobertura

```text
L0  descubierto
L1  identificado
L2  evidencia básica
L3  verificado
L4  físicamente validado
```

Son niveles de cobertura de evidencia, **no puntuaciones de calidad**.

## Promoción

```text
Agentic → Gate OSI → Quality Gate → Atlas
LLM     → Evidencia → Quality Gate → Atlas
```

Cuando OSI sea obligatorio, Quality Gate no puede saltárselo.

## Router y MANADA

El Router solo usa como verificadas las entidades/datos que cumplan el estado requerido y mantiene visibles las incertidumbres relevantes. Las salidas de MANADA no superan automáticamente el gate: el consenso entre agentes no sustituye la evidencia requerida.

## Observabilidad y revisión

Cada evaluación conserva, cuando proceda, `trace_id`, `run_id` y referencias a las evidencias utilizadas. Una afirmación crítica irresuelta queda en `REVIEW`, conservando la evidencia previa y el motivo.

## No concurrencia

Las comprobaciones pueden ejecutarse en paralelo. La promoción o modificación de registros canónicos utiliza exclusivamente `leones-main-writers` con `cancel-in-progress: false`.

## Cierre

El Quality Gate queda definido como mecanismo de aceptación de evidencia. La implementación deberá parametrizar los requisitos por tipo de entidad/afirmación sin convertir el gate en un score opaco.
