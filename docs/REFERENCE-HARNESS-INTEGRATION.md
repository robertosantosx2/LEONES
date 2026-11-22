# Reference harness integration status

The reference subprojects are now connected to a common LEONES contract.

## Current chain

`llmfit -> Atlas -> JGB/hardware/evidence -> CABE/RULA -> Magnitude/ODS -> Buddy/DeepSeek Harness -> LOTB -> result`

This is intentionally an adapter architecture. Upstream source remains in Git submodules and is not copied into LEONES.

## Implemented in this phase

- common candidate router;
- deterministic ranking with hard gates;
- measured performance preferred over estimates;
- explicit llmfit estimate fields;
- ODS runtime normalization;
- Magnitude profile normalization;
- Buddy task-result normalization;
- DeepSeek Harness task-result normalization;
- offline contract tests;
- integration policy and acceptance gates.

## Not claimed yet

A local smoke run against real ODS/Magnitude/Buddy/DeepSeek Harness is an empirical validation step and must be performed on the target runtime. The adapters themselves do not fabricate measurements when an upstream component is unavailable.

## Reproducibility

The upstream revisions are pinned through `.gitmodules` and the subproject policy. Upgrade only after contract, offline and smoke tests pass.
