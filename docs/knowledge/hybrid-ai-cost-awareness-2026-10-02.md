# Hybrid AI Cost Awareness — Investigation

**Date:** 2026-10-02  
**Area:** LEONES Evolution / ODS / hybrid inference  
**Status:** Research / proposed architecture

## Purpose

Investigate how LEONES can tell a user the expected spend when ODS leaves local inference and uses proprietary or paid remote AI.

The design must distinguish:

`published price ≠ estimated spend ≠ actual charge`

and:

`estimated ≠ reported ≠ observed ≠ measured`

## Initial reference

[Best Model for Your Budget](https://bestmodelforyourbudget.terrydjony.com/) and its [source repository](https://github.com/terryds/bestvaluemodel) use Artificial Analysis data and a 3:1 input/output blended-price assumption to expose a model value frontier. This is useful as a model-price comparison layer, but the blended price is not a prediction of an individual request.

A central finding is that token price alone is insufficient for task economics: different models may consume different numbers of tokens or generate different numbers of calls to complete the same task. LEONES should therefore support cost per token, request, user action and completed task.

## Research landscape

Relevant sources and projects investigated:

- Best Model for Your Budget — https://bestmodelforyourbudget.terrydjony.com/
- Artificial Analysis — https://artificialanalysis.ai/
- OpenRouter Models API — https://openrouter.ai/docs/api/api-reference/models/get-models
- OpenRouter pricing — https://openrouter.ai/pricing
- Hugging Face Inference Providers — https://huggingface.co/docs/inference-providers/
- Hugging Face pricing — https://huggingface.co/docs/inference-providers/pricing
- LiteLLM — https://github.com/BerriAI/litellm
- LiteLLM spend tracking — https://docs.litellm.ai/docs/proxy/virtual_keys
- Token Tariff — https://github.com/Prajwalsrinvas/token-tariff
- LLMWise llm-cost — https://github.com/LLMWise-AI/llm-cost
- llm-cost-utils — https://github.com/augmentedmind/llm-cost-utils
- ai-cost-calculator — https://github.com/gushwork/ai-cost-calculator
- llm-cost-tracker — https://github.com/danieleschmidt/llm-cost-tracker
- Xidao LLM Cost Calculator — https://github.com/XidaoApi/llm-cost-calculator
- concurrency-aware serving-cost methodology — https://arxiv.org/abs/2606.11690

These fall into two complementary families: pricing calculators and actual cost-accounting systems. LEONES needs both.

## Cost Envelope

Before remote execution, ODS/LEONES should expose an estimate such as:

```text
HYBRID AI
Task: coding
Model/provider: <model> / <provider>

Expected:       €0.01
Conservative:   €0.03
Current daily:  €0.17 / €1.00
Price source:   provider
Pricing age:    2 h
Confidence:     medium

Local route available

Proceed? [Y/n]
```

The three concepts are:

- **Expected:** central estimate.
- **Conservative:** percentile or prudent scenario.
- **Hard ceiling:** only where an enforceable limit exists.

Do not manufacture precision.

## Cost model

For a simple text request:

```text
estimated_cost =
  input_tokens_est / 1,000,000 × input_price
+ output_tokens_est / 1,000,000 × output_price
```

For actual accounting:

```text
actual_cost = provider_reported_usage × effective_price
```

Provider-reported usage should take precedence when available.

The schema should account for:

- uncached input;
- cached input read;
- cache write;
- output;
- reasoning;
- image/audio units;
- request fees;
- service tiers;
- retries;
- fallbacks.

For agents, cost per user action is more meaningful than cost per API call because one action can trigger multiple model requests and tools.

## Provider Pricing Registry

Proposed conceptual schema:

```yaml
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
```

Workload must be separate from pricing:

```yaml
workload:
  input_tokens_estimate: ...
  output_tokens_estimate: ...
  reasoning_tokens_estimate: ...
  cache_hit_tokens_estimate: ...
  requests_estimate: ...
  retries_estimate: ...
  tool_calls_estimate: ...
```

This prevents a provider's published price from being confused with a prediction about how much the user's task will consume.

## Route identity and provenance

The economic identity should be:

```text
provider + model + version + route + service tier
```

A model can have different effective prices through different providers or aggregators.

Every price should retain:

```text
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
```

Suggested precedence:

```text
DIRECT PROVIDER PRICE
       >
ROUTER EFFECTIVE PRICE
       >
AGGREGATOR PRICE
       >
STALE CACHE
       >
NO PRICE
```

Stale data must be explicitly marked.

## Cost Ledger

Per request:

```text
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
```

Per user action:

```text
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
```

Per period:

```text
day / week / month
provider
model
local / remote
estimated
actual
```

The ledger should not store prompts, documents, conversations, secrets or API keys.

## Budget and consent policies

Example:

```yaml
remote_ai:
  mode: ask
  daily_budget: 1.00
  monthly_budget: 10.00
  per_action_soft_limit: 0.05
  per_action_hard_limit: 0.20
```

Potential modes:

- ASK;
- WARN;
- BLOCK;
- LOCAL_FIRST;
- CHEAPEST_COMPATIBLE;
- PRIVACY_FIRST.

These are explicit user policies. Routing should not silently override them.

## Hybrid architecture

```text
USER REQUEST
     |
     v
TASK / PRIVACY / BUDGET
     |
     v
WORKLOAD ESTIMATOR
     |
     +-- historical profile
     +-- token estimate
     +-- agent request estimate
     |
     v
PROVIDER / MODEL RESOLVER
     |
     +-- direct provider
     +-- LiteLLM
     +-- OpenRouter
     +-- Hugging Face
     +-- cached registry
     |
     v
COST ENVELOPE
     |
     +-- expected
     +-- conservative
     +-- confidence
     +-- ceiling
     |
     v
CONSENT / POLICY GATE
     |
     +-- LOCAL
     +-- FREE REMOTE
     +-- PAID REMOTE
              |
              v
           REQUEST
              |
              v
        USAGE EXTRACTOR
              |
              v
          ACTUAL COST
              |
              v
          COST LEDGER
              |
              +-- daily
              +-- monthly
              +-- historical evidence
```

## ODS integration

ODS already has a multi-provider/hybrid direction and LiteLLM integration. The proposed division is:

```text
ODS
 |
 +-- provider routing
 |
 +-- LiteLLM
 |    +-- adapters
 |    +-- model pricing
 |    +-- completion cost
 |
 +-- LEONES Cost Layer
      +-- estimate
      +-- consent
      +-- budget
      +-- actual
      +-- provenance
      +-- evidence
```

OpenRouter and Hugging Face can act as provider-specific sources for pricing and usage. Direct provider APIs should have higher provenance priority when their effective price is available.

## Local cost

Local inference has no external API charge, but it is not necessarily economically free. Serving cost depends on hardware, utilization and workload.

Therefore LEONES should initially show:

```text
REMOTE PROVIDER COST
LOCAL PROVIDER COST = 0 API spend
LOCAL OPERATIONAL COST = separate estimate
```

Do not silently mix electricity, hardware amortization or subscriptions into the remote-provider figure.

## Historical estimation

Once enough executions exist, LEONES can learn task-specific distributions:

```text
coding output:
P50 = 600 tokens
P90 = 1,800 tokens
P99 = 5,000 tokens
```

Expected and conservative estimates can then use historical percentiles, clearly labeled as historical estimates rather than guarantees.

This allows:

```text
future request
   ↓
purpose profile
   ↓
estimated workload
   ↓
provider price
   ↓
estimated spend
```

## Validation criteria

1. Every price has provenance.
2. Estimated and actual cost are clearly separated.
3. Remote execution requiring consent is never silent.
4. Provider usage is preferred for actual accounting.
5. Retries and fallbacks count.
6. Cache and reasoning charges count when billable.
7. The ledger stores no user content.
8. Stale pricing is visible.
9. Model versions are not conflated.
10. Actual provider and route are recorded.
11. Economic measurements are not presented as performance benchmarks.
12. Local and remote costs remain separate.

## Proposed implementation priority

**P0 — specification**
- pricing schema;
- workload schema;
- estimate schema;
- provenance;
- confidence;
- currency.

**P1 — accounting**
- usage;
- actual cost;
- ledger;
- budgets;
- daily/monthly totals.

**P2 — preflight**
- Cost Envelope;
- consent;
- soft/hard limits.

**P3 — intelligence**
- historical profiles;
- percentiles;
- task economics;
- agent prediction;
- cost-aware routing.

**P4 — ODS**
- Dashboard;
- LiteLLM;
- OpenRouter;
- Hugging Face;
- direct providers.

## Key conclusion

LEONES should make **cost awareness a first-class dimension of hybrid inference**, alongside capability, privacy and local availability.

The core loop is:

```text
PRE-REQUEST
  estimated cost
       |
       v
CONSENT / BUDGET GATE
       |
       v
REQUEST
       |
       v
POST-REQUEST
  actual cost
       |
       v
HISTORICAL LEDGER
       |
       v
BETTER FUTURE ESTIMATES
```

The central LEONES accounting rule remains:

```text
ESTIMATED ≠ REPORTED ≠ OBSERVED ≠ MEASURED
PUBLISHED PRICE ≠ ESTIMATED SPEND ≠ ACTUAL CHARGE
```
