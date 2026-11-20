# LEONES repository hygiene and consolidation plan

Audit date: 2026-11-20  
Repository: `robertosantosx2/LEONES`  
Canonical integration branch: `main`

## Operating rules

1. `main` is the only integration baseline. Feature branches must target `main` unless a documented stacked dependency is intentional.
2. Every open PR must have one explicit disposition: active, stacked dependency, blocked on external evidence, superseded, or ready to merge. Never close a PR solely because it is old.
3. A branch is eligible for deletion only after its exact remote SHA is recorded, its commits are reachable from a retained branch or tag, no open PR uses it as head/base, and local inventories confirm no unique unpushed work depends on it.
4. For branches sharing an identical SHA, retain one canonical ref and archive or delete aliases only after the checks above. Equal tip SHA proves identical remote tip, not that local working copies/stashes are disposable.
5. Local checkouts with modifications, untracked evidence, submodules, stashes, detached HEADs, or divergent histories are preservation points. Do not reset, clean, prune, or remove them as part of routine consolidation.
6. Keep source repositories, validation checkouts, evidence bundles, model caches, and build outputs in separate named areas. Do not classify caches or nested Git metadata as independent project clones without inspecting them.
7. Do not update submodule pins or collapse engine forks as a side effect of repository cleanup.

## Remote audit snapshot

GitHub API inventory on 2026-11-20:
- 335 remote branch refs across four pages.
- 267 unique branch-tip commits.
- 12 exact-tip duplicate groups, comprising 80 refs and 68 excess aliases.
- 56 open pull requests at audit time.
- Repository default branch and integration baseline: `main`, SHA `ccba52a3d8cc4308b8917a96db1b5d44528ca1b4` before the C07 v3 documentation merge.

### Exact-tip duplicate groups

Retain the first listed canonical ref unless an open PR or a later documented decision requires another:

| Tip SHA | Canonical ref | Same-tip aliases |
|---|---|---|
| `7764b5bf` | `atlas/empirical-pipeline-integration` | `atlas/empirical-pipeline-v2` |
| `2dfb408e` | `feat/a01-execution-manifest` | `feat/a01-real-runtime`, `feat/a01-runner-wiring`, `feat/a01-runner-wiring-2` |
| `5018cba7` | `feat/canirun-adapter` | `feat/canirun-adapter-direct`, `feat/canirun-adapter-direct2`, `feat/canirun-adapter-final`, `feat/canirun-adapter-final2`, `feat/canirun-adapter-final3`, `feat/canirun-adapter-final4`, `feat/canirun-adapter-v2` through `feat/canirun-adapter-v10` |
| `f66a4984` | `feat/leones-lab-agent-benchmark-runner` | `feat/leones-lab-agent-v0.4.0-final` |
| `7f9c6066` | `feat/runtime-selection-gate-2` | `feat/runtime-selection-gate-3`, `feat/runtime-selection-gate-final`, `feat/runtime-selection-gate-final2` through `feat/runtime-selection-gate-final9` |
| `29ef31c2` | `feat/runtime-to-agentic-benchmark-2` | `feat/runtime-to-agentic-benchmark-3` through `feat/runtime-to-agentic-benchmark-9` |
| `73b741bc` | `jalon2-evidence-bridge` | `jalon2-closed` (keep the PR head ref) |
| `1718d600` | `jalon2-debian-ready` | `jalon2-debian-ready-2`, `jalon2-debian-ready-3`, `jalon2-runtime-execution-v1` |
| `edfcf5fe` | `jalon2-final-debian-ready` | `jalon2-pre-debian`, `jalon2-pre-debian-unique` |
| `5c5155fd` | `jalon4-cpd` | `jalon4-runtime-selection`, `jalon4-runtime-selection-cpd`, `jalon4-runtime-selection-cpd-v1`, `jalon4-runtime-selection-soho`, `jalon4-runtime-selection-soho-v1`, `jalon4-runtime-taxonomy-selection-v1`, `jalon4-runtime-taxonomy-selection-v2`, `jalon4-soho`, `jalon4-soho-final`, `jalon4-soho-runtime-v1` |
| `bd034bee` | `rc4-fitllm-recommender-resource` | `rc4-fitllm-recommender-resource2` through `rc4-fitllm-recommender-resource6` |
| `b1462b4b` | `rc4-resource` | `rc4-resource-final`, `rc4-resource-final2` through `rc4-resource-final5`, `rc4-resource-preflight`, `rc4-resource-preflight-v2`, `rc4-resource-x`, `rc4-resource-y`, `rc4-resource-z` |

These are exact tip duplicates, not permission to delete immediately. Preserve the SHA inventory before any ref mutation.

## Pull request triage

The 2026-11-20 open-PR snapshot contains a deliberately stacked NEPENTHES implementation chain (#159–#173, with numbering gaps). Its base relationships are part of the integration graph; do not retarget each PR independently or merge them out of order. Keep the chain intact until dependency-by-dependency CI and diff review is complete.

Other notable preservation candidates:
- #139 Atomic Chat/TensorFold: retain; local branch is materially behind its remote and local worktrees contain independent uncommitted state.
- #142 kinetic audit/benchmark: retain as research; it has a large exclusive history and a corresponding local checkout.
- #147 and #149 Tandem/MoE: retain as separate evidence/code work until their relationship is reconciled.
- #208 shared-envelope documentation: inspect against the current INDEX before deciding whether it is redundant.
- #241 was closed unmerged; #243 is the merged replacement for the `globalTid` process-identity fix.
- #245 records C07 paired-import v3 and is merged after all four PR checks succeeded.

## Local workspace preservation inventory

The companion MSI inventory dated 2026-11-20 identifies multiple independent worktrees and evidence-bearing paths. Priority preservation set:
- LEONES: `~/LEONES` backup branch `backup/evidence-c07-before-main-20261120`; `~/leones-work/LEONES` Atomic Chat worktree and its WIP stash; `~/leones-work/LEONES-tandem-evidence` Tandem evidence branch.
- NEPENTHES C07: original JSONL, original Nsight SQLite, `.nsys-rep`, prior import DBs and v3 output under `~/nepenthes-validation/llama.cpp-pr10`.
- TensorFold: all PR1879 checkouts, especially the 808-file / 51,789-deletion anomalous worktree, the in-progress conflict checkout, review-cleanup branch, rebase branch, stashes, evidence and build outputs.
- llama.cpp/Tandem: both divergent `f5222f25c` source copies, their untracked CUDA/MoE files, `report1.nsys-rep`, and the separate request-id-zero validation branch.
- Magnitude, ODS, Picchio, Pithos, Open-dCoder and other dirty checkouts listed in the critical inventory.

No local worktree, stash, model, cache, build directory, evidence file, or branch is authorized for deletion by this document.

## Execution gates and outstanding work

- [x] Snapshot remote refs and identify exact-tip duplicates.
- [x] Snapshot open PRs and identify the intentionally stacked NEPENTHES chain.
- [x] Record the C07 v3 import evidence in the master INDEX (LEONES PR #245, merged).
- [ ] Compare each duplicate-tip group with open PR head/base refs and local refs; preserve a recoverable ref before removing any alias.
- [ ] Resolve the stacked PR chain in dependency order; update bases only with explicit diff review.
- [ ] Reconcile local duplicate/divergent worktrees by content hashes and commit graph; no blind clone deletion.
- [ ] Investigate the TensorFold 51,789-deletion worktree against its base and other PR1879 checkouts.
- [ ] Verify C07 v3 bundle, manifest, hashes, SQLite integrity, coverage and `nepenthes verify` on the MSI.
- [ ] Produce a final canonical workspace map and a reversible migration plan before moving or removing local directories.

## Tooling limitation

The GitHub integration available during this audit can enumerate refs and create/update branches and PRs, but does not expose a branch-ref deletion operation. Therefore no remote branches were deleted in this pass. The alias list above is a verified cleanup queue, not a claim that deletion has occurred. Local cleanup must be performed only after the preservation gates and user-side inventory are complete.
