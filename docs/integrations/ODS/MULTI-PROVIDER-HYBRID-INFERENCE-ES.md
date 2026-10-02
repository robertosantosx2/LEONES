# ODS — Inferencia híbrida multi-proveedor / fallback de proveedores gratuitos

**Línea de investigación LEONES:** evolución de ODS  
**Estado:** 🟡 candidato de investigación / propuesta de integración  
**Fecha:** 2026-10-02

## Resumen

Esta investigación estudia la evolución de ODS desde la inferencia local/cloud híbrida hacia una capa de routing multi-proveedor que combine inferencia local, múltiples APIs externas y proveedores gratuitos/sin tarjeta descubiertos mediante servicios como freeLLM.

**Principio arquitectónico:** freeLLM es una fuente de descubrimiento/catálogo, no un backend de inferencia de ODS.

ODS ya documenta LiteLLM como gateway API para modos local/cloud/hybrid. La evolución propuesta es por tanto un registro de proveedores y una capa de políticas/routing sobre el gateway existente.

## Arquitectura propuesta

```
Aplicaciones
     │
     ▼
ODS Router / Policy
     │
     ▼
LiteLLM
     │
 ┌───┼────────────────┐
 ▼   ▼                ▼
Local  proveedores     proveedores
       gratuitos       de pago
```

El router debe distinguir identidad del proveedor e identidad del modelo y mostrar la ruta efectiva.

## Integración de freeLLM

Flujo recomendado:

```
freeLLM
   │
   ▼
descubrimiento proveedor/modelo
   │
   ▼
ODS Provider Registry
   │
   ▼
configuración compatible con LiteLLM
   │
   ▼
política de routing ODS
```

El registro debe conservar procedencia, fecha de descubrimiento, tipo de acceso, autenticación, identificadores de modelos, límites de contexto y cuotas conocidas. La disponibilidad de los proveedores puede cambiar, por lo que los metadatos deben poder actualizarse o fijarse en snapshots.

freeLLM no debería ser una dependencia obligatoria de ejecución.

## Registro de proveedores

Ejemplo conceptual:

```
provider: example-provider
type: openai-compatible
base_url: https://...
authentication: api_key
free_access: true
no_card: true
models:
  - id: example-model
    context: 32768
provenance:
  source: freeLLM
  discovered_at: 2026-10-02
```

El esquema definitivo debe reutilizar las convenciones de ODS/LiteLLM y no crear un segundo formato incompatible.

## Políticas de routing

### Local primero

1. Intentar el modelo local configurado.
2. Si no está disponible o no es adecuado, usar un proveedor externo aprobado.
3. Continuar por una cadena de fallback explícita.

### Fallback de proveedores gratuitos

```
local
  ↓
proveedor gratuito A
  ↓
proveedor gratuito B
  ↓
proveedor gratuito C
  ↓
proveedor de pago opcional
```

### Privacidad primero

Solo inferencia local y proveedores externos aprobados explícitamente; sin fallback externo silencioso.

### Manual

El usuario selecciona explícitamente proveedor y modelo.

La política activa debe ser visible. Los datos privados nunca deben salir del equipo simplemente porque el modelo local esté ocupado, salvo que la política configurada lo permita.

## Selector / Dashboard propuesto

```
Inference mode
  ○ Local
  ● Hybrid
  ○ Cloud

Routing policy
  ● Local first
  ○ Free providers first
  ○ Privacy first
  ○ Manual

Providers
  ✓ Local — llama-server
  ✓ Provider A — configured
  ✓ Provider B — configured
  □ Provider C — not configured
```

El selector debe mostrar proveedor y ruta por separado:

```
Proveedor       Modelo                 Ruta
Local           Qwen3.5 2B            local
Provider A      Model X               external
OpenRouter      Model Y :free         external
```

## Semántica del fallback

Registrar el motivo de fallo:

- endpoint no disponible;
- fallo de autenticación;
- rate limit;
- cuota agotada;
- modelo no disponible;
- límite de contexto;
- presión de recursos locales;
- política del usuario.

Evitar reintentos ilimitados. Exponer la ruta final y el motivo del fallback al Dashboard/observabilidad.

## Frontera de privacidad

Antes del routing externo, ODS debe conocer proveedor destino, modelo, estado de autenticación, clasificación de datos y política activa del usuario.

El modo híbrido debe ser explícito y auditable.

## Integración con LEONES

```
descubrimiento
   ↓
candidato proveedor/modelo
   ↓
ODS router
   ↓
ejecución real
   ↓
benchmark LEONES
   ↓
MEASURED
```

Las afirmaciones de los proveedores permanecen como fuente/evidencia/estimación hasta que LEONES ejecute la ruta bajo condiciones controladas.

Los benchmarks deben identificar proveedor, modelo, ruta, fecha/hora, revisión del modelo cuando sea observable, límites, latencia, throughput cuando sea medible, fallos/reintentos, clasificación de datos y si la ejecución fue local o externa.

## Fases de implementación

1. **Registro de proveedores** — registro ODS compatible con LiteLLM.
2. **Descubrimiento** — importador opcional de metadatos de freeLLM.
3. **Dashboard** — disponibilidad de proveedores/modelos y política de routing.
4. **Router** — cadenas explícitas local → proveedor gratuito → proveedor de pago.
5. **Evidencia** — registrar selección de ruta y fallbacks.
6. **Benchmark LEONES** — medir por separado rutas locales y externas.

## Preguntas abiertas

1. ¿Cuánto descubrimiento debe pertenecer a ODS frente a LEONES?
2. ¿Metadatos actualizables o snapshots fijados?
3. ¿Cómo representar cuotas y rate limits?
4. ¿Cómo clasificar prompts antes del fallback externo?
5. ¿Qué capacidades de routing de LiteLLM pueden reutilizarse directamente?
6. ¿Debe ods/current representar un modelo o una ruta gobernada por política?
7. ¿Cómo mostrar fallbacks en Open WebUI, Portal y Dashboard?

## Estado LEONES

**Candidato de investigación — integración que merece continuar.**

Separación recomendada:

> freeLLM → descubrimiento; ODS registry → metadatos; LiteLLM → gateway API; política ODS → selección; LEONES → medición independiente.

## Referencias

- ODS: https://github.com/Osmantic/ODS
- freeLLM: https://freellm.sh/
- LiteLLM: https://github.com/BerriAI/litellm
