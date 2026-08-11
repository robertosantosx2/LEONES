# LEONES reengineering

## Decision

LEONES is being re-engineered around **small, clear, composable scripts**.

This is an implementation decision. It does not replace the conceptual architecture or the frozen experimental principles.

## Before

A script that tries to:

- inspect hardware;
- identify a model;
- start inference;
- run LOTB;
- create charts;
- publish to GitHub;
- and update the website

is difficult to understand, test and trust.

## After

Each script answers one question:

| Script | Question |
|---|---|
| `leones-hardware.py` | What machine am I running on? |
| `leones-model.py` | What exact model am I testing? |
| `leones-infer.py` | How does inference perform? |
| `leones-lotb.py` | Can the agent complete the standard tasks? |
| `leones-report.py` | How do I describe this experiment? |
| `leones-publish.py` | Is this report safe and valid to publish? |
| `leones-stats.py` | What do the public reports show? |

A thin orchestrator may call these in order.

## Why

### Clarity

A new contributor can understand a script from its name and its documentation.

### Testability

Each component can be tested without running the complete stack.

### Replaceability

A hardware detector can be replaced without touching LOTB. A new report format can be introduced without changing inference measurement.

### Safety

The publication boundary becomes explicit. Privacy checks happen before GitHub publication.

### Automation

GitHub Actions can invoke one capability at a time.

### Portability

Small commands are easier to adapt to Debian, Ubuntu, Red Hat and other supported Linux environments.

## Dependency direction

```text
hardware ─┐
model ─────┤
infer ─────┤
lotb ──────┤──► report ─► publish ─► stats/web
           │
           └── shared data formats
```

Scripts should not create circular dependencies.

## Data over hidden state

Whenever practical, one script should produce a structured result that the next script can consume. The Markdown report is the public human-readable representation; internal structured data may be used to avoid fragile text parsing.

## No silent invention

If a required measurement is missing, the script must say so. It must not fill the value with a guess merely to produce a complete-looking report.

## No silent publication

A generated result is not automatically a verified result. Publication and verification are separate concepts.

## Documentation standard

Every script must have a companion explanation covering:

1. purpose;
2. non-goals;
3. inputs;
4. outputs;
5. dependencies;
6. examples;
7. privacy considerations;
8. error conditions;
9. relationship with the other scripts.

The goal is that someone unfamiliar with the original project conversation can understand the complete workflow by reading `docs/ARCHITECTURE.md`, `docs/SCRIPTS.md` and `docs/SCHEMAS.md`.

## Frozen concepts remain frozen

This reengineering does not remove or weaken:

- Libre/Open priority;
- Copyleft priority;
- Buddy as a central candidate;
- consumer hardware focus;
- separation of inference and agentic evaluation;
- LOTB B01–B05;
- 10 tok/s usability threshold;
- metaLEONES privacy rules;
- evidence states;
- public GitHub as canonical project source.

The goal is to make the implementation easier to understand while preserving the project's accumulated knowledge.
