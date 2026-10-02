# Cost awareness para IA híbrida — investigación LEONES

**Fecha:** 2026-10-02  
**Área:** LEONES Evolution / ODS / multi-provider hybrid inference  
**Estado:** investigación arquitectónica; no es una medición LEONES

## Objetivo

El modo híbrido de ODS puede combinar modelos locales con proveedores remotos gratuitos, créditos y APIs comerciales. LEONES debe permitir al usuario conocer el **gasto previsto antes de salir de la ruta local** y el **gasto real después de la ejecución**.

Regla fundamental:

~~~text
PUBLISHED PRICE ≠ ESTIMATED SPEND ≠ ACTUAL CHARGE
ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
~~~

La propuesta es un **Cost Envelope + Cost Ledger**, integrado con consentimiento, privacidad y presupuesto.

## 1. Referencia: Best Model for Your Budget

[Best LLM for every budget](https://bestmodelforyourbudget.terrydjony.com/) y [terryds/bestvaluemodel](https://github.com/terryds/bestvaluemodel) comparan modelos usando datos de Artificial Analysis, una tarifa combinada 3:1 input/output y una frontera de valor. El proyecto refresca datos diariamente y conserva precio input/output, inteligencia, coding, math, tokens/s y TTFT. citeturn3search0

Es una referencia excelente para introducir **coste como dimensión del perfil de modelo**, pero su precio 3:1 es una hipótesis de carga, no el coste de una petición concreta.

La discusión pública aporta una advertencia importante: se señala que coste por token puede ser demasiado ingenuo porque distintos modelos pueden usar cantidades muy distintas de tokens para resolver la misma tarea, y que coste por tarea puede ser una métrica más útil. citeturn3search5

Por ello LEONES debe investigar simultáneamente:

~~~text
cost / token
cost / request
cost / user action
cost / completed task
~~~

## 2. Fuentes investigadas

| Fuente | Aporta | Utilidad |
|---|---|---|
| Best Model for Your Budget | frontera capacidad/precio | Alta |
| Artificial Analysis | precios, benchmarks, throughput, latencia y coste por tarea | Muy alta |
| OpenRouter Models API | catálogo y pricing programático | Muy alta |
| OpenRouter billing/activity | usage, límites, créditos y presupuesto | Muy alta |
| Hugging Face Inference Providers | pricing, routing y billing | Muy alta |
| LiteLLM | cálculo y tracking multi-provider | Muy alta |
| Token Tariff | workload, cache, reasoning y escenarios | Alta |
| LLMWise llm-cost | precios live y cálculo por tokens | Alta |
| llm-cost-utils | cache-aware accounting | Alta |
| ai-cost-calculator | normalización multi-fuente | Alta |
| llm-cost-tracker | histórico, OpenTelemetry y budget guards | Alta |
| ttmgr/llm-cost-calculator | proyecciones y sensibilidad | Media |
| vllm-cost-meter / metodología 2026 | coste de serving dependiente de carga | Muy alta para futuro |

Conclusión: hay dos familias. Los **pricing calculators** responden cuánto cuesta una unidad; los sistemas de **cost accounting** responden cuánto costó realmente una ejecución. LEONES necesita ambas.

## 3. Evidencias especialmente relevantes

### OpenRouter

Su API de modelos expone modelo, contexto, modalidades, prompt price, completion price, proveedores y capacidades, y permite ordenar por precio, throughput, latencia e inteligencia. citeturn2search0

También documenta usage, créditos, límites, routing y service tiers; el coste puede depender de prompt/completion, imágenes y reasoning. citeturn2search3turn2search5

**Aplicación LEONES:** provider adapter + fuente de precios + fuente de usage real.

### Hugging Face Inference Providers

HF centraliza modelos/proveedores y ofrece pricing, routing y billing. Su API permite políticas como fastest, cheapest y preferred, y la página de proveedores expone input/output price, contexto, latencia y throughput. citeturn1search0turn1search7turn1search9

**Aplicación LEONES:** provider/model registry y coste efectivo de la ruta.

### LiteLLM

LiteLLM dispone de completion cost y tracking de gasto por key, usuario y equipo, además de información de pricing y caché. citeturn2search12turn1search3

**Aplicación LEONES:** normalización y accounting dentro de la arquitectura multi-provider de ODS.

### Token Tariff y herramientas de accounting

Token Tariff modela tokens por llamada, número de llamadas, cache hit rate, reasoning overhead y batch. llm-cost-utils separa input, output, cache read y cache write. ai-cost-calculator normaliza modelos y usage desde varias fuentes. llm-cost-tracker añade histórico, OpenTelemetry y budget guards.

**Aplicación LEONES:** son patrones para un Cost Provider Registry y un Cost Ledger, no necesariamente dependencias.

### Coste de serving local

La metodología de 2026 sobre concurrencia y coste de inferencia muestra que el coste por token de infraestructura local depende fuertemente de utilización y carga.

Por eso LEONES debe distinguir:

~~~text
local = no API bill
local ≠ economic cost zero
~~~

El objetivo inmediato debe separar provider_cost y local_operational_cost.

## 4. Modelo de coste

### Estimación previa

~~~text
estimated_cost =
  input_tokens_est / 1,000,000 × input_price
+ output_tokens_est / 1,000,000 × output_price
~~~

Ejemplo:

~~~text
4,000 input × $1/M  = $0.004
1,000 output × $5/M = $0.005
estimated            = $0.009
~~~

Debe aparecer como **estimación**, nunca como factura.

### Coste real

~~~text
actual_cost = provider_reported_usage × effective_price
~~~

Cuando existe usage del proveedor debe preferirse frente a reconstruir tokens desde el texto.

### Cache y reasoning

El esquema debe poder distinguir:

~~~text
uncached input
cached input read
cache write
output
reasoning
~~~

No debe asumirse que output visible = output facturable.

### Agentes

Una acción puede producir:

~~~text
user request
 → planner
 → tool
 → model
 → tool result
 → model
 → final
~~~

Por tanto:

**cost per user action ≠ cost per API request**

## 5. Cost Envelope

Antes de una llamada remota, ODS debería mostrar:

~~~text
┌─ HYBRID AI ─────────────────────────────────────────────┐
│ Task: coding                                            │
│ Model: <model> / <provider>                             │
│ Estimated input: 3.2K                                   │
│ Estimated output: 0.8K                                  │
│ Expected:       €0.01                                   │
│ Conservative:   €0.03                                   │
│ Current daily:  €0.17 / €1.00                           │
│ Price source: provider API                              │
│ Pricing age:   2 h                                      │
│ Confidence:    medium                                   │
│ Local route available                                   │
└─────────────────────────────────────────────────────────┘
~~~

Tres niveles:

- **Expected:** estimación central.
- **Conservative:** percentil o escenario prudente.
- **Hard ceiling:** solo si existe un límite real o LEONES puede imponerlo.

No se debe fabricar precisión.

## 6. Provider Pricing Registry

Propuesta:

~~~yaml
provider: openrouter
model: provider/model-id
model_version: pinned-or-null
currency: USD

pricing:
  input_per_1m: ...
  output_per_1m: ...
  cache_read_per_1m: ...
  cache_write_per_1m: ...
  reasoning_per_1m: ...
  request_fee: ...
  image_unit: ...
  audio_unit: ...

metadata:
  source: ...
  source_url: ...
  retrieved_at: ...
  valid_until: ...
  pricing_mode: standard
  service_tier: ...
~~~

Workload:

~~~yaml
workload:
  input_tokens_estimate: ...
  output_tokens_estimate: ...
  reasoning_tokens_estimate: ...
  cache_hit_tokens_estimate: ...
  requests_estimate: ...
  retries_estimate: ...
  tool_calls_estimate: ...
~~~

Resultado:

~~~yaml
cost_estimate:
  expected: ...
  conservative: ...
  currency: ...
  confidence: high|medium|low|unknown
  status: estimated
~~~

## 7. Price provenance y rutas

LEONES debe conservar:

~~~text
source
source_url
provider
retrieved_at
valid_from
valid_until
model_id
model_version
pricing_revision
route
service_tier
~~~

Nunca solamente model + price.

Un modelo puede tener:

~~~text
model X
 ├── provider A → $0.20/M
 ├── provider B → $0.35/M
 └── provider C → $0.50/M
~~~

Por tanto la identidad económica es:

~~~text
provider + model + version + route + service tier
~~~

Jerarquía propuesta de precios:

~~~text
DIRECT PROVIDER PRICE
       >
ROUTER EFFECTIVE PRICE
       >
AGGREGATOR PRICE
       >
STALE CACHE
       >
NO PRICE
~~~

Un precio antiguo debe aparecer como stale.

## 8. Hybrid Router + Cost Guard

~~~text
USER REQUEST
     ↓
TASK / PRIVACY / BUDGET GATE
     ↓
local possible?
   ├── yes → LOCAL ROUTE
   └── no / approved
            ↓
      REMOTE CANDIDATES
            ↓
       COST ESTIMATOR
        ├── within budget → REQUEST
        └── over budget → ASK / BLOCK / LOCAL
                              ↓
                       PROVIDER RESPONSE
                              ↓
                        USAGE EXTRACTOR
                              ↓
                         ACTUAL COST
                              ↓
                      COST LEDGER / BUDGET
~~~

Esto hace explícita la transición de IA local/privada a IA remota/propietaria.

## 9. Políticas de usuario

~~~yaml
remote_ai:
  mode: ask
  daily_budget: 1.00
  monthly_budget: 10.00
  per_action_soft_limit: 0.05
  per_action_hard_limit: 0.20
~~~

Modos:

- ASK: pedir consentimiento al superar umbral.
- WARN: permitir pero informar.
- BLOCK: impedir superar límite.
- LOCAL_FIRST: intentar local compatible.
- CHEAPEST_COMPATIBLE: calcular la ruta compatible de menor coste.
- PRIVACY_FIRST: no enviar datos remotos sin consentimiento.

Son preferencias explícitas, no decisiones ocultas.

## 10. Cost Ledger

Por request:

~~~text
timestamp
provider
model
route
request_id
input_tokens
output_tokens
reasoning_tokens
cached_tokens
cache_write_tokens
latency
status
retry_count
actual_cost
currency
pricing_source
~~~

Por acción:

~~~text
action_id
requests_count
providers_used
models_used
estimated_cost
actual_cost
fallbacks
retries
local_requests
remote_requests
~~~

Por periodo:

~~~text
day
week
month
provider
model
local/remote
estimated
actual
~~~

El ledger no debe guardar prompts, documentos, conversaciones, secretos ni API keys.

## 11. Coste por tarea y aprendizaje histórico

El precio por token puede ser insuficiente. LEONES debe evolucionar hacia:

~~~text
cost / token
cost / request
cost / action
cost / completed task
~~~

Para agentes:

~~~text
TASK: fix issue X

planner  $0.002
search   $0.001
coding   $0.012
review   $0.006
retry    $0.003
----------------
actual   $0.021
~~~

Con historial:

~~~text
coding output:
P50 = 600
P90 = 1,800
P99 = 5,000
~~~

P50 puede alimentar Expected y P90 Conservative, siempre como estadística histórica y no como garantía.

## 12. Integración con ODS

Arquitectura:

~~~text
ODS
 │
 ├── provider routing
 │
 ├── LiteLLM
 │    ├── provider adapters
 │    ├── model pricing
 │    └── completion cost
 │
 └── LEONES Cost Ledger
      ├── estimate
      ├── actual
      ├── budget
      └── evidence
~~~

OpenRouter puede alimentar:

~~~text
models API → pricing registry
chat/completions → usage → actual cost
activity/limits → budget reconciliation
~~~

Hugging Face puede aportar:

~~~text
model + provider + pricing + throughput + latency + billing context
~~~

Su política cheapest debe registrarse como señal de routing, no adoptarse silenciosamente como decisión LEONES.

## 13. TUI / Dashboard futuro

~~~text
┌─ HYBRID AI ────────────────────────────────────────────────┐
│ Task: coding                                               │
│ Privacy: local preferred                                   │
│                                                           │
│ LOCAL                                                     │
│   Qwen ...                         €0 provider cost         │
│                                                           │
│ REMOTE                                                    │
│   Model A / Provider X             ~€0.008 / action        │
│   Model B / Provider Y             ~€0.014 / action        │
│                                                           │
│ Daily remote budget:            €0.17 / €1.00               │
│                                                           │
│ [Run local] [Run remote] [Details] [Budget] [Cancel]       │
└───────────────────────────────────────────────────────────┘
~~~

Antes:

~~~text
Estimated remote cost: €0.01
Conservative estimate: €0.03
Current daily spend: €0.17
Daily budget: €1.00

Proceed? [Y/n]
~~~

Después:

~~~text
Actual cost: €0.0084
Input: 3,812 tokens
Output: 694 tokens
Provider: ...
Model: ...
~~~

Dashboard:

~~~text
Hybrid
 ├── Local
 ├── Remote
 │    ├── provider
 │    ├── model
 │    ├── current price
 │    └── budget
 └── Cost
      ├── today
      ├── month
      ├── per model
      ├── per provider
      └── per purpose
~~~

## 14. Arquitectura completa

~~~text
                         LEONES COST AWARE HYBRID

 USER
   ↓
 PURPOSE / PRIVACY / BUDGET
   ↓
 WORKLOAD ESTIMATOR
   ├── historical profile
   ├── token estimator
   └── agent request estimate
   ↓
 PROVIDER/MODEL RESOLVER
   ├── direct provider
   ├── LiteLLM
   ├── OpenRouter
   ├── Hugging Face
   └── cached registry
   ↓
 COST ENVELOPE
   ├── expected
   ├── conservative
   ├── ceiling
   └── confidence
   ↓
 CONSENT / POLICY GATE
   ├── LOCAL
   ├── FREE REMOTE
   └── PAID REMOTE
          ↓
       REQUEST
          ↓
    USAGE EXTRACTOR
          ↓
      ACTUAL COST
          ↓
      COST LEDGER
          ↓
     daily / month / evidence
~~~

## 15. Prioridad

**P0 — especificación**

- pricing schema;
- workload schema;
- cost estimate schema;
- estimated/reported/observed/measured;
- provenance;
- currency.

**P1 — accounting**

- usage;
- actual cost;
- ledger;
- daily/monthly totals;
- budgets.

**P2 — preflight**

- estimate;
- Cost Envelope;
- consent;
- soft/hard limits.

**P3 — inteligencia**

- histórico;
- percentiles;
- purpose profiles;
- agent prediction;
- cost-aware routing.

**P4 — ODS**

- Dashboard;
- LiteLLM;
- OpenRouter;
- Hugging Face;
- direct providers.

## 16. Criterios de validación

1. Cada precio tiene procedencia.
2. Se distingue estimado de real.
3. Una ruta remota no se ejecuta silenciosamente cuando requiere consentimiento.
4. El coste real usa usage del proveedor cuando existe.
5. Retries y fallbacks cuentan.
6. Cache y reasoning cuentan cuando son facturables.
7. El ledger no guarda contenido.
8. Precios caducados aparecen como stale.
9. Versiones de modelo no se mezclan.
10. Provider/ruta real queda registrada.
11. Economía no se presenta como benchmark de rendimiento.
12. Costes locales y remotos permanecen separados.

## 17. Fuentes

- Best Model for Your Budget — https://bestmodelforyourbudget.terrydjony.com/
- Source repository — https://github.com/terryds/bestvaluemodel
- Artificial Analysis — https://artificialanalysis.ai/
- OpenRouter Models API — https://openrouter.ai/docs/api/api-reference/models/get-models
- OpenRouter pricing — https://openrouter.ai/pricing
- OpenRouter billing — https://openrouter.ai/support/
- Hugging Face pricing — https://huggingface.co/docs/inference-providers/pricing
- Hugging Face Inference Providers — https://huggingface.co/docs/inference-providers/
- LiteLLM — https://github.com/BerriAI/litellm
- LiteLLM spend tracking — https://docs.litellm.ai/docs/proxy/virtual_keys
- Token Tariff — https://github.com/Prajwalsrinvas/token-tariff
- LLMWise llm-cost — https://github.com/LLMWise-AI/llm-cost
- AI Cost Estimator — https://ai-cost-estimator.com/pricing
- Xidao LLM Cost Calculator — https://github.com/XidaoApi/llm-cost-calculator
- llm-cost-utils — https://github.com/augmentedmind/llm-cost-utils
- ai-cost-calculator — https://github.com/gushwork/ai-cost-calculator
- llm-cost-tracker — https://github.com/danieleschmidt/llm-cost-tracker
- deployment cost calculator — https://github.com/timreska/llm-cost-calculator
- concurrency-aware methodology — https://arxiv.org/abs/2606.11690

## Veredicto

**LEONES debería convertir cost awareness en una dimensión de primera clase del modo híbrido.**

La pieza central:

~~~text
PRE-REQUEST
  estimated cost
       ↓
consent / budget gate
       ↓
REQUEST
       ↓
POST-REQUEST
  actual cost
       ↓
historical ledger
       ↓
better future estimates
~~~

La combinación de Best Model for Your Budget, Artificial Analysis, OpenRouter/Hugging Face, LiteLLM y usage accounting proporciona una base madura para una implementación real.

La regla LEONES permanece:

~~~text
ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
PUBLISHED PRICE ≠ ESTIMATED SPEND ≠ ACTUAL CHARGE
~~~
