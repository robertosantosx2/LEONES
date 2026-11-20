# AGENTS.md — LEONES HDAE governance

This repository and every subproject follow the LEONES adaptation in [docs/engineering/HDAE-DIRECTIVE.md](docs/engineering/HDAE-DIRECTIVE.md).

**Normative HDAE method reference:** consult the LEONES-owned, pinned snapshot documented in [docs/engineering/HDAE-REFERENCE.md](docs/engineering/HDAE-REFERENCE.md), specifically commit `12d1a3389e74642dddee47a6cc4cb217f55f1144` of https://github.com/robertosantosx2/hdae. Do not use the moving `main` branch as the fixed reference. The original upstream is https://github.com/gmkurtzer/hdae and is consulted only when evaluating a proposed, human-approved update.

Before substantial work:
1. Read the pinned HDAE reference instructions and the LEONES HDAE directive.
2. Read the project/subproject's canonical master INDEX and current durable checkpoint; inspect repository status, dependencies and overlap recursively.
3. Derive or prepare bounded gates with objective acceptance criteria, evidence and stop conditions. Follow gates already approved by the master INDEX without redundant approval.
4. Develop remotely in GitHub first (branch, commit, PR, CI). Use local hardware only for requested/necessary validation, physical capture, benchmarks, builds or reproducibility checks.
5. Iterate implementation/tests/diagnosis within scope; stop on material ambiguity, risk, scope expansion, or human decision.
6. Record evidence and status distinctions; update the canonical INDEX and checkpoint when acceptance is demonstrated.

Do not claim CI, hardware, benchmark, causal, security, or acceptance results without evidence. The master INDEX is the source of priority/acceptance; the LEONES directive defines the method. Preserve human authority and do not execute destructive or consequential actions without explicit authorization.
