# Cost Awareness for Hybrid AI — LEONES Research

**Date:** 2026-10-02  
**Area:** LEONES Evolution / ODS / multi-provider hybrid inference  
**Status:** architectural research; not a LEONES measurement

## Objective

ODS hybrid mode may combine local inference with free remote providers, credits and commercial APIs. LEONES should show the user the **expected spend before leaving the local route** and the **actual spend after execution**.

Core rule:

~~~text
PUBLISHED PRICE ≠ ESTIMATED SPEND ≠ ACTUAL CHARGE
ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
~~~

The proposed feature is a **Cost Envelope + Cost Ledger**, integrated with consent, privacy and budgets.

## 1. Best Model for Your Budget

[Best LLM for every budget](https://bestmodelforyourbudget.terrydjony.com/) and [terryds/bestvaluemodel](https://github.com/terryds/bestvaluemodel) compare models using Artificial Analysis data, a 3:1 input/output blended price and a value frontier. The project refreshes data daily and exposes input/output pricing, intelligence, coding, math, tokens/s and TTFT. citeturn3search0

This is an excellent reference for making **cost a first-class model attribute**, but the 3:1 price is a workload assumption, not the price of a concrete user request.

Public discussion around the project highlights an important limitation: token price alone can be misleading because models may consume very different numbers of tokens to complete the same task. Cost-per-task can therefore be more useful for real workloads. citeturn3search5

LEONES should consequently track:

~~~text
cost / token
cost / request
cost / user action
cost / completed task
~~~

## 2. Research landscape

| Source | Contribution | LEONES value |
|---|---|---|
| Best Model for Your Budget | capability/price frontier | High |
| Artificial Analysis | pricing, benchmarks, throughput, latency and task economics | Very high |
| OpenRouter Models API | programmable model/pricing catalog | Very high |
| OpenRouter billing/activity | usage, limits, credits and budgets | Very high |
| Hugging Face Inference Providers | pricing, routing and billing | Very high |
| LiteLLM | multi-provider cost calculation/tracking | Very high |
| Token Tariff | workload, cache, reasoning and scenarios | High |
| LLMWise llm-cost | live pricing and token estimates | High |
| llm-cost-utils | cache-aware accounting | High |
| ai-cost-calculator | multi-source normalization | High |
| llm-cost-tracker | history, OpenTelemetry and budget guards | High |
| ttmgr/llm-cost-calculator | projections and sensitivity | Medium |
| vllm-cost-meter / 2026 methodology | load-dependent serving economics | Very high for future |

The ecosystem has two families:

- **pricing calculators:** what does a unit cost?
- **cost accounting:** what did an execution actually cost?

LEONES needs both.

## 3. Important evidence

### OpenRouter

The models API exposes model, context, modalities, prompt price, completion price, providers and capabilities, with sorting by price, throughput, latency and intelligence. citeturn2search0

OpenRouter also documents usage, credits, limits, routing and service tiers. Cost may depend on prompt/completion, images and reasoning. citeturn2search3turn2search5

**LEONES use:** provider adapter + pricing source + actual usage source.

### Hugging Face Inference Providers

HF centralizes model/provider information and offers pricing, routing and billing. Policies include fastest, cheapest and preferred, while provider pages expose input/output price, context, latency and throughput. citeturn1search0turn1search7turn1search9

**LEONES use:** provider/model registry and effective route pricing.

### LiteLLM

LiteLLM provides completion cost and spend tracking by key, user and team, plus model pricing and cache-aware cost calculation. citeturn2search12turn1search3

**LEONES use:** normalization/accounting within the ODS multi-provider layer.

### Cost accounting projects

Token Tariff models tokens per call, call count, cache hit rate, reasoning overhead and batch pricing. llm-cost-utils separates input, output, cache read and cache write. ai-cost-calculator normalizes model names and usage across sources. llm-cost-tracker adds historical accounting, OpenTelemetry and budget guards.

These are implementation patterns, not necessarily dependencies.

### Local serving economics

The 2026 concurrency-aware inference-cost methodology shows that local infrastructure cost per token depends strongly on utilization and load.

Therefore:

~~~text
local = no API bill
local ≠ zero economic cost
~~~

LEONES should keep provider_cost and local_operational_cost separate.

## 4. Cost model

### Pre-request estimate

~~~text
estimated_cost =
  input_tokens_est / 1,000,000 × input_price
+ output_tokens_est / 1,000,000 × output_price
~~~

Example:

~~~text
4,000 input × $1/M  = $0.004
1,000 output × $5/M = $0.005
estimated            = $0.009
~~~

The UI must label this as an **estimate**, never as an invoice.

### Actual cost

~~~text
actual_cost = provider_reported_usage × effective_price
~~~

Provider-reported usage should be preferred whenever available.

### Cache and reasoning

The schema must distinguish:

~~~text
uncached input
cached input read
cache write
output
reasoning
~~~

Do not assume visible output tokens equal billable output tokens.

### Agents

One user action may generate:

~~~text
user request
 → planner
 → tool
 → model
 → tool result
 → model
 → final
~~~

Therefore:

**cost per user action ≠ cost per API request**

## 5. Cost Envelope

Before a remote request, ODS should show something like:

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

Three levels:

- **Expected:** central estimate.
- **Conservative:** percentile or prudent scenario.
- **Hard ceiling:** only when a real ceiling exists or LEONES can enforce one.

Do not fabricate precision.

## 6. Provider Pricing Registry

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

Result:

~~~yaml
cost_estimate:
  expected: ...
  conservative: ...
  currency: ...
  confidence: high|medium|low|unknown
  status: estimated
~~~

## 7. Price provenance and route identity

Keep:

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

Never store only model + price.

One model may have:

~~~text
model X
 ├── provider A → $0.20/M
 ├── provider B → $0.35/M
 └── provider C → $0.50/M
~~~

Economic identity should therefore be:

~~~text
provider + model + version + route + service tier
~~~

Suggested pricing precedence:

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

Stale prices must be labeled.

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

This makes the transition from local/private AI to remote/proprietary AI explicit.

## 9. User policies

~~~yaml
remote_ai:
  mode: ask
  daily_budget: 1.00
  monthly_budget: 10.00
  per_action_soft_limit: 0.05
  per_action_hard_limit: 0.20
~~~

Modes:

- ASK: request consent above threshold.
- WARN: allow but show projected cost.
- BLOCK: prevent exceeding the limit.
- LOCAL_FIRST: try a compatible local route.
- CHEAPEST_COMPATIBLE: calculate the cheapest compatible route.
- PRIVACY_FIRST: do not send remote data without consent.

These are explicit user policies, not hidden system decisions.

## 10. Cost Ledger

Per request:

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

Per user action:

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

Per period:

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

The ledger must not store prompts, documents, conversations, secrets or API keys.

## 11. Task economics and historical learning

Token price alone may hide task-level differences. LEONES should support:

~~~text
cost / token
cost / request
cost / action
cost / completed task
~~~

For an agent:

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

With enough history:

~~~text
coding output:
P50 = 600
P90 = 1,800
P99 = 5,000
~~~

P50 can drive Expected and P90 Conservative, clearly labeled as historical statistics rather than guarantees.

## 12. ODS integration

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

OpenRouter:

~~~text
models API → pricing registry
chat/completions → usage → actual cost
activity/limits → budget reconciliation
~~~

Hugging Face:

~~~text
model + provider + pricing + throughput + latency + billing context
~~~

Its cheapest policy should be recorded as provider routing policy, not silently adopted as a LEONES decision.

## 13. Future TUI / Dashboard

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

Before:

~~~text
Estimated remote cost: €0.01
Conservative estimate: €0.03
Current daily spend: €0.17
Daily budget: €1.00

Proceed? [Y/n]
~~~

After:

~~~text
Actual cost: €0.0084
Input: 3,812 tokens
Output: 694 tokens
Provider: ...
Model: ...
~~~

## 14. Full architecture

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

## 15. Implementation priority

**P0 — specification**

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

**P3 — intelligence**

- history;
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

## 16. Validation criteria

1. Every price has provenance.
2. Estimated and actual values are clearly separated.
3. Remote execution is not silent when consent is required.
4. Actual cost uses provider usage when available.
5. Retries and fallbacks count.
6. Cache and reasoning charges count when billable.
7. The ledger stores no user content.
8. Stale pricing is labeled.
9. Model versions are not conflated.
10. Actual provider/route is recorded.
11. Economic figures are not presented as performance measurements.
12. Local and remote costs remain separate.

## 17. Sources

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

## Verdict

**LEONES should make cost awareness a first-class dimension of hybrid mode.**

The core loop is:

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

The combination of Best Model for Your Budget, Artificial Analysis, OpenRouter/Hugging Face, LiteLLM and usage accounting is mature enough to justify a real implementation.

The LEONES rule remains:

~~~text
ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
PUBLISHED PRICE ≠ ESTIMATED SPEND ≠ ACTUAL CHARGE
~~~
