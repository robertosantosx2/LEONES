# Canonical result format

LEONES uses one canonical JSON document as the machine-readable representation of an experiment.

Schema: `schemas/result.schema.json`

## Flow

```text
hardware.py ─┐
model.py ────┼──► result.json ─► report.py ─► result.md ─► publish.py
infer.py ────┤                         │
lotb.py ─────┘                         └────────► human-readable GitHub

result.json ───────────────────────────────────► stats.py / web
```

## Why JSON first?

The Markdown report is intended for people. Statistics, charts and future automation need structured data. Using one canonical result avoids scraping Markdown to reconstruct measurements.

## Required concepts

- `schema_version` — identifies the result format.
- `status` — `reported`, `reproducible`, `verified` or `rejected`.
- `hardware` — anonymised machine characteristics.
- `model` — model identity and provenance information.
- `inference` — raw inference measurements.
- `lotb` — B01–B05 task results.
- `software` — relevant software/version information.
- `notes` — human observations.

## Agentic extension

Agentic evaluations extend the same canonical result rather than creating a parallel result format. The extension must preserve the existing inference and B01–B05 fields while adding task, environment, tool and trajectory evidence.

Recommended concepts:

- `agentic` — metadata for the agentic benchmark execution.
- `benchmark_id` / `benchmark_version` — benchmark identity and frozen version.
- `task_id` / `task_version` — exact task identity.
- `model_version` — exact evaluated model revision where available.
- `runtime` — inference/runtime identity and version.
- `scaffold` — agent harness/scaffold identity and version.
- `environment` — controlled execution environment.
- `tools` — tools exposed to the agent and their versions/capabilities.
- `execution_id` — unique run identifier.
- `outcome` — objective task result and grader output.
- `trajectory` — primary event trace, including tool calls, results, errors and recovery.
- `metrics` — elapsed time, tokens, tool calls, errors, recovery count and cost when observable.
- `safety` — policy/permission violations and safety outcomes.
- `artifacts` — generated or modified artefacts and their verification state.
- `grader` — grader identity/version and method.

Unknown values remain `unknown`/`null` as appropriate. They must not be guessed.

## Outcome versus trajectory

These are intentionally separate. A successful outcome does not imply an efficient, safe or correct trajectory, and a failed outcome does not erase useful evidence about tool use or recovery.

```text
OUTCOME       → did the task succeed?
TRAJECTORY    → how did the agent attempt it?
METRICS       → how much time/tokens/cost/tools?
SAFETY        → did it respect constraints?
ARTIFACTS     → what did it actually produce/change?
```

## Evidence lifecycle

```text
reported → reproducible → verified
               │
               └──────────→ rejected
```

`reported` means submitted. `reproducible` means the information is sufficient for reproduction. `verified` means it has passed the project's independent verification process. `rejected` means it must not contribute to official aggregates.

A result being syntactically valid does not make it verified.

## Privacy boundary

The schema intentionally has no fields for operator identity, email, hostname, serial number, UUID, MAC address, IP address, exact location, credentials or private filesystem paths.

A local implementation may know such values internally, but they must not enter the public result document.

## Demo data

Development/demo results may include `"demo": true`. Production aggregation can explicitly exclude them. Demo data must never be presented as real community evidence.

## Compatibility

Changes to the schema should increment `schema_version` when they affect interpretation. Scripts should fail clearly rather than silently guessing the meaning of unknown fields.
