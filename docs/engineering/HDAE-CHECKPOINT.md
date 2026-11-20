# HDAE adoption checkpoint — LEONES

- Status: governance proposal on branch `governance/hdae-directive-20261120`; PR #237 remains open.
- Upstream origin: https://github.com/gmkurtzer/hdae
- LEONES fork: https://github.com/robertosantosx2/hdae (public fork; parent verified as `gmkurtzer/hdae`).
- Pinned HDAE snapshot: `12d1a3389e74642dddee47a6cc4cb217f55f1144` — https://github.com/robertosantosx2/hdae/tree/12d1a3389e74642dddee47a6cc4cb217f55f1144
- Snapshot policy: consult the pinned commit; do not treat moving `main` as normative or advance the pin without a human-approved review PR. See [HDAE-REFERENCE.md](HDAE-REFERENCE.md).
- Scope: LEONES root and all subprojects. Adoption of methodology is project-wide after this directive is accepted; cross-repository adoption remains evidence-based.
- Canonical master priority index: each project/subproject's explicitly designated INDEX. NEPENTHES: research/moe/tandem.cpp/NEPENTHES-INDEX.md.
- Branch: `governance/hdae-directive-20261120`
- PR: https://github.com/robertosantosx2/LEONES/pull/237

## Gate 1 — adopt governance

- [x] Create the HDAE directive.
- [x] Establish root AGENTS.md discovery instruction.
- [x] Add durable checkpoint.
- [x] Create and verify public LEONES fork with upstream parent relationship.
- [x] Pin an immutable HDAE commit and document controlled update policy.
- [x] Link directive, reference snapshot and fork from README.
- [x] Review the five-file PR diff for scope and internal references.
- [ ] Resolve GitHub mergeability state; current API response reports `mergeable=false`.
- [ ] Obtain CI evidence; current HEAD has zero check runs and zero commit statuses reported.
- [ ] Merge PR #237 after the mergeability and required checks gates pass.
- [ ] Audit subprojects for conflicting agent instructions and INDEX/checkpoint presence; create bounded remediation gates (not automatic bulk edits).
- [ ] Establish/refresh project checkpoints where needed.

## Evidence / boundaries

The fork API identified `robertosantosx2/hdae` as a public GitHub fork whose parent/source is `gmkurtzer/hdae`. Its `main` ref resolved to the pinned commit when this reference was prepared. The PR changes governance documentation only; it does not install upstream HDAE skills in every tool environment, alter subproject code, close issues, or change technical acceptance status.
