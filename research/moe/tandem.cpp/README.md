# tandem.cpp — preserved source snapshot

This directory preserves the upstream `ewhacc/tandem.cpp` repository as it existed at the pinned commit below.

- Upstream: https://github.com/ewhacc/tandem.cpp
- Upstream commit: `e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683`
- Snapshot date: 2026-11-03
- Upstream base llama.cpp commit: `f5222f25c` (see `BASE_COMMIT`)
- Upstream license file: `LICENSE` (MIT)
- Main implementation: `tandem.patch`
- Build helper: `build.sh`
- Benchmark scripts and GSM8K data: `bench/`

## Preservation notes

This is a source snapshot copied into LEONES, not a Git submodule. The source files and patch are therefore preserved independently of the upstream repository's future availability or history changes. The upstream commit is pinned for provenance; compare it with the original URL before updating this snapshot.

## Scope

The project is a patch set applied to a specific llama.cpp base revision. It is not a standalone inference engine and should be built in an isolated worktree. See the upstream README for usage, supported expert tensor layouts, runtime flags, benchmark methodology, and limitations.

No benchmark has been run on the LEONES MSI Thin 15 hardware merely by archiving this source.
