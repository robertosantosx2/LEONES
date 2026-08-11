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

## Privacy boundary

The schema intentionally has no fields for operator identity, email, hostname, serial number, UUID, MAC address, IP address, exact location, credentials or private filesystem paths.

A local implementation may know such values internally, but they must not enter the public result document.

## Evidence boundary

A result being syntactically valid does not make it verified. The publication state and verification state are explicit concepts and must not be inferred from the existence of a file.

## Compatibility

Changes to the schema should increment `schema_version` when they affect interpretation. Scripts should fail clearly rather than silently guessing the meaning of unknown fields.
