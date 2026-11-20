# HDAE adoption checkpoint — LEONES

- Status: **MERGED** into `main`.
- Merge PR: [#237](https://github.com/robertosantosx2/LEONES/pull/237).
- Merge commit: `99835b35ac4b9e5af60244b541a2c8999908719a`.
- PR head: `3ac2a9befb932e1ac4d8c30da32fdd82d0ab02a4`.
- CI evidence on exact PR head: `gate`, `runtime-contracts`, `regression`, and `v1-complete` all completed with `success`; the v1-complete job ran JSON validation, complete Python regression suite, synthetic controlled benchmark, and no-real-model-dependency assertion.
- Upstream origin: https://github.com/gmkurtzer/hdae
- LEONES fork: https://github.com/robertosantosx2/hdae (public fork; parent verified as `gmkurtzer/hdae`).
- Pinned HDAE snapshot: `12d1a3389e74642dddee47a6cc4cb217f55f1144` — https://github.com/robertosantosx2/hdae/tree/12d1a3389e74642dddee47a6cc4cb217f55f1144
- Snapshot policy: consult the pinned commit; do not treat moving `main` as normative or advance the pin without a human-approved review PR. See [HDAE-REFERENCE.md](HDAE-REFERENCE.md).
- Scope: LEONES root and all subprojects. Methodology directive is merged; per-project adoption evidence and index/checkpoint remediation remain staged.
- Canonical master priority index: each project/subproject's explicitly designated INDEX. NEPENTHES: `research/moe/tandem.cpp/NEPENTHES-INDEX.md`. No single canonical INDEX file for every LEONES workstream was identified in the initial tree inventory.
- Governance source: [AGENTS.md](../../AGENTS.md), [HDAE-DIRECTIVE.md](HDAE-DIRECTIVE.md), [HDAE-REFERENCE.md](HDAE-REFERENCE.md).

## Gate 1 — adopt governance

- [x] Create the HDAE directive.
- [x] Establish root AGENTS.md discovery instruction.
- [x] Add durable checkpoint.
- [x] Create and verify public LEONES fork with upstream parent relationship.
- [x] Pin an immutable HDAE commit and document controlled update policy.
- [x] Link directive, reference snapshot and fork from README.
- [x] Review five-file PR diff for scope and internal references.
- [x] Resolve mergeability; GitHub reported mergeable before merge.
- [x] Obtain CI evidence: 4/4 checks success on exact PR head.
- [x] Merge PR #237 into main.

## Gate 2 — recursive subproject adoption audit

- [x] Inventory root and nested AGENTS.md: only root AGENTS.md found in the repository tree.
- [x] Inventory subproject READMEs, INDEX-like files, roadmaps and checkpoints.
- [ ] Inspect every candidate canonical index and resolve overlaps/authority.
- [ ] Audit subproject-specific instructions, checkpoints, acceptance gates, test evidence and MSI-vs-remote responsibilities.
- [ ] Prepare bounded remediation PRs, ordered by canonical master priorities; do not bulk-edit or invent priorities.
- [ ] Record each subproject's adoption evidence and exceptions.

## Evidence / boundaries

The fork API identified `robertosantosx2/hdae` as a public GitHub fork whose parent/source is `gmkurtzer/hdae`. Its `main` ref resolved to the pinned commit when this reference was prepared. Governance changes are documentation-only; they do not install upstream HDAE skills in every tool environment, alter subproject code, close technical issues, or change technical acceptance status. CI success validates the repository workflows on the exact PR head; it is not MSI physical validation.
