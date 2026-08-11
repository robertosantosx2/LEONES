# LEONES schemas

This page collects the diagrams that explain how the project fits together.

## 1. Whole ecosystem

```text
                         LEONES
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
   KNOWLEDGE             AGENTIC             INFERENCE
       │                    │                    │
     Buddy              harness/tools       model/backend
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                           LOTB
                     B01 B02 B03 B04 B05
                            │
                            ▼
                       metaLEONES
                            │
                 ┌──────────┼──────────┐
                 ▼          ▼          ▼
               GitHub       Web        X
```

## 2. Knowledge survives the stack

```text
Machine A ──┐
Model A ────┤
Backend A ──┤
Harness A ──┤──► Buddy / controlled knowledge
             │                 │
             └─────────────────┘
                               │
                               ▼
Machine B + Model B + Backend B + Harness B
```

The point is not that every component is permanently fixed. The point is that changing a component should not require throwing away the accumulated controlled knowledge.

## 3. Measurement pipeline

```text
                 MACHINE
                    │
                    ▼
             HARDWARE REPORT
                    │
                    ▼
                 MODEL
                    │
                    ▼
             INFERENCE TEST
                    │
                    ├── tok/s
                    ├── memory
                    ├── timing
                    └── errors
                    │
                    ▼
                  LOTB
                    │
             ┌──────┼──────┐
             ▼      ▼      ▼
            B01    B02    ... B05
             │      │          │
             └──────┼──────────┘
                    ▼
                 REPORT
                    │
                    ▼
                VALIDATE
                    │
                    ▼
                PUBLISH
```

## 4. Evidence states

```text
             user report
                  │
                  ▼
              REPORTED
                  │
          enough information?
             ┌────┴────┐
            no        yes
             │          │
             ▼          ▼
          REJECTED  REPRODUCIBLE
                         │
                    verification
                         │
                         ▼
                      VERIFIED
```

A report can remain reproducible without being verified. The states must never be conflated.

## 5. Discovery pipeline

```text
daily discovery
      │
      ▼
new project
      │
      ▼
license / openness check
      │
      ▼
technical relevance
      │
      ▼
local evaluation
      │
      ▼
recommendation
      │
      ▼
possible incorporation
```

LEONES discovers Open projects broadly but prioritises Copyleft candidates.

## 6. UX decision loop

```text
                 RESULT
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       tok/s               task UX
          │                   │
          └─────────┬─────────┘
                    ▼
             STACK ANALYSIS
                    │
                    ▼
       recommendation to user
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       model     backend    harness
          │         │         │
          └─────────┼─────────┘
                    ▼
               re-evaluate
```

The objective is not to maximise one isolated metric. LEONES should be able to tell a user which piece of the stack is worth changing to improve the actual user experience.

## 7. Privacy boundary

```text
LOCAL MACHINE
     │
     ├── technical facts ───────► metaLEONES
     │
     └── personal information ──X  NEVER PUBLISH
```

The report is about the experiment and configuration, not about identifying the operator.

## 8. Automation

```text
GitHub Actions
      │
      ├── daily ──► discovery
      │
      ├── weekly ─► LEONES Weekly
      │
      ├── monthly ► ecosystem report
      │
      └── event ──► result aggregation
                         │
                         ▼
                     web / charts
                         │
                         ▼
                    @metaleones
```

Automation must preserve the same evidence and privacy rules as manual execution.
