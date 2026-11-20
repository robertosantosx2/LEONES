# MSI disk and Git checkout inventory — analysis

Capture: 2026-11-20, approximately 20:10 local time  
Source files: [resumen.txt](resumen.txt), [modelos.tsv](modelos.tsv), [git-checkouts.txt](git-checkouts.txt)  
Machine: Ubuntu MSI workstation; snapshot only. No filesystem operation was performed by this analysis.

## Executive summary

- Root filesystem: 937 GiB total, 709 GiB used, 181 GiB available (80% used).
- `/home/ssantos`: approximately 526 GiB.
- Model-file inventory: 1,931 paths, approximately 298.96 GiB represented.
- Git inventory: 111 checkout/worktree sections (112 headings including the report title), 249 repository/worktree entries, 30 sections with working-tree changes, and 14 stash records.
- The inventory is a point-in-time snapshot. Directory sizes and model-file totals are not additive: nested checkouts, caches, duplicate files and submodules overlap.

## Model storage concentration

Largest top-level contributors in the model-file inventory:

| Location under /home/ssantos | Approx. size |
|---|---:|
| `models` | 73.40 GiB |
| `bitnet-falcon3-10b` | 44.80 GiB |
| `benchmarks` | 36.24 GiB |
| `.local` | 32.83 GiB |
| `modelos` | 27.98 GiB |
| `picchio-data` | 25.70 GiB |
| `colibri-models` | 21.44 GiB |
| `clover-35b-a3b-preview` | 12.92 GiB |
| `Pithos` | 10.34 GiB |

The TSV contains 492 `.gguf`, 93 `.safetensors`, 1,201 `.bin`, 101 `.npy`, 22 `.npz`, 20 `.pth` and 2 `.pt` files. These are file paths and sizes, not a deduplicated content inventory.

### High-value duplicate candidates (not deletion candidates yet)

- `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf` appears twice at 9.94 GiB: under `models/tandem-qwen35` and `benchmarks/qwen3.5-35b-a3b-iq2-xxs`. This is the clearest large duplicate candidate; compare SHA-256 before deciding which copy, if either, can be removed.
- The TSV groups 235 sets by identical basename and byte size. Most are build intermediates (for example Rust `dep-graph.bin`) or small llama.cpp vocabulary assets copied into multiple validation checkouts. Same name and size do not prove identical contents.
- Several vocabulary files appear in many llama.cpp/Tandem validation trees. Reclaiming these is low priority until the source checkout and model-cache behavior are understood.

## Git checkout preservation findings

The report records 111 checkout/worktree sections. Nested submodules and nested repositories are included; the 249 repository entries must not be interpreted as 249 disposable clones.

Highest-risk dirty worktrees:

| Checkout | Snapshot state | Required treatment |
|---|---|---|
| `leones-work/LEONES/experimental/companion-hub` | 2,993 staged deletions on branch `dev` | Preserve; inspect whether this is an intentional sparse/removed tree or destructive staged work. Do not reset/clean. |
| `tensorfold-pr1879-real-validation-20261109/TensorFold` | 809 changed paths: 808 staged plus one unstaged | Preserve all staged/unstaged state and evidence. Do not commit/push this aggregate diff. |
| `build/leones-engine-builds/tandem-cpp/source` | 57 untracked paths; no commits yet on master | Preserve as a separate source/evidence candidate; inspect provenance before adoption. |
| Tandem/llama.cpp validation copies | Several detached checkouts with 39–42 modified paths each | Preserve; reconcile against the canonical Tandem source and recorded benchmark evidence before consolidating. |
| `nepenthes-validation/llama.cpp-pr10` | Six untracked C07 artifacts, including JSONL, SQLite databases and `.nsys-rep` | Preserve byte-for-byte; these are evidence, not disposable build output. |
| `leones-work/LEONES` | Atomic Chat branch 61 commits behind remote, 3 local changes and a WIP stash | Preserve branch, changes and stash; reconcile against PR #139 before any synchronization. |

The report contains 14 stash records. Several are repeated across separate worktrees, but each stash belongs to its own Git directory; do not treat equal stash messages as duplicates.

## Reorganization sequence

1. **P0 — freeze and preserve.** No deletion, reset, clean, prune, branch removal, checkout switch, or stash operation. Preserve the TensorFold anomaly, Companion Hub staged deletions, Tandem modifications, LEONES WIP, and C07 artifacts.
2. **P1 — content-level model deduplication.** Generate SHA-256 for large model files, beginning with the duplicated 9.94 GiB Qwen3.5-35B file. Compare inode/hardlink status, metadata, and references from launch scripts/configs before considering one canonical path.
3. **P1 — classify storage.** Separate canonical model stores, benchmark inputs/results, Hugging Face/TensorFold caches, build outputs, and evidence. Cache/build cleanup is considered only after verifying regeneration and active-process use.
4. **P1 — checkout graph.** Build a canonical map of Git common-dir, worktree path, remote URL, branch/HEAD, ahead/behind, dirty state, nested submodules, untracked evidence, and stashes. Distinguish nested repositories from independent clones.
5. **P2 — remote branch hygiene.** Reconcile the local checkout inventory with the existing remote duplicate-ref and open-PR audit. Exact duplicate remote tips do not prove local worktrees or stashes are disposable.
6. **P2 — reversible consolidation.** Propose one canonical validation checkout per engine plus named evidence/archive locations. Move or remove nothing until hashes, commit reachability, PR dependencies and recovery copies are verified.

## Limits

- This snapshot does not contain file hashes, inode/link information, model usage references, process-open file checks, or a complete Git common-dir identity map.
- The checkout report is a snapshot and may contain nested/repeated paths; it is not sufficient to delete or move directories.
- No cleanup has been performed or authorized by this analysis. The MSI must be consulted only for the missing live checks and any physical moves/deletions after a reviewed plan.


## Qwen3.5-35B duplicate verification — 2026-11-20

The MSI read-only follow-up compared the two `Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf` paths:

| Path | Bytes | Inode | Modification time |
|---|---:|---:|---|
| `models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf` | 10,676,139,840 | 30,949,105 | 2026-11-05 09:55:01 +0100 |
| `benchmarks/qwen3.5-35b-a3b-iq2-xxs/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf` | 10,676,139,840 | 28,340,432 | 2026-10-21 23:51:37 +0200 |

Both SHA-256 values are identical: `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`. The files have distinct inodes on the same device, so they are separate physical files rather than hardlinks. The read-only `lsof` and `fuser` checks reported no process using either path at capture time.

**Finding:** content identity is confirmed; approximately 9.94 GiB is duplicated on disk. This is not yet deletion approval. Before choosing a canonical path, search launch scripts, benchmark manifests, service definitions, symlinks and model registries for both exact paths and their parent directories. Then check whether either path is relied upon by automation or reproducibility instructions. Preserve both until references are reconciled and an explicit cleanup decision is made. No file was moved or deleted.
