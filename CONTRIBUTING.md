# Contributing to LEONES

Thank you for contributing to **LEONES — Local Ecosystem of Open Neural Expert Systems**.

LEONES is an open ecosystem focused on reproducible evidence for local and open AI: models, hardware, runtimes, benchmarks, agents, measurements and recommendations. Contributions are welcome when they improve the quality, traceability, reproducibility or usefulness of that ecosystem.

This document follows the general contribution principles described by [contributing.md](https://contributing.md/), adapted to the architecture and working practices of LEONES.

## 1. What we value

LEONES is built around a simple rule:

> **Discover, document, verify, measure and preserve provenance. Do not turn a claim into a fact merely by repetition.**

Contributions should therefore favour:

- reproducibility over anecdote;
- primary sources over copied claims;
- evidence over assumptions;
- explicit provenance over undocumented enrichment;
- measured results over estimates when measurements exist;
- small, reviewable changes over opaque rewrites;
- automation where it improves consistency;
- clear separation between source, evidence, estimation and LEONES measurement.

## 2. Before contributing

Please first:

1. Search the repository for existing documentation, issues, tests and implementations.
2. Check whether the proposed work is already being discussed or implemented.
3. For substantial changes, open an issue describing the problem and proposed solution before investing in a large implementation.
4. Read the relevant architecture and contract documentation before modifying data flows or public schemas.
5. Keep the scope of a change focused. If you discover an unrelated problem, report it separately unless it is required to make the contribution correct.

Useful starting points include:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PILLARS.md`
- `docs/RESULT_SCHEMA.md`
- `docs/SOURCE-DISCOVERY.md`
- `docs/PIPELINE_E2E.md`
- `docs/EVALUACION_AGENTIC_TESTS.md`
- `docs/` phase and integration documentation
- `tests/`

## 3. Ways to contribute

You can contribute in several ways:

### Code

- implement or improve a feature;
- fix a bug;
- improve an adapter, runtime integration or benchmark;
- improve data ingestion or validation;
- improve the web application;
- improve CI, testing or automation.

### Knowledge and research

- add a relevant project, model, runtime, benchmark, dataset or source;
- improve an existing knowledge fiche;
- document technical findings;
- add primary evidence and provenance;
- identify contradictory or obsolete information.

### Measurements and benchmarks

- contribute reproducible measurements;
- add benchmark scenarios;
- improve benchmark harnesses and graders;
- report hardware, model, quantization, runtime and configuration precisely;
- identify contamination, leakage or methodological weaknesses.

### Documentation

- clarify architecture or workflows;
- improve onboarding;
- document known limitations;
- improve the knowledge web and navigation;
- correct terminology, links or examples.

### Issues and reviews

- report reproducible bugs;
- propose improvements;
- review pull requests;
- challenge unsupported claims constructively;
- identify missing evidence or provenance.

## 4. Source, evidence, estimation and measurement

LEONES deliberately keeps different kinds of information separate.

Do not silently promote one kind of information into another.

Use the project's established terminology where applicable:

- `estimated`: a calculation or estimate;
- `reported`: a value declared by an external source;
- `observed`: a configuration or behaviour observed in an environment;
- `measured`: a measurement executed by LEONES;
- `verified`: information that has passed the project's defined quality gate;
- `unknown`: information that has not been demonstrated sufficiently.

When adding factual information, preserve its origin and status. If a value is inferred, label it as an inference or estimate rather than presenting it as a measured fact.

## 5. Knowledge contributions

When adding a project or source to LEONES knowledge, provide enough information for another contributor to understand why it matters.

Where applicable, a knowledge fiche should cover:

1. project/source name;
2. canonical URL;
3. category;
4. what it is;
5. what problem it solves;
6. how it works at a useful technical level;
7. relevant hardware/runtime/model relationships;
8. licence and openness information when relevant;
9. evidence and primary sources;
10. limitations and caveats;
11. relationship with LEONES;
12. whether it is inspiration, evidence, implementation reference, discovery source or another clearly identified role;
13. date or version when freshness matters.

Do not turn a discovery candidate into canonical knowledge merely because it was discovered. Apply the repository's evidence and quality rules first.

## 6. Benchmarks and measurements

A benchmark contribution should be reproducible by another person.

Record, whenever applicable:

- exact model and revision;
- model format and quantization;
- hardware SKU and relevant memory;
- operating system and relevant driver/runtime versions;
- inference runtime and version;
- runtime configuration and flags;
- context/input length;
- output length;
- concurrency/batch configuration;
- workload or prompts;
- warm-up procedure;
- number of repetitions;
- metrics collected;
- raw or structured evidence;
- known limitations.

Do not compare token/s figures without documenting the workload and execution conditions.

A third-party benchmark remains third-party evidence. It must not be represented as a LEONES physical measurement unless LEONES actually executed the measurement.

## 7. Model and runtime integrations

Keep these concepts separate:

`model + quantization + runtime + hardware + configuration`

An integration should not hide runtime assumptions inside a model record, nor should a runtime claim be treated as proof that every model supported by its API performs equally well.

For selector/router work, preserve the complete chain of evidence and the distinction between candidate selection, runtime selection, execution, grading, benchmark and evidence.

## 8. Code changes

Prefer changes that are:

- minimal and focused;
- readable;
- covered by tests where practical;
- compatible with existing contracts unless the contract itself is intentionally changed;
- documented when they alter public behaviour;
- deterministic where reproducibility matters.

Avoid:

- unrelated formatting churn;
- deleting historical evidence merely to make a result look cleaner;
- hard-coding measured values into selectors;
- silently changing schemas or semantics;
- introducing dependencies without a clear reason;
- bypassing quality gates.

## 9. Tests and validation

Run the most relevant checks before submitting a change.

For Python changes, normally run the repository's documented test suite, for example:

```bash
python -m pytest tests -q
```

For contract or integration changes, run the corresponding contract and integration tests as documented in the repository.

For web changes, validate the affected pages, navigation and generated/public artefacts when applicable.

If you cannot run a required check locally, state that clearly in the pull request and explain what was or was not validated.

Never report a test as passing unless it was actually executed.

## 10. Pull requests

A good pull request should make the following clear:

### Problem

What problem does this change solve?

### Solution

What did you change and why is this the appropriate layer for the change?

### Evidence

What sources, tests, measurements or observations support the change?

### Validation

Which tests or checks were executed, with relevant results?

### Risks and limitations

What remains unknown, what could regress, and what was deliberately left out?

Keep pull requests focused. If a change affects contracts, schemas, public data or the recommendation pipeline, call this out explicitly.

## 11. Data and provenance rules

When modifying structured knowledge or evidence:

- preserve source URLs and provenance;
- preserve timestamps/version information when relevant;
- do not overwrite a previous measurement with a new one when the historical distinction matters;
- do not merge contradictory observations into a single unexplained value;
- keep estimates, reports, observations and measurements distinguishable;
- prefer explicit `unknown` to invented completeness.

The goal is not merely to have more data. The goal is to have **trustworthy, traceable data**.

## 12. Web and knowledge publication

Changes to the knowledge web should preserve the separation between the project's knowledge layers.

A public fiche should explain what the source is, what it contributes to LEONES, what evidence supports the claims, and what remains uncertain.

Do not publish a discovery item as established LEONES evidence without passing the appropriate validation process.

When adding an external project, link to its canonical source whenever possible.

## 13. Security and sensitive information

Do not commit:

- passwords;
- API keys or access tokens;
- private credentials;
- personal data that is not required;
- private benchmark data without permission;
- proprietary material that cannot legally be redistributed.

If you discover a security vulnerability, avoid publishing exploitable details in a public issue. Contact the maintainers through the project's available private security channel.

## 14. Respectful collaboration

LEONES welcomes contributors with different backgrounds and levels of expertise.

Be precise without being hostile. Challenge claims, implementations and methodology rather than people. Assume good faith, ask for evidence, explain disagreements and prefer reproducible demonstrations over authority or popularity.

Contributions may be rejected because of technical, methodological, licensing, security or maintenance concerns. That is part of maintaining a trustworthy open project and is not a judgement on the contributor.

## 15. Licensing

By contributing, you confirm that you have the right to submit the contribution under the repository's applicable licence and that your contribution does not knowingly introduce incompatible third-party material.

When adding external code, datasets, documentation or copied material, document its licence and provenance before inclusion.

## 16. Maintainers and review

Maintainers are responsible for protecting the architecture, evidence quality, reproducibility and long-term maintainability of LEONES.

Review may therefore consider more than whether code works. A contribution can also be evaluated for:

- provenance;
- methodological soundness;
- reproducibility;
- contract compatibility;
- security;
- licensing;
- maintenance cost;
- impact on the knowledge model;
- impact on recommendation correctness.

## 17. A simple contribution workflow

```text
IDEA / PROBLEM
      ↓
SEARCH EXISTING WORK
      ↓
ISSUE / DISCUSSION (when useful)
      ↓
SMALL, FOCUSED CHANGE
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

## 18. Final principle

The most valuable contribution to LEONES is not necessarily the largest one.

A small change that makes an assumption explicit, preserves provenance, adds a missing test, reproduces a measurement, documents a runtime limitation or prevents an unsupported claim can be more valuable than a large feature.

**Build it. Measure it. Explain it. Preserve the evidence.**

For general open-source contribution guidance, see [contributing.md](https://contributing.md/).
