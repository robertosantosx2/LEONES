# Contributing to LEONES

Thank you for contributing to **LEONES — Local Ecosystem of Open Neural Expert Systems**.

LEONES is an open ecosystem for reproducible evidence around models, hardware, runtimes, benchmarks, agents, measurements and recommendations. This guide follows the general principles of [contributing.md](https://contributing.md/), adapted to the actual architecture and CI of LEONES.

## 1. What we value

> **Discover, document, verify, measure and preserve provenance. Do not turn a claim into a fact merely by repetition.**

Prefer:

- reproducibility over anecdote;
- primary sources over copied claims;
- evidence over assumptions;
- explicit provenance over undocumented enrichment;
- measurements over estimates when measurements exist;
- focused, reviewable changes over opaque rewrites;
- automation when it improves consistency;
- strict separation between source, evidence, estimation and LEONES measurement.

## 2. Before contributing

1. Search existing documentation, issues, tests and implementations.
2. Check whether the work is already being discussed or implemented.
3. For substantial changes, open an issue describing the problem and proposed solution.
4. Read the relevant architecture, schema and contract documentation before changing data flows.
5. Keep unrelated fixes separate unless they are required for correctness.

Start with:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PILLARS.md`
- `docs/RESULT_SCHEMA.md`
- `docs/SOURCE-DISCOVERY.md`
- `docs/PIPELINE_E2E.md`
- `docs/EVALUACION_AGENTIC_TESTS.md`
- `docs/`
- `tests/`
- `.github/workflows/`

## 3. Ways to contribute

### Code

Features, bug fixes, adapters, runtimes, benchmarks, ingestion, validation, web, CI and automation.

### Knowledge and research

Projects, models, runtimes, benchmarks, datasets and sources; technical findings; primary evidence; contradictory or obsolete information.

### Measurements

Reproducible benchmark runs, scenarios, harnesses, graders and precise hardware/model/quantization/runtime configurations.

### Documentation

Architecture, workflows, onboarding, limitations, knowledge web, navigation and terminology.

### Issues and reviews

Reproducible bugs, proposals, pull-request reviews and challenges to unsupported claims.

## 4. Source, evidence, estimation and measurement

LEONES deliberately keeps these states separate:

- `estimated`: calculation or estimate;
- `reported`: value declared by an external source;
- `observed`: configuration or behaviour observed in an environment;
- `measured`: measurement executed by LEONES;
- `verified`: information that passed the project's quality gate;
- `unknown`: information not sufficiently demonstrated.

Never silently promote one state into another. If a value is inferred, identify it as an inference or estimate. A third-party benchmark remains third-party evidence and is not a LEONES physical measurement unless LEONES actually executed it.

## 5. Knowledge contributions

A knowledge fiche should provide, where applicable:

1. project/source name;
2. canonical URL;
3. category;
4. what it is;
5. problem solved;
6. useful technical description;
7. model/hardware/runtime relationships;
8. licence and openness;
9. evidence and primary sources;
10. limitations;
11. relationship with LEONES;
12. role: inspiration, evidence, implementation reference, discovery source, etc.;
13. version/date when freshness matters.

Discovery does not automatically make a source canonical knowledge. Apply the repository's evidence and quality rules first.

## 6. Benchmarks and measurements

Record whenever applicable:

- exact model and revision;
- format and quantization;
- hardware SKU, RAM/VRAM and relevant capabilities;
- OS and driver/runtime versions;
- inference runtime and version;
- runtime flags/configuration;
- context/input and output length;
- concurrency/batch configuration;
- workload/prompts;
- warm-up and repetitions;
- collected metrics;
- raw/structured evidence;
- limitations.

Do not compare tokens/s without documenting execution conditions.

## 7. Model, runtime, selector and router integrations

Keep the execution tuple explicit:

`model + quantization + runtime + hardware + configuration`

Do not hide runtime assumptions inside model records. A runtime supporting a model does not prove equivalent performance across models or configurations.

For selector/router work preserve the chain:

`candidate selection → runtime selection → execution → grading → benchmark → evidence`

## 8. Code changes

Prefer minimal, readable, deterministic changes covered by tests where practical and compatible with existing contracts. Document public behaviour changes.

Avoid unrelated formatting churn, deletion of historical evidence, hard-coded measured values in selectors, silent schema/semantic changes, unnecessary dependencies and quality-gate bypasses.

## 9. Tests and CI validation

**GitHub Actions are part of the contribution contract.** The workflow set can evolve; inspect `.github/workflows/` and run the checks relevant to the affected area.

The current `contract-tests.yml` workflow performs the following core checks:

```bash
python -m unittest discover -s tests/contracts -p 'test_*.py' -v
python -m pytest tests/contracts/test_freetoken_selector_contract.py -q
python -m pytest tests/contracts/test_knowledge_four_layers.py -q
python -m pytest tests -q
```

It also:

- parses every JSON schema in `schemas/`;
- checks contract-version invariants;
- validates evidence verification states;
- validates router OSI modes;
- validates promotion and Atlas storage invariants;
- requires provenance in evidence storage;
- verifies `tests/contracts/contract-tests.md` exists and is non-empty.

Other current workflows cover areas including Atlas feed/ingestion/prospection/recommendations, agentic A01 contracts, measured benchmarks and daily discovery. Changes affecting those areas must be validated with their corresponding workflows/tests.

For web changes, validate affected pages, navigation and generated/public artefacts.

If a check cannot be run locally, state exactly what was and was not validated. Never claim a test passed unless it was executed.

## 10. Pull requests

A useful pull request states:

### Problem
What problem is being solved?

### Solution
What changed and why this layer is the correct place?

### Evidence
What sources, tests, measurements or observations support it?

### Validation
Which checks actually ran and with what result?

### Risks and limitations
What remains unknown or could regress?

Call out explicitly when contracts, schemas, public data or the recommendation pipeline are affected.

## 11. Data and provenance

When modifying structured knowledge/evidence:

- preserve source URLs and provenance;
- preserve timestamps/versions when relevant;
- retain historical measurements when the distinction matters;
- do not collapse contradictory observations into unexplained values;
- keep estimates, reports, observations and measurements distinguishable;
- prefer explicit `unknown` to invented completeness.

The objective is **trustworthy, traceable data**, not simply more data.

## 12. Web and knowledge publication

The public knowledge web must preserve the project's knowledge layers. A fiche should explain what the source is, what it contributes, what evidence supports the claims and what remains uncertain.

Do not publish a discovery item as established LEONES evidence without the appropriate validation. Prefer canonical external URLs.

## 13. Security and sensitive information

Never commit passwords, API keys, access tokens, private credentials, unnecessary personal data, private benchmark data without permission or proprietary material that cannot legally be redistributed.

For security vulnerabilities, do not publish exploitable details in a public issue; use the project's available private security channel.

## 14. Collaboration and review

Challenge claims, implementation and methodology rather than people. Ask for evidence and prefer reproducible demonstrations over authority or popularity.

Review may consider provenance, methodology, reproducibility, contracts, security, licensing, maintenance cost, knowledge-model impact and recommendation correctness—not merely whether code runs.

## 15. Licensing

By contributing, confirm that you have the right to submit the contribution under the repository's applicable licence. For external code, datasets, documentation or copied material, record licence and provenance before inclusion.

## 16. Contribution workflow

```text
IDEA / PROBLEM
      ↓
SEARCH EXISTING WORK
      ↓
ISSUE / DISCUSSION (when useful)
      ↓
FOCUSED CHANGE
      ↓
SOURCE + PROVENANCE
      ↓
TEST / MEASURE / VALIDATE
      ↓
PULL REQUEST
      ↓
REVIEW
      ↓
MERGE
      ↓
DOCUMENT / PUBLISH / PRESERVE EVIDENCE
```

## 17. Final principle

The most valuable contribution is not necessarily the largest one. A small change that preserves provenance, adds a missing test, reproduces a measurement, documents a runtime limitation or prevents an unsupported claim can be more valuable than a large feature.

**Build it. Measure it. Explain it. Preserve the evidence.**

For general open-source contribution guidance, see [contributing.md](https://contributing.md/).
