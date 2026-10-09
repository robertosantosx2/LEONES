# cafe-llama.cpp release artifact matrix for ODS

Reviewed GitHub Releases API for tag `0.75` on 2026-10-09:
https://github.com/quimmedes/cafe-llama.cpp/releases/tag/0.75

The fork candidate commit `a2068a4a12a3cf8cdf27ca047cc28bbceb16df30` points to
`llama-bin-ubuntu-x64-cuda-12.4.zip`. That exact asset name is **not** in the
0.75 release manifest. The actual Linux x64 CUDA 12.4 asset is:

- Asset: `llama-0.75-bin-linux-cuda-12.4-x64.tar.gz`
- URL: https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-0.75-bin-linux-cuda-12.4-x64.tar.gz
- Published release digest: `sha256:536ec49ec1de5277578be976a5c161bb985857d5f8066e74889afff6c3f5920c`
- Size: 342,307,440 bytes

Other release assets and published SHA-256 digests observed:
| Platform/backend | Asset | SHA-256 |
|---|---|---|
| Linux x64 CUDA 12.8 | `llama-0.75-bin-linux-cuda-12.8-x64.tar.gz` | `7d5fa65c9d58d46218c2d01720b6af067a2e4b1d2b01a526046201d64a2e1fb1` |
| Linux x64 CUDA 13.3 | `llama-0.75-bin-linux-cuda-13.3-x64.tar.gz` | `155d2ac5cf2859d28b60f59d31b2f91ed165c09b0617f655cfad6811092590e0` |
| Linux ARM64 CUDA 13.3 | `llama-0.75-bin-linux-cuda-13.3-arm64.tar.gz` | `053601076e953799bfa3b4023e002bfc732f7f8e97e6d1ceb693cfa8044a3896` |
| Ubuntu x64 Vulkan | `llama-0.75-bin-ubuntu-vulkan-x64.tar.gz` | `059aff1e26d616d2ff25ac76697d72c80d3d429af827e15cf2849b8e70095d5e` |
| Ubuntu ARM64 CPU | `llama-0.75-bin-ubuntu-arm64.tar.gz` | `71dc9fa1c920d1787a74e65af4d4371ac45f14f4203b119af8299909bbd75a91` |
| Ubuntu x64 CPU | `llama-0.75-bin-ubuntu-x64.tar.gz` | `315e4319af501d311f2c7fecf706f916cba72c920ac7df91e50b88517f7156a7` |

## Required implementation

1. Choose the artifact from an explicit architecture/backend mapping; do not use
   one CUDA x64 default for every ODS installation.
2. Pin the tag, exact filename and digest in reviewed source.
3. Download with failure-on-HTTP-error, verify SHA-256 before extraction, and
   fail the build if the digest differs or the expected executable is missing.
4. Extract the known archive format with the required tools installed; avoid
   format guessing through an uninstalled `file` command.
5. Record artifact URL, release tag, SHA-256 and runtime build ID in the
   runtime profile/proof, and reject activation when they are missing.
6. Keep cafe opt-in. A valid archive does not prove the runtime is compatible
   with a model or capable of serving a completion; the ODS activation
   transaction must still verify `/health`, `/v1/models`, context, and a real
   completion before publishing its route.

This is release-metadata evidence, not a local binary execution test and not
a claim that ODS integration is complete.
