# RC1 — Ubuntu physical runbook

> **Use only after the GitHub gates are green.**
>
> This document is intentionally procedural. Ubuntu is for installation, observation, execution and measurement — not architecture design.

## 1. Entry gate

Before touching Ubuntu, verify in GitHub:

- JALÓN 3 remains closed;
- RC1 task contract is frozen;
- fixture is versioned;
- result schema is versioned;
- ODS/Magnitude interface contracts are documented;
- runner/adapters are tested with fixtures/mocks;
- no open design question blocks the first experiment.

## 2. Capture the host first

Record before installing anything:

```text
hostname
uname -a
cat /etc/os-release
lscpu
free -h
lspci
lsblk
python3 --version
git --version
docker --version
docker compose version
```

Do not edit the output. Preserve it as raw host evidence.

## 3. ODS first

Use the exact ODS release/commit selected by LEONES.

Prefer an audited checkout/release over an unreviewed moving target.

Installation must produce:

```text
ods-installation.json
ods-version.txt
ods-status.txt
ods-hardware.txt
```

Then verify the local inference API and the actual model:

```bash
curl -fsS http://localhost:11434/v1/models
```

If the installation uses a different configured host port, use the effective port recorded by ODS rather than assuming `11434`.

## 4. Verify Hermes path

After ODS has reported a healthy inference service:

```text
ODS
 ↓
Hermes Agent
 ↓
OpenAI-compatible API
 ↓
llama-server
 ↓
model
```

The actual endpoint, model name and effective context must be captured from the running configuration.

Do not infer them from the README.

## 5. Smoke test

First prove plain inference:

```text
model list
model identity
one short completion
```

Only after that prove Hermes:

```text
Hermes health
Hermes model/provider configuration
one minimal agentic task
```

Only after both pass should the benchmark start.

## 6. RC1-A01

Run exactly the versioned fixture and task contract.

For each run preserve:

```text
execution_id
started_at
finished_at
hardware
model
runtime
agent
fixture hash
result hash
task_success
wall time
tool calls
errors
recovery
logs
```

Protocol:

```text
1 warm-up
5 measured runs
```

Never overwrite an earlier run.

## 7. Magnitude

Magnitude is tested separately using its documented/native path.

Do not install it merely to make the comparison symmetrical. Install it when the ODS baseline is captured or when its own integration gate is ready.

The first Magnitude question is:

> What exact process/engine serves the model on this release?

Capture the answer from the running system.

## 8. Failure protocol

If anything fails:

```text
STOP
 ↓
collect logs/config/version
 ↓
assign failure layer
 ↓
return to GitHub
 ↓
fix the smallest responsible component
 ↓
repeat
```

Do not redesign several layers in one Ubuntu session.

## 9. Exit gate

Ubuntu work is complete when LEONES has:

```text
[ ] host evidence
[ ] stack version evidence
[ ] hardware evidence
[ ] runtime identity
[ ] model identity
[ ] successful inference
[ ] successful A01
[ ] 1 warm-up
[ ] 5 measured executions
[ ] per-run evidence
[ ] validated aggregate
```

At that point the result can enter the existing JALÓN 3 validation/promotion path and, if accepted, the MANADA publication path.
