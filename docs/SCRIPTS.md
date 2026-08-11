# LEONES scripts

The scripts are intentionally small. Do not make one script responsible for hardware discovery, benchmarking, report generation and GitHub publication at the same time.

## Current target interface

```text
scripts/
├── leones-hardware.py   # What machine is this?
├── leones-model.py      # What model is being tested?
├── leones-infer.py      # How fast/stable is inference?
├── leones-lotb.py       # Can the agent complete LOTB?
├── leones-report.py     # Turn measurements into Markdown
├── leones-publish.py    # Validate and publish a report
└── leones-stats.py      # Aggregate public reports
```

The names describe the responsibility, not the implementation technology.

## 1. `leones-hardware.py`

### One job
Collect the minimum technical description of the current machine.

### It should collect

- CPU model;
- architecture;
- cores/threads;
- RAM;
- GPU and VRAM when available;
- operating system/kernel;
- relevant runtime information.

### It must not collect

- user names;
- home-directory paths;
- serial numbers;
- UUIDs;
- MAC/IP addresses;
- credentials;
- arbitrary personal files.

### Output
A machine description that can be consumed by the report step.

### Example

```bash
python3 scripts/leones-hardware.py
```

## 2. `leones-model.py`

### One job
Describe the exact model being evaluated.

### It should record

- model name;
- format;
- quantisation;
- file size;
- SHA-256 when available;
- source identifier/path only when safe to publish.

### Example

```bash
python3 scripts/leones-model.py ~/models/model.gguf
```

It does not benchmark the model.

## 3. `leones-infer.py`

### One job
Measure inference performance and stability.

### It should measure

- prompt evaluation speed;
- generation speed;
- total elapsed time;
- memory where reliably measurable;
- errors/failures;
- exact backend/version information.

### Example

```bash
python3 scripts/leones-infer.py --model ~/models/model.gguf
```

It does not run LOTB and does not publish results.

## 4. `leones-lotb.py`

### One job
Run the standard agentic task battery against the configured local agent endpoint.

### Tasks

- B01 — memory/locality;
- B02 — files;
- B03 — multistep;
- B04 — recovery;
- B05 — local coding.

### Example

```bash
python3 scripts/leones-lotb.py --endpoint http://127.0.0.1:8080
```

The task runner records success, failure, timing and relevant technical observations. It does not decide whether the result is globally verified.

## 5. `leones-report.py`

### One job
Combine measured inputs into one human-readable Markdown experiment report.

### It should include

- hardware;
- model;
- inference measurements;
- LOTB results;
- software versions/commits;
- parameters;
- observations;
- provenance state.

### Example

```bash
python3 scripts/leones-report.py --output result.md
```

It must not silently invent missing measurements.

## 6. `leones-publish.py`

### One job
Check a report for privacy and structural requirements and publish an accepted report to the repository.

### Validation

At minimum, reject or stop when a report contains obvious:

- credentials/tokens;
- personal email addresses;
- user/home paths;
- serial/UUID/MAC/IP identifiers;
- required technical fields missing.

Publication does not automatically make a result `verified`.

### Example

```bash
python3 scripts/leones-publish.py result.md
```

The exact GitHub authentication mechanism is environment-dependent and must never be stored in the report or source tree.

## 7. `leones-stats.py`

### One job
Aggregate public reports and regenerate statistics/charts.

### It should produce

- report count;
- hardware distribution;
- RAM distribution;
- tok/s distributions;
- LOTB success statistics;
- profile comparisons;
- chart files consumed by the website.

### Example

```bash
python3 scripts/leones-stats.py
```

It should ignore rejected reports and clearly distinguish demo data from real measurements.

## 8. Orchestration

A thin `leones.py` command may call the scripts in sequence:

```text
hardware → model → infer → lotb → report → publish → stats
```

The orchestrator should primarily validate arguments, call the individual steps and pass structured results between them. Domain logic belongs in the individual component.

## Why this structure?

A user who only wants hardware information should not have to run a benchmark. A user who wants an inference benchmark should not have to publish anything. A maintainer who changes the report format should not have to rewrite hardware discovery.

Small scripts make LEONES:

- easier to understand;
- easier to test;
- easier to replace;
- safer to run;
- easier to port between Linux distributions;
- easier to automate with GitHub Actions.

## Implementation rule

If a script starts accumulating unrelated responsibilities, split it before adding more features.
