# 🦁 LEONES Atlas

Atlas is the structured knowledge layer used by LEONES to explain recommendations.

## Status

**v0.1 — schema established; data population pending.**

Atlas must not become a copy of an arbitrary model list. A record is useful only
when its provenance and evidence are explicit.

## Canonical record

Each record may describe a model, family, organization, runtime, quantization or
other ecosystem object. The minimum model-oriented record contains:

- identity: name, family, organization and version;
- openness: classification and evidence, never replaced by a numeric score;
- architecture: parameters, context and modality when known;
- artifacts: format, quantization and source;
- execution: runtime/backend compatibility and hardware evidence;
- evaluation: benchmark or LEONES measurement references;
- provenance: source URLs, retrieval date and evidence state;
- lifecycle: active, changed, deprecated or unknown.

## Evidence boundary

Atlas distinguishes at least:

- `reported` — submitted information;
- `reproducible` — enough information to reproduce the claim;
- `verified` — independently checked by LEONES;
- `rejected` — must not enter official aggregates.

A discovery made by Prospector does not automatically become trusted Atlas
knowledge.

## Privacy

Atlas public records must never contain operator identity, hostname, serial
number, UUID, MAC/IP, exact location, credentials, tokens or private paths.

## Next integration

```text
Prospector
   ↓
review + evidence
   ↓
Atlas
   ↓
Router
   ↓
Runtime
```

The Router may use Atlas only when the relevant fact is present and its evidence
state is suitable. Otherwise it must return `unknown` rather than inventing a
recommendation.
