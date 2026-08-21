# Real runtime adapters

This directory contains adapters that connect a selected LEONES `RuntimePlan` to Agentic Benchmark V1.

## Contract

An adapter must:

1. accept a normalized, execution-authorized runtime plan;
2. identify the exact model revision, quantization, runtime and hardware;
3. execute only the registered tools declared by the task;
4. capture the complete agent trajectory;
5. capture wall-clock and tool-call measurements;
6. collect expected artifacts;
7. invoke the versioned grader;
8. emit a canonical result with `evidence.evidence_type=measured` and an `execution_id`.

The adapter must never turn model-generated text into shell commands or arbitrary executable code.

## A01 reference implementation boundary

The first real adapter should expose only two task tools:

- `lookup_model(model_id)` — read-only lookup against the task catalog;
- `write_report(path, name)` — controlled artifact writer constrained to the task workspace.

A01's canonical task requires `demo-2`, then a report containing `Beta`, with a maximum of two tool calls and no shell access. See `../tasks/A01_tool_use_v1.json`.

The deterministic `smoke_a01.py` remains a harness test. It is not evidence about model quality. A real adapter must populate the actual selected model/runtime/hardware identity and produce primary measured evidence.

## Safety boundary

Adapters are benchmark infrastructure, not general-purpose agents. Tool registration is allow-listed; workspace paths are sandboxed; budgets are enforced; failures are recorded rather than silently retried.
