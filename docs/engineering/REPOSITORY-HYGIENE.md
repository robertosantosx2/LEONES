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


## Remote recheck after PR #246 — 2026-11-20

A second GitHub API snapshot was taken after the plan was merged:
- 338 remote branch refs and 56 open PRs.
- All 12 previously identified duplicate-tip groups remain exact duplicates, with the same 80 refs and 68 excess aliases.
- Cross-checking every alias against all 56 open PR head/base refs found one live dependency: `jalon2-evidence-bridge` is the head of open PR #64. Preserve this ref; `jalon2-closed` is its same-tip alias, but neither ref is eligible for cleanup until the local-ref/worktree inventory is reconciled.
- None of the other 67 excess aliases is currently used as an open PR head or base. This is only a remote-PR check, not deletion authorization: local refs, tags, reflogs, stashes, and unpushed work remain unverified.
- No branch was deleted. The integration available here still does not expose branch-ref deletion.

The 338-ref count includes the new documentation branches created during this audit; it is not directly comparable to the 335-ref initial snapshot without accounting for those additions.


## MSI inventory and remote recheck — 2026-11-20 (20:10–20:22 CET)

The MSI read-only inventory is now merged via [LEONES PR #250](https://github.com/robertosantosx2/LEONES/pull/250), merge commit `d01066cd05adebddbed526d6b8bb6659d3832e74`. Raw files live in `docs/inventory/msi/`; the detailed interpretation and preservation-first order are in `docs/inventory/msi/ANALYSIS.md`. The NEPENTHES master INDEX was updated in the same PR and remains the single source of truth for NEPENTHES priorities.

MSI snapshot findings: root filesystem 937 GiB total / 709 GiB used / 181 GiB available (80%); `/home/ssantos` approximately 526 GiB; model inventory 1,931 paths / 298.96 GiB; 111 checkout/worktree sections, 30 dirty sections and 14 stash records. Counts overlap nested repositories, caches and repeated files and are not additive. No physical cleanup was performed.

A fresh GitHub API recheck after the inventory merge found:
- 341 remote branch refs, 273 unique tip commits.
- The same 12 exact-tip duplicate groups, 80 refs total and 68 excess aliases.
- 55 open pull requests.
- Only `jalon2-evidence-bridge` among the duplicate aliases is used as an open PR head/base (PR #64 head). Retain it; no alias deletion is authorized by this recheck.
- The MSI inventory branch is merged and remains as an audit ref. TensorFold checkout-forensics PR #249 is closed unmerged; its branch is not considered integrated evidence and the local TensorFold anomaly remains preserved by the MSI inventory.

### Updated local preservation gates

The MSI inventory supersedes earlier partial checkout lists where they differ. In particular, preserve without mutation:
- `~/tensorfold-pr1879-real-validation-20261109/TensorFold`: 808 staged paths plus one unstaged path (809 total); do not publish its aggregate diff.
- `~/leones-work/LEONES/experimental/companion-hub`: 2,993 staged deletions; inspect intent before any reset or restore.
- `~/nepenthes-validation/llama.cpp-pr10`: original JSONL, Nsight SQLite, `.nsys-rep` and all import DBs.
- `~/build/leones-engine-builds/tandem-cpp/source`: untracked source tree with no initial commit; preserve until provenance and canonical source relationship are established.
- LEONES/Tandem/llama.cpp dirty or detached validation worktrees and the 14 stash records; same stash message across worktrees does not mean same stash object.

### Next safe sequence

1. On MSI, run read-only SHA-256 and inode checks for the two 9.94 GiB Qwen3.5-35B GGUF copies, then check references in manifests/scripts. Do not delete either copy yet.
2. Capture Git common-dir and per-worktree branch/HEAD/upstream/ahead-behind metadata for the dirty preservation set; verify each stash belongs to its reported Git directory.
3. Reconcile the current 55 open PR dependency graph, especially stacked NEPENTHES #159–#173, before changing any base/head or closing PRs.
4. Only after hashes, commit reachability, PR dependencies and recovery copies are verified, propose reversible local consolidation. No reset, clean, prune, branch deletion, stash mutation, model deletion or directory move is authorized by this audit.

**Tooling boundary:** branch-ref deletion is still unavailable through the current GitHub integration. The 68 aliases remain a reviewed queue, not completed cleanup.


## Remote audit refresh after Qwen3.5-35B deduplication — 2026-11-20

A fresh paginated GitHub API inventory after LEONES PR #253 merged:
- 346 remote branch refs, 278 unique tip commits.
- 12 exact-tip duplicate groups (80 refs total, 68 excess aliases).
- 57 open pull requests in the audit snapshot.
- Preserve the JALON2 evidence refs `jalon2-evidence-bridge` (head of open PR #64) and `jalon2-closed` until local refs/worktrees are reconciled.
- PR #253 merged as `faa1ac5b2f3dd21c3fbd44e85130602da96aeae3`; its four required checks passed. The MSI Qwen3.5-35B duplicate removal and approximately 9.94 GiB recovery are recorded in the master NEPENTHES INDEX and MSI analysis.
- The AIPerf/OTel chain #159–#173 remains stacked: #159 is draft; #162 and #164 are closed unmerged; #165 is the active adapter successor. No child PR was retargeted or merged.

No branch aliases or local Git worktrees were deleted. The current GitHub integration does not expose branch-ref deletion, and the remote snapshot cannot establish local reflog, stash, unpushed-work or dirty-worktree dependencies. The 68-alias queue remains pending local preservation checks and an explicitly reviewed deletion-capable operation.


## Remote audit refresh after PR #256 — 2026-11-20 (20:59 UTC)

A new fully paginated GitHub API snapshot was taken after merging the duplicate-tip classification document:
- **348 remote branch refs**, **280 unique tip commits**.
- The same **12 exact-tip duplicate groups**, comprising **80 refs** and **68 excess aliases**; all group SHAs and member refs are unchanged from the 2026-11-20 classification in `docs/engineering/BRANCH-ALIAS-RECONCILIATION-2026-11-20.md`.
- **56 open pull requests** at snapshot time.
- LEONES PR #256 (branch-alias classification) merged into `main` as `e5a5329dcdbc831bf0e723e0c17fcf4a90d3bfa4`; all four required checks completed successfully.
- PR #257 reconciled the NEPENTHES master INDEX and merged as `d71aab6a3e0f5cf5b8007a5386aa4db700c4b8cd`; all four required checks completed successfully.
- The AIPerf/OTel NEPENTHES chain #159–#173 remains stacked parent-first. Do not retarget or merge children independently.
- `jalon2-evidence-bridge` remains the head of open PR #64 and must be retained. Keep `jalon2-closed` as a historical evidence ref until local dependencies are reconciled.

No branch alias was deleted, renamed, or retargeted. The 68-alias list remains a remote cleanup queue only: local upstreams, worktrees, reflogs, stashes, unpushed commits and dirty evidence remain unverified without the MSI inventory/recheck. No local directory, model, cache, evidence bundle, stash or worktree was changed.


## Remote audit refresh after PR #257/#258 merges — 2026-11-20 (22:44 UTC)

A further fully paginated GitHub API snapshot was taken after the INDEX reconciliation and hygiene snapshot PRs merged:
- **350 remote branch refs**, **282 unique tip commits**.
- The same **12 exact-tip duplicate groups**, comprising **80 refs** and **68 excess aliases**. The member names and tip groupings remain unchanged from the classification in `docs/engineering/BRANCH-ALIAS-RECONCILIATION-2026-11-20.md`.
- **55 open pull requests** at snapshot time.
- PR #257 (NEPENTHES INDEX reconciliation) merged as `d71aab6a3e0f5cf5b8007a5386aa4db700c4b8cd`; its four required checks passed.
- PR #258 (this hygiene snapshot) merged as `bd10ba797744553dd92d8a943b9fe6b507c81333`; all four required checks passed.
- LEONES issue #212 was refreshed to reflect completed host many-to-many propagation, importer guard and producer-side NVTX implementation (Tandem.cpp PR #5/#7; LEONES #218/#219). Remaining gates are physical paired C07 validation and separate C08 overhead measurement; issue remains open.
- The AIPerf/OTel stack #159–#173 remains parent-first. Current bases form a linear chain from #159 on `main` through #160/#161/#165–#173; preserve this order and do not retarget/merge children independently.
- `jalon2-evidence-bridge` remains the head of open PR #64 and must be retained. Keep `jalon2-closed` as a historical evidence ref until local dependencies are reconciled.

No branch alias was deleted, renamed, or retargeted. The 68-alias list remains a remote cleanup queue only: local upstreams, worktrees, reflogs, stashes, unpushed commits and dirty evidence remain unverified without the MSI inventory/recheck. No local directory, model, cache, evidence bundle, stash or worktree was changed.
