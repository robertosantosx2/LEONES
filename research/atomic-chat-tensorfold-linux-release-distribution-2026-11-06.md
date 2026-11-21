# TensorFold Native 1.2.3: Linux release artifact and distribution decision

Date: 2026-11-06  
Scope: public release metadata and packaging documentation; no archive was downloaded or executed in this step.

## Verified v1.2.3 release assets

Release: https://github.com/ashhart/TensorFold/releases/tag/v1.2.3  
Published: 2026-11-05  
Tag: `v1.2.3`

The release publishes a Linux x86_64 archive and companion checksum/signature assets:

| Asset | Published size | Published SHA-256 |
|---|---:|---|
| `tensorfold-1.2.3-linux-x86_64.tar.gz` | 47,986,595 bytes | `a60f7a6e0a975a6d747248cfe9d819dc6c51170cc12038cf1b6ae961e89c8c44` |
| `tensorfold-1.2.3-linux-x86_64.tar.gz.sha256` | 103 bytes | `3005061ed167fae32785a9807e2c30c486d33456b1443b7d8b22749732cf4c56` |
| `tensorfold-1.2.3-linux-x86_64.tar.gz.sha256.sig` | 64 bytes | `9dac0ba05bf56d7b49a53e8a6f073c624b0bbc26354b362f627f641f62a3dad2` |

The release also publishes Linux aarch64 equivalents. The x86_64 archive URL is:
https://github.com/ashhart/TensorFold/releases/download/v1.2.3/tensorfold-1.2.3-linux-x86_64.tar.gz

The GitHub release API marks the release as not immutable. Pinning the version and asset digest is therefore required; do not consume a moving `latest` URL.

## Archive contract

The upstream `packaging/README.md` says each archive has one named top-level directory containing:
- `bin/tensorfold-native`
- `lib/`
- `LICENSE`, `NOTICE`, `VERSION`, `RUNTIME.md`
- `LICENSES/`, `THIRD_PARTY_NOTICES.md`, and `SHA256SUMS`

The archive does not include model weights, Python packages, source, tests or build caches. The release packaging has no Python runtime dependency.

Linux release builds use CUDA and baseline CPU features, with glibc 2.28 as the stated minimum. The documented qualified CUDA fatbin targets include SM86, which corresponds to the Ampere compute capability used by the reference RTX 3050 Laptop GPU. This is packaging/architecture evidence only; it is not proof that a specific model fits or runs on that GPU.

## Integrity and trust caveat

Upstream publishes a SHA-256 file and a detached 64-byte signature file beside the Linux archive. The public `SECURITY.md` and `packaging/README.md` explain companion SHA-256 files, but the inspected v1.2.3 public packaging/security docs do not identify a trusted public key or a verification command for the Linux archive signature.

Therefore:
- A managed installer can pin the immutable version string and expected archive SHA-256, download the archive and checksum, verify the archive digest, safely extract it, and run `--version` plus `capabilities --json`.
- Do not claim independent signature authenticity until Atomic Chat has a trusted, independently pinned upstream signing key and a documented verification procedure.
- Do not treat a checksum downloaded from the same release endpoint as an independent authenticity root.

## Distribution recommendation

**Production direction:** managed, versioned TensorFold binary distribution owned by Atomic Core, not implicit PATH lookup. It gives the app a deterministic executable path, controlled upgrades, a clear version/build lifecycle, checksum enforcement and a place to keep the backend binary separate from model data.

**First implementation stage:** permit an explicitly configured external executable path for the Linux PoC only. Do not resolve `tensorfold-native` from PATH implicitly. The external path must be visible in diagnostics and validated with `--version` and `capabilities --json`.

A production managed installer should:
1. Use an explicit version and architecture-specific GitHub release asset URL.
2. Verify the expected archive SHA-256 before extraction.
3. Reject path traversal, symlinks escaping the staging directory, unexpected top-level layouts and missing required files.
4. Extract to a new versioned directory; never overwrite a running build.
5. Verify the bundled `SHA256SUMS` and execute `--version` and `capabilities --json` from the extracted absolute path.
6. Activate the new build only after validation, while retaining old build directories until no session uses them.
7. Keep model weights and caches outside the engine installation directory.

## Source references

- Release metadata and assets: https://api.github.com/repos/ashhart/TensorFold/releases/tags/v1.2.3
- Release page: https://github.com/ashhart/TensorFold/releases/tag/v1.2.3
- Upstream packaging contract: https://github.com/ashhart/TensorFold/blob/v1.2.3/packaging/README.md
- Upstream security policy: https://github.com/ashhart/TensorFold/blob/v1.2.3/SECURITY.md
