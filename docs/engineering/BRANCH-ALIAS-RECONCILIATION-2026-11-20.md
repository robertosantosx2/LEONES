# Remote branch alias reconciliation — 2026-11-20

## Scope and safety

Read-only classification of paginated GitHub API branch and open-PR listings. Snapshot: **346 branch refs**, **278 unique tips**, **12 duplicate-tip groups**, **80 refs in those groups**, **68 excess aliases**, **57 open PRs**.

Identical tip commits prove only that refs currently point to the same commit. They do not prove a branch is unused: a ref may be a PR head/base, evidence anchor, handoff name or local worktree upstream. No branch was deleted or renamed.

## Exact duplicate-tip groups

| Tip SHA | Branch refs sharing the tip | Count |
|---|---|---:|
| `7764b5bf7c1cdeb2040f93d552fb4c48ea1fd423` | `atlas/empirical-pipeline-integration`, `atlas/empirical-pipeline-v2` | 2 |
| `2dfb408e6638b6ebca0382cdc7cff46462ccd7ec` | `feat/a01-execution-manifest`, `feat/a01-real-runtime`, `feat/a01-runner-wiring`, `feat/a01-runner-wiring-2` | 4 |
| `5018cba701fa5bf9f3adb54b904306af4c660053` | `feat/canirun-adapter`, `feat/canirun-adapter-direct`, `feat/canirun-adapter-direct2`, `feat/canirun-adapter-final`, `feat/canirun-adapter-final2`, `feat/canirun-adapter-final3`, `feat/canirun-adapter-final4`, `feat/canirun-adapter-v2`, `feat/canirun-adapter-v3`, `feat/canirun-adapter-v4`, `feat/canirun-adapter-v5`, `feat/canirun-adapter-v6`, `feat/canirun-adapter-v7`, `feat/canirun-adapter-v8`, `feat/canirun-adapter-v9`, `feat/canirun-adapter-v10` | 16 |
| `f66a49840afc8eea300a093e8a29401e1185df37` | `feat/leones-lab-agent-benchmark-runner`, `feat/leones-lab-agent-v0.4.0-final` | 2 |
| `7f9c606673af4d853c6ae70fbff65efc8f62964b` | `feat/runtime-selection-gate-2`, `feat/runtime-selection-gate-3`, `feat/runtime-selection-gate-final`, `feat/runtime-selection-gate-final2`, `feat/runtime-selection-gate-final3`, `feat/runtime-selection-gate-final4`, `feat/runtime-selection-gate-final5`, `feat/runtime-selection-gate-final6`, `feat/runtime-selection-gate-final7`, `feat/runtime-selection-gate-final8`, `feat/runtime-selection-gate-final9` | 11 |
| `29ef31c2f0d581cd3f0c39903408a2ca7048c480` | `feat/runtime-to-agentic-benchmark-2`, `feat/runtime-to-agentic-benchmark-3`, `feat/runtime-to-agentic-benchmark-4`, `feat/runtime-to-agentic-benchmark-5`, `feat/runtime-to-agentic-benchmark-6`, `feat/runtime-to-agentic-benchmark-7`, `feat/runtime-to-agentic-benchmark-8`, `feat/runtime-to-agentic-benchmark-9` | 8 |
| `73b741bc3a53f6a5ea9d5c08eec5c5da6c4ee384` | `jalon2-closed`, `jalon2-evidence-bridge` | 2 |
| `1718d60029d5f616bead766360e75dfbaea1a14f` | `jalon2-debian-ready`, `jalon2-debian-ready-2`, `jalon2-debian-ready-3`, `jalon2-runtime-execution-v1` | 4 |
| `edfcf5fe43c3110f75d0c432cc863ee1f5f83967` | `jalon2-final-debian-ready`, `jalon2-pre-debian`, `jalon2-pre-debian-unique` | 3 |
| `5c5155fd0cefeb52e50b9fd9bc26159428c7e408` | `jalon4-cpd`, `jalon4-runtime-selection`, `jalon4-runtime-selection-cpd`, `jalon4-runtime-selection-cpd-v1`, `jalon4-runtime-selection-soho`, `jalon4-runtime-selection-soho-v1`, `jalon4-runtime-taxonomy-selection-v1`, `jalon4-runtime-taxonomy-selection-v2`, `jalon4-soho`, `jalon4-soho-final`, `jalon4-soho-runtime-v1` | 11 |
| `bd034bee61c3346fa44d6fddfaecb8beb8228b59` | `rc4-fitllm-recommender-resource`, `rc4-fitllm-recommender-resource2`, `rc4-fitllm-recommender-resource3`, `rc4-fitllm-recommender-resource4`, `rc4-fitllm-recommender-resource5`, `rc4-fitllm-recommender-resource6` | 6 |
| `b1462b4b10788dcc2257bb701160e4a11e3ed484` | `rc4-resource`, `rc4-resource-final`, `rc4-resource-final2`, `rc4-resource-final3`, `rc4-resource-final4`, `rc4-resource-final5`, `rc4-resource-preflight`, `rc4-resource-preflight-v2`, `rc4-resource-x`, `rc4-resource-y`, `rc4-resource-z` | 11 |

## Preservation classification

### Protected — do not delete
- `jalon2-evidence-bridge`: HEAD of open PR #64. Its identical-tip peer `jalon2-closed` is not a safe substitute for the PR head ref.
- `jalon2-closed`: preserve until JALON2 historical evidence and local refs/worktrees are reconciled.
- Any branch used as an open PR head/base or referenced by a release/evidence manifest.

### High-risk historical families — manual review
- `jalon2-*` and `jalon4-*`: milestone/evidence naming; identical tips do not establish interchangeability.
- `rc4-*`: historical branch names only. This inventory does not reactivate RC4 in the product roadmap or authorize deletion. Check issue/PR/document references before archiving.
- `feat/canirun-*`, `feat/runtime-selection-gate-*`, `feat/runtime-to-agentic-benchmark-*`, `feat/a01-*`: likely iteration aliases, but inspect PR history, local upstreams and worktree state before choosing canonical names.

### Lower-risk candidates — still require local checks
- `atlas/empirical-pipeline-*`
- `feat/leones-lab-agent-*`

No canonical name is selected here. Selection must consider PR history, branch protection, commit signatures, local upstreams, worktree refs, tags, release/evidence links and operator handoffs.

## Required checks before any deletion

1. Refresh the full branch and PR inventory immediately before acting.
2. On MSI, inventory `git worktree list --porcelain`, all local and remote-tracking refs, upstream config, stashes, reflogs and dirty/untracked work in every checkout.
3. Search repository docs and evidence manifests for every candidate branch name.
4. Produce a per-ref keep/archive/delete proposal with exact tip SHA, PR references, local dependencies and recovery command.
5. Archive candidates first by preserving tip SHA in a durable tag or bundle and documenting restoration. Delete only after separate explicit approval and second verification.
6. Never rewrite or retarget AIPerf/OTel parent-first chain #159–#173 as a side effect of alias cleanup.

## Result

**Classification completed; deletion not started.** All 68 excess aliases remain protected pending local dependency reconciliation. This is a review artifact, not an instruction to run bulk branch deletion.
