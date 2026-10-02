# ODS — Multi-Provider Hybrid Inference / Free-Provider Fallback

**LEONES research track:** ODS evolution  
**Status:** 🟡 research candidate / integration proposal  
**Date:** 2026-10-02

## Summary

This investigation studies an ODS evolution from local/cloud hybrid inference toward a multi-provider routing layer combining local inference, multiple external APIs, and free/no-card providers discovered through services such as freeLLM.

**Architectural principle:** freeLLM is a discovery/catalog source, not an ODS inference backend.

ODS already documents LiteLLM as its API gateway for local/cloud/hybrid modes. The proposed evolution is therefore a provider registry and routing/policy layer above the existing gateway.

## Proposed architecture

```
Applications
     │
     ▼
ODS Router / Policy
     │
     ▼
LiteLLM
     │
 ┌───┼───────────────┐
 ▼   ▼               ▼
Local  Free providers  Paid providers
```

The router should distinguish provider identity from model identity and expose the effective route.

## freeLLM integration

Recommended flow:

```
freeLLM
   │
   ▼
provider/model discovery
   │
   ▼
ODS Provider Registry
   │
   ▼
LiteLLM-compatible configuration
   │
   ▼
ODS routing policy
```

The registry should retain provenance, discovery date, access type, authentication requirements, model identifiers, context limits and known quotas. Provider availability can change, so metadata should be refreshable or pinned.

freeLLM should not be a mandatory runtime dependency.

## Provider registry

Example conceptual record:

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

The final schema should reuse ODS/LiteLLM conventions rather than create an incompatible second format.

## Routing policies

### Local first

1. Try the configured local model.
2. If unavailable or unsuitable, use an approved external provider.
3. Continue through an explicit fallback chain.

### Free-provider fallback

```
local
  ↓
free provider A
  ↓
free provider B
  ↓
free provider C
  ↓
optional paid provider
```

### Privacy first

Only local inference and explicitly approved external providers; no silent external fallback.

### Manual

The user explicitly selects provider and model.

The active policy must be visible. Private data must never leave the machine merely because the local model is busy unless the configured policy permits it.

## Dashboard / selector proposal

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

A model selector should show provider and route separately:

```
Provider       Model                 Route
Local          Qwen3.5 2B            local
Provider A     Model X               external
OpenRouter     Model Y :free         external
```

## Fallback semantics

Record why a route failed:

- endpoint unavailable;
- authentication failure;
- rate limit;
- quota exhausted;
- model unavailable;
- context limit;
- local resource pressure;
- user policy.

Avoid unlimited retries. Expose the final route and fallback reason to Dashboard/observability.

## Privacy boundary

Before external routing, ODS should know the destination provider, model, authentication state, data classification and active user policy.

Hybrid mode must therefore be explicit and auditable.

## LEONES integration

```
discovery
   ↓
provider/model candidate
   ↓
ODS router
   ↓
real execution
   ↓
LEONES benchmark
   ↓
MEASURED
```

Provider claims remain source/evidence/estimated until LEONES executes the route under controlled conditions.

Benchmark records should identify provider, model, route, date/time, model revision when observable, limits, latency, throughput where measurable, failures/retries, data classification and whether execution was local or external.

## Implementation phases

1. **Provider registry** — ODS registry compatible with LiteLLM.
2. **Discovery** — optional freeLLM metadata importer.
3. **Dashboard** — provider/model availability and routing policy.
4. **Router** — explicit local → free-provider → paid-provider chains.
5. **Evidence** — record route selection and fallback events.
6. **LEONES benchmark** — measure local and external routes separately.

## Open questions

1. How much discovery belongs in ODS versus LEONES?
2. Refreshable provider metadata or pinned snapshots?
3. How should quotas/rate limits be represented?
4. How should prompts be classified before external fallback?
5. Which LiteLLM routing capabilities can be reused directly?
6. Should ods/current represent one model or a policy-controlled route?
7. How should fallback events appear in Open WebUI, Portal and Dashboard?

## LEONES status

**Research candidate — integration worth pursuing.**

Recommended separation:

> freeLLM → discovery; ODS registry → provider metadata; LiteLLM → API gateway; ODS routing policy → provider selection; LEONES → independent measurement.

## References

- ODS: https://github.com/Osmantic/ODS
- freeLLM: https://freellm.sh/
- LiteLLM: https://github.com/BerriAI/litellm
