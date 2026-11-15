# tandem.cpp — preserved source snapshot

This directory preserves the upstream `ewhacc/tandem.cpp` repository as it existed at the pinned commit below.

- Upstream: https://github.com/ewhacc/tandem.cpp
- Upstream commit: `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`
- Snapshot date: 2026-11-03
- Upstream base llama.cpp commit: `f5222f25c` (see `BASE_COMMIT`)
- Upstream license file: `LICENSE` (MIT)
- Main implementation: `tandem.patch`
- Build helper: `build.sh`

## Preservation notes

This directory is a source snapshot, not a Git submodule. The source files and patch are preserved independently of upstream history. The pinned commit is provenance; compare it with upstream before updating.

## Scope

The project is a patch set applied to a specific llama.cpp base revision. It is not a standalone inference engine and should be built in an isolated worktree. No benchmark has been run on the LEONES MSI merely by archiving this source.

## NEPENTHES

NEPENTHES documentation and evidence:
- [Index and validation status](NEPENTHES-INDEX.md)
- [Implementation roadmap and acceptance gates](NEPENTHES-ROADMAP.md)
- [Nsight/CUPTI importer contract and real MSI validation](NEPENTHES-IMPORTER.md)
- [Installer, CLI and capture package](NEPENTHES-CLI.md)
- [Qwen3.5-35B historical capture report](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md)
- [Validation and experimentation campaigns](NEPENTHES-CAMPAIGNS.md)

## Language versions

Spanish is the original and source of truth. The English translation preserves the same structure and document paths on branch [docs/nepenthes-quickstart-index-20261115-en](https://github.com/robertosantosx2/LEONES/tree/docs/nepenthes-quickstart-index-20261115-en). The original Spanish documents are on branch [docs/nepenthes-quickstart-index-20261115](https://github.com/robertosantosx2/LEONES/tree/docs/nepenthes-quickstart-index-20261115).

The instrumented runtime and universal JSONL sink are developed in [Tandem.cpp PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1). LEONES integration is tracked in [PR #150](https://github.com/robertosantosx2/LEONES/pull/150), [#151](https://github.com/robertosantosx2/LEONES/pull/151), [#152](https://github.com/robertosantosx2/LEONES/pull/152), and [#153](https://github.com/robertosantosx2/LEONES/pull/153).
