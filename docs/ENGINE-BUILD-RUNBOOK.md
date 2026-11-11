# Engine build and runtime runbook (Ubuntu / MSI)

This document pins build recipes to the source snapshots recorded by `third_party/engines/*/SOURCE.json`.
It is a preparation guide, not a claim that these builds or model runs have already been executed on the MSI.
Build logs and the resulting executable must be captured with `scripts/capture_engine_build.py` before the runner will measure an engine.

## Common host assumptions

The target host is the MSI Thin 15 B12UC running Ubuntu, Intel i7-12650H, RTX 3050 Laptop (sm_86, 4 GiB VRAM), 14 GiB RAM and a CUDA 13.4 toolkit. The runtime driver and available NVRTC/CUDA libraries must be checked on the day of the run. Do not infer build success from the presence of a prebuilt binary.

Keep model weights outside `third_party/engines`. The runner accepts a model file for GGUF engines and a model directory for checkpoint-based engines; it hashes the complete file or a sorted manifest of every file in a directory.

## Pinned sources and build recipes

### Kinetic

Snapshot: `third_party/engines/kinetic/SOURCE.json`.

The upstream README specifies Rust 1.91 or newer. The CLI crate is `crates/kinetic-cli`; its default features include CUDA and Vulkan. From the vendored snapshot root:

```bash
rustc --version
cargo --version
cargo install --locked --path crates/kinetic-cli --root "$HOME/.local"
```

Expected executable: `$HOME/.local/bin/kinetic`.

Example server command (use a GGUF model):

```bash
kinetic serve /path/to/model.gguf --host 127.0.0.1 --port 8080 \
  --device cuda -ngl 8 -t 4 -c 512 --parallel 1 --off warm-start
```

Kinetic documents `--device cuda|vulkan|cpu`, llama.cpp-compatible `-ngl`/context flags and `--off warm-start`. Record the actual selected device from its startup log.

### TensorFold

Snapshot: `third_party/engines/tensorfold/SOURCE.json`. This snapshot requires the exact Zig version in its `.zig-version`: **0.17.0**. The native CUDA product build supports `sm_86` and requires exactly one of `-Dnvcc` or `-Dfatbins`.

From the vendored snapshot root:

```bash
zig version
/usr/local/cuda-13.4/bin/nvcc --version
zig build -Dgpu=sm_86 -Dnvcc=/usr/local/cuda-13.4/bin/nvcc
```

Expected executable: `zig-out/native/bin/tensorfold-native`.

Example server command (the checkpoint path is positional and should be a complete local checkpoint/Hugging Face cache directory):

```bash
zig-out/native/bin/tensorfold-native serve /path/to/qualified-checkpoint \
  --host 127.0.0.1 --port 8080 --context 512 --parallel 1 \
  --temperature 0 --no-thinking
```

The example benchmark configuration therefore uses an engine-specific directory path for TensorFold. Do not pass a GGUF file unless that particular TensorFold model family explicitly supports it. Preserve the exact checkpoint revision and hash.

### llama.cpp (current upstream)

Snapshot: `third_party/engines/llama-cpp/SOURCE.json`. From its snapshot root:

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build build --config Release -j 4 --target llama-server
```

Expected executable: `build/bin/llama-server`.

This is the current upstream reference. It is not the exact unpatched base used by Tandem.cpp.

### llama.cpp (Tandem.cpp base)

Snapshot: `third_party/engines/llama-cpp-tandem-base/SOURCE.json`, pinned to
`f5222f25c18da062ab2b8a2dbbfbf4feae398566`. This is the exact commit declared in Tandem.cpp's `BASE_COMMIT`.

Use the same CUDA CMake recipe as current llama.cpp, from this snapshot root:

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build build --config Release -j 4 --target llama-server
```

Expected executable: `build/bin/llama-server`. This is the correct unpatched baseline for Tandem.cpp comparisons.

### Tandem.cpp

Snapshot: `third_party/engines/tandem-cpp/SOURCE.json`. Tandem.cpp is a patch set, not a complete llama.cpp fork. Its vendored `BASE_COMMIT` is the same pinned base above; its `LICENSE` states MIT and identifies the portions derived from llama.cpp as MIT as well.

The upstream `build.sh` checks out that base commit, applies `tandem.patch`, then builds CUDA `llama-server`. From the LEONES repository root:

```bash
TANDEM_SRC=third_party/engines/tandem-cpp/source/e1acb8877bfcf92b4ae7c9f0e0f1d896dbf6c683
bash "$TANDEM_SRC/build.sh" "$HOME/build/tandem-msi" \
  -DCMAKE_CUDA_ARCHITECTURES=86
```

Expected executable: `$HOME/build/tandem-msi/build/bin/llama-server`.

For a low-RAM host, the Tandem README recommends `--cache-ram 0`; leave `-lm none` out when the model exceeds physical RAM. Its documented MoE launch includes `-ngl 99 -cmoe --moe-cache-mib auto -np 1 -c <context>`. The sample configuration also sets `--cache-ram 0`. Tandem's upstream performance table is not LEONES evidence.

### RustingStrata

Snapshot: `third_party/engines/rusting-strata/SOURCE.json`. The project is pure Rust and documents `cargo build --release`; CUDA kernels are compiled at runtime through NVRTC. From the vendored snapshot root:

```bash
rustc --version
cargo --version
cargo build --release --locked
```

Expected executable: `target/release/rustingstrata`.

Example CUDA server command:

```bash
target/release/rustingstrata serve --model /path/to/model.gguf --gpu \
  --backend cuda --ctx 512 --addr 127.0.0.1:8080 --threads 4 --parallel 1
```

RustingStrata's documented default `--gpu` selects CUDA when available and otherwise Vulkan; the explicit `--backend cuda` in this example prevents silent backend substitution. It supports Qwen-family GGUF models, not arbitrary GGUF architectures.

## Build evidence capture

After each successful build, retain the full build log under `artifacts/engine-builds/<id>/`, then capture the exact binary:

```bash
python3 scripts/capture_engine_build.py \
  --engine <registry-id> \
  --binary /absolute/path/to/executable \
  --build-command 'exact command used' \
  --build-log artifacts/engine-builds/<registry-id>/build.log \
  --compiler 'compiler --version' \
  --backend cuda \
  --feature <feature-or-architecture> \
  --output artifacts/engine-builds/<registry-id>/build.json
```

Use `rustc --version` and `cargo --version` for Rust engines; `zig version` and `nvcc --version` for TensorFold; and `cmake --version`, `c++ --version`, `nvcc --version` for llama.cpp/Tandem. The runner checks that the build evidence belongs to the configured engine and that the launched executable SHA-256 equals the captured binary SHA-256.

## Benchmark comparability and MSI handoff

- `llama-cpp` (current upstream), `llama-cpp-tandem-base` (exact base), and `tandem-cpp` are distinct build identities.
- Tandem.cpp and TensorFold are scoped to the CUDA profile in the example because their example builds are CUDA-specific. The runner records skipped profiles rather than trying to launch unsupported CPU variants.
- Kinetic, llama.cpp and RustingStrata use GGUF in this comparison; TensorFold uses its own qualified checkpoint directory. Do not publish a cross-engine ranking unless the checkpoint/tokenizer/template are genuinely equivalent and the artifact differences are explicitly disclosed.
- All commands bind to loopback. The runner loads one engine/profile at a time, captures host/GPU state, stops the process and requires recovery before proceeding.
- Do not run the full matrix until model paths, binary hashes, build JSON files and adapter health/API behavior have been checked.

**The only remaining work that cannot be completed by GitHub CI is the physical build/runtime smoke test and measurement on the MSI**, because it requires the local RTX 3050, its driver, its installed CUDA/NVRTC libraries, available RAM/VRAM and local model artifacts. Until that point the framework, source snapshots and build recipes are prepared but no performance value is MEASURED.
