# HDAE adoption checkpoint — LEONES

- Status: **MERGED** into `main`.
- Merge PR: [#237](https://github.com/robertosantosx2/LEONES/pull/237).
- Merge commit: `99835b35ac4b9e5af60244b541a2c8999908719a`.
- PR head: `3ac2a9befb932e1ac4d8c30da32fdd82d0ab02a4`.
- CI evidence on exact PR head: `gate`, `runtime-contracts`, `regression`, and `v1-complete` all completed with `success`.
- Upstream origin: https://github.com/gmkurtzer/hdae
- LEONES fork: https://github.com/robertosantosx2/hdae (public fork; parent verified as `gmkurtzer/hdae`).
- Pinned HDAE snapshot: `12d1a3389e74642dddee47a6cc4cb217f55f1144` — https://github.com/robertosantosx2/hdae/tree/12d1a3389e74642dddee47a6cc4cb217f55f1144
- Snapshot policy: consult the pinned commit; do not treat moving `main` as normative or advance the pin without a human-approved review PR.
- Scope: root governance is merged; subproject-specific adoption and remediation remain in progress.
- Initial audit: [HDAE-SUBPROJECT-AUDIT.md](HDAE-SUBPROJECT-AUDIT.md).
- **Canonical LEONES master INDEX:** `research/moe/tandem.cpp/NEPENTHES-INDEX.md` on `main`; it is the sole source of priority and acceptance. Do not create a parallel root index or elevate auxiliary roadmaps above it.

## Gate 1 — repository-wide HDAE governance

- [x] Fork and verify LEONES-owned HDAE reference.
- [x] Pin immutable HDAE commit and controlled update policy.
- [x] Add root AGENTS.md and governance directive.
- [x] Link governance in README.
- [x] Review PR #237 diff and mergeability.
- [x] All four CI checks passed on exact PR head.
- [x] Merge PR #237 into main.

## Gate 2 — recursive subproject audit

- [x] Inventory complete repository tree for AGENTS.md, README, INDEX-like, roadmap and checkpoint-like files.
- [x] Confirm root AGENTS.md is the only AGENTS.md found.
- [x] Inspect subproject map and representative project documentation.
- [x] Verify NEPENTHES PR #210 merged and correct stale TRACE-ENVELOPE status.
- [x] Fix broken LEONES Lab Agent README links in docs/subprojects/README.md.
- [x] Apply the user-designated LEONES master INDEX authority; no parallel root index created.
- [ ] Complete source/dependency/test/workflow/issue/PR and checkpoint audit for each active subproject.
- [ ] Prepare bounded remediation PRs strictly following the master INDEX.
- [ ] Record per-project HDAE adoption evidence and exceptions.

## Evidence and limits

The tree inventory found no nested AGENTS.md. The initial audit is documentary and not a full code/security/runtime/hardware audit. CI success is not MSI physical validation. The HDAE fork does not imply installation of upstream skills in every execution environment. The current master INDEX priority still requires physical MSI C07/C08 validation for llama.cpp and Tandem.cpp after their remote gates; no such new physical validation was run here.
