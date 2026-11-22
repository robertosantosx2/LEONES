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


## Remote audit refresh after NEPENTHES AIPerf stack reconciliation — 2026-11-20 (22:03 UTC)

A fully paginated GitHub API snapshot was taken after merging PRs #260–#262 and retiring superseded NEPENTHES PRs:
- **354 remote branch refs**, **286 unique tip commits**.
- **12 exact-tip duplicate groups**, comprising **80 refs** and **68 excess aliases**; the group membership remains unchanged from the 2026-11-20 classification.
- **42 open pull requests** at snapshot time.
- Among all 68 excess aliases, only `jalon2-evidence-bridge` appears as a head/base ref of an open PR (head of #64). Preserve it and its same-tip historical alias `jalon2-closed`.
- NEPENTHES AIPerf/OTel stack: #159 merged; #160/#161/#165–#173 closed as superseded after comparing branch trees with main. #150 and #156 were also closed as stale snapshots; their useful quickstart/docs were selectively ported to the current INDEX or operational guide. #154 remains draft and explicitly blocked pending a fresh English translation of the current Spanish INDEX.
- PR #261 merged the exact integer UTC epoch-nanosecond fix into the canonical AIPerf importer. PR #262 merged operational NVML/energy/OTLP guides and AIPerf upstream provenance. PR #260 merged the INDEX reconciliation and quickstart.
- No branch alias was deleted, renamed or retargeted. Closed-PR branch refs remain present for provenance/recovery. The 68-alias queue still requires MSI-local upstream/worktree/reflog/stash/unpushed-commit verification before any archive/delete action.
- No local directory, model, cache, evidence bundle, stash or worktree was changed. The MSI inventory phase remains blocked until the workstation is accessible.

## Remote audit refresh after NEPENTHES PR #270/#271 — 2026-11-20

A fresh fully paginated GitHub API inventory was taken after merging LEONES PRs #266, #268, #270 and #271:
- **362 remote branch refs**, **294 unique tip commits**.
- **12 exact-tip duplicate groups**, comprising **80 refs** and **68 excess aliases**. All 12 group SHAs and member names are unchanged from the prior classification; the net increase since the previous 354/286 snapshot is eight branch refs and eight unique tips, not new duplicate groups.
- **41 open pull requests** after PR #271 merged.
- No branch refs were reported as protected by the paginated branch API.
- The only duplicate-tip alias currently appearing as an open PR head remains `jalon2-evidence-bridge` (PR #64). Preserve it and its same-tip historical peer `jalon2-closed`.
- LEONES PR #266 (documentation snapshot), #268 (AIPerf 0.14.0 warmup-summary importer compatibility), #270 (C07 batch NVTX verifier) and #271 (master INDEX reconciliation) are merged. PR #270 passed all eight checks; PR #271 passed all four checks.
- Superseded PRs #267 and #269 were closed after rebuilding their successors from current main. Their remote branch refs remain present for provenance and are not candidates for deletion until the MSI-local ref/worktree/stash/reflog inventory is complete.
- PR #139 remains draft, with its head 66 commits ahead and 436 behind current main at the latest review; it was not retargeted or rebased. PRs #147/#149 remain open backlog. JALON2 #64 remains protected by its open-PR dependency.

No branch alias was deleted, renamed or retargeted. The 68-alias queue remains a review queue, not completed cleanup. The remote snapshot cannot establish local worktree, reflog, stash, dirty-file, unpushed-commit or user handoff dependencies. No local directory, model, cache, evidence bundle, stash or worktree was changed. The MSI inventory phase remains blocked until the workstation is accessible.



## Cross-repository MSI recovery and remote recheck — 2026-11-22

This addendum records GitHub-side work only. No MSI filesystem, local Git checkout, stash, model, cache, or process was accessed or modified during this pass.

### Current LEONES remote inventory

- Paginated branch search returned **372 branch refs**.
- Open-PR search returned **45 open pull requests**.
- The 12 duplicate-tip groups documented in [BRANCH-ALIAS-RECONCILIATION-2026-11-20.md](BRANCH-ALIAS-RECONCILIATION-2026-11-20.md) were rechecked pairwise against their canonical refs: all **68 aliases still point to exactly the same tip SHA** as their respective canonical ref.
- Cross-checking those 68 aliases against all 45 current open PR head/base refs found one live dependency: `jalon2-evidence-bridge` remains the head of open PR #64. No other alias in those groups is currently an open PR head or base.
- The full unique-tip histogram for all 372 refs was not recomputed in this pass; the 12 known duplicate groups are verified, but the 26-ref net increase since the 2026-11-20 snapshot still needs a full tip-level classification.
- No branch was deleted, renamed, or force-updated. The GitHub connector used here does not expose branch-ref deletion, and the local dependency gate remains mandatory.

### NEPENTHES and related PR graph

| PR / ref | Remote finding | Disposition |
|---|---|---|
| LEONES #153 / `feat/nepenthes-nsys-only-20261115` | PR merged. Branch is an ancestor of current `main` (0 ahead, 233 behind). | Merged historical ref; retain until MSI refs/stashes are checked. |
| LEONES #147 / `nepenthes/moe-probes-20261114` | Open; 42 commits ahead of its explicit base `benchmarks/tandem-qwen35-reasoning-battery-2026-11-12`. | Active stacked work; retain. |
| LEONES #149 / `nepenthes/performance-capacity-roadmap-20261114` | Open; base is #147's head. It is 91 commits ahead of #147 with no behind commits. Includes raw Nsight captures, SQLite and reproducibility evidence. | Preserve the stack and evidence; do not retarget or merge out of order. |
| LEONES #273 / `feat/nepenthes-nsys-runtime-thread-join-20261121` | Open against `main`; 7 commits ahead and 11 behind. The change is confined to the Nsight importer and its tests. The PR description reports passing CI; the combined-status endpoint returned no status rows during this audit. | Keep open; physical re-import against the preserved MSI capture remains a separate gate. |
| LEONES #139 / `research/atomic-chat-tensorfold-linux-cuda` | Open draft. PR head is `fb5407616da2cba4dd2f0b2e5ce306a5bf5a5883`; the MSI inventory records a different local checkout HEAD plus staged submodule/gitlink state and a WIP stash. | Do not synchronize or collapse until MSI comparison. |
| LEONES #141 / `feat/pithos-opencl-dense-logits` | Open draft tracking Pithos reliability work. | Retain. |

The #147 → #149 relationship is intentionally stacked and is not a duplicate-branch problem. The historical #153 branch is merged remotely, but its local clone also carries a stash and must not be discarded on remote ancestry alone.

### Cross-repository recovery archives verified on GitHub

The following five independent recovery branches are published. Their manifests and preserved patches were fetched back from GitHub; they are archival branches, not merges into the repositories' integration branches.

| Repository | Recovery ref / commit | Remote verification |
|---|---|---|
| `robertosantosx2/llama.cpp` | `msi-recovery/2026-11-22/llama-cpp-tandem` / `d9ce64500187eaf419f47cedc0ca9d8801892f28` | One archive commit; manifest, worktree patch and untracked-file archive present. Merge base is original Tandem HEAD `f5222f25c18da062ab2b8a2dbbfbf4feae398566`; branch remains 625 commits behind current `master`. |
| `robertosantosx2/TensorFold` | `msi-recovery/2026-11-22/tensorfold-pr1879` / `328d6a1936f69fc4d0718670c6ae53977b6d3efc` | Manifest, 808-path staged inventory, 70,742-line staged patch and unstaged patch are present. The preserved state includes 286 staged deletions and 51,789 staged deleted lines plus one unstaged change. It is not safe to apply or discard wholesale. Its current branch ancestry is divergent from the fork's `main` and from the current `fix/qwen35-cuda-lazy-scratch` ref; no equivalence is assumed. |
| `robertosantosx2/Pithos` | `msi-recovery/2026-11-22/pithos-opencl-validation` / `0c71413bc2730ba484579ddaa95bfe337eab6a71` | Recovery branch is 5 commits ahead of `main`. All four changed source files have identical blob SHAs to `fix/intel-opencl-dense-logits-fail-closed`; the recovery branch additionally carries the manifest and local unstaged patch. Open draft PR #1 remains separate. |
| `robertosantosx2/ODS` | `msi-recovery/2026-11-22/ods-cafe-llama-icd` / `1c1aea2f65fcd33166ce2dc47054951f891b61a0` | One archive commit based on current fork `main`; manifest, commit metadata and 491-line patch verified. Three proposed new files are absent from the open draft PR #6 branch; `model_selection.py` exists there with a different, much larger implementation. Do not apply this patch blindly. |
| `robertosantosx2/ODS` | `msi-recovery/2026-11-22/ods-i18n-react-i18next` / `e88fdb722` | 15 commits ahead of fork `main`; manifest, 14-commit sequence, original status and 69,988-byte working-tree patch verified. The 12 i18n/dependency source files have identical blob SHAs to `feat/dashboard-i18n-es-zh`, although the branch histories differ. The extra local patch is not applied. |

### ODS i18n duplicate-content finding

The 12 relevant tracked files on `feat/dashboard-i18n-es-zh` and the i18n recovery branch were compared by Git blob SHA; all 12 are byte-identical. This is a verified duplicate *content state*, not proof that the branch refs or local worktrees can be removed. The archived working-tree patch contains three uncommitted edits, including dependency changes that remain unreviewed: `react-router-dom` changes from 7.18.4 to `^6.26.0`, `vite` and `vitest` ranges are lowered, and `@zip.js/zip.js` plus two overrides are removed. No dependency downgrade is approved by this record.

### Open integration PRs in related repositories

- ODS #6: open draft Cafe-LLama ICD integration.
- Pithos #1: open draft Intel OpenCL dense-logits failure propagation.
- llama.cpp #15: open draft upstream sync, 32 commits ahead of `master`.
- llama.cpp #9: open draft typed-event contract based on `nepenthes/rc1-upstream-20261119`; it is a separate stacked line and must not be retargeted automatically.
- LEONES #95: open ODS dashboard i18n expansion for Hindi, Korean, Vietnamese and Japanese; distinct from the Spanish/Chinese i18n recovery.

### MSI handoff gates — not executable from GitHub

The remote archive work is complete, but the overall reorganization is not. Before any local cleanup or branch alias deletion, the MSI must provide a fresh read-only inventory of all worktrees, local and remote-tracking refs, upstreams, stashes, reflogs, staged/unstaged/untracked state, submodule gitlinks and exact file hashes. Priority items include:

- LEONES Atomic Chat WIP and its stash; compare local HEAD and staged `.gitmodules`/gitlink state with PR #139.
- Tandem evidence checkout: inspect the untracked affinity A/B script and the staged empty-blob state; do not run the script until reviewed.
- NEPENTHES CLI/importer/validation clones: identify which checkout owns each stash and reconcile the local #153-era state with the merged remote history.
- ODS i18n validation checkout: compare its three modified files with the remote archive patch; do not apply the dependency changes without review.
- ODS Café staging: preserve and inspect the untracked `os` PostScript artifact and its provenance.
- TensorFold PR1879 worktrees: reconcile the 808 staged paths, 286 deletions, unstaged build-file edit, all related worktrees and stashes.
- llama.cpp/Tandem: confirm the local detached source tree, untracked CUDA/MoE files and evidence archive against the published recovery bundle.
- Recheck the Pithos original worktree against the recovery patch; do not infer that the patch makes the local copy disposable.

**Stop condition:** no local directory, branch, stash, model, cache, build output or evidence is authorized for deletion by this remote audit. After the MSI inventory is reconciled, produce a per-item keep / archive / duplicate / obsolete proposal with exact hashes and restoration path. Any destructive cleanup remains a separate, explicit approval step.


The audit branch and draft PR #281 were created after the inventory snapshot above. Post-creation GitHub inventory is therefore **373 branch refs** and **46 open PRs**; the duplicate-tip recheck remains the 68 aliases across the 12 previously documented groups, and PR #281 is not part of those groups.
