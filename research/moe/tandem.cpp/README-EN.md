# tandem.cpp — preserved source snapshot

**Language:** [English](README-EN.md) · [Español](README.md)

This directory preserves the upstream `ewhacc/tandem.cpp` repository at the pinned commit below.

- Upstream: https://github.com/ewhacc/tandem.cpp
- Pinned commit: `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`
- Snapshot date: 2026-11-03
- Upstream llama.cpp base: `f5222f25c` (see `BASE_COMMIT`)
- License: MIT (`LICENSE`)
- Main implementation: `tandem.patch`
- Build helper: `build.sh`

## Preservation notes

This is a source snapshot, not a Git submodule. Source files and patches are preserved independently of upstream history. The pinned commit records provenance; compare it with upstream before updating.

## Scope

This is a patch set for a specific llama.cpp base revision, not a standalone inference engine. Build it in an isolated worktree. Archiving this source does not constitute a benchmark on the LEONES MSI.

## NEPENTHES documentation

- [Spanish index](NEPENTHES-INDEX.md) · [English index](NEPENTHES-INDEX-EN.md)
- [Roadmap (ES)](NEPENTHES-ROADMAP.md) · [Roadmap (EN)](NEPENTHES-ROADMAP-EN.md)
- [Campaigns (ES)](NEPENTHES-CAMPAIGNS.md) · [Campaigns (EN)](NEPENTHES-CAMPAIGNS-EN.md)
- [CLI (ES)](NEPENTHES-CLI.md) · [CLI (EN)](NEPENTHES-CLI-EN.md)
- [Importer (ES)](NEPENTHES-IMPORTER.md) · [Importer (EN)](NEPENTHES-IMPORTER-EN.md)
- [Historical Qwen3.5-35B report (ES)](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115.md) · [English report](NEPENTHES-QWEN35-HISTORICAL-REPORT-20261115-EN.md)

The instrumented runtime and universal JSONL sink are developed in [Tandem.cpp PR #1](https://github.com/robertosantosx2/tandem.cpp/pull/1). LEONES integration is tracked in [PR #150](https://github.com/robertosantosx2/LEONES/pull/150), [#151](https://github.com/robertosantosx2/LEONES/pull/151), [#152](https://github.com/robertosantosx2/LEONES/pull/152), and [#153](https://github.com/robertosantosx2/LEONES/pull/153).
