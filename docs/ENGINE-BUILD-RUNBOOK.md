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
TANDEM_SRC="$(python3 -c 'import json; print("third_party/engines/tandem-cpp/" + json.load(open("third_party/engines/tandem-cpp/SOURCE.json"))["source_tree"])')"
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

Use `rustc --version` and `cargo --version` for Rust engines; `zig version` and `nvcc --version` for TensorFold; and `cmake --version`, `c++ --version`, `nvcc --version` for llama.cpp/Tandem. For Tandem.cpp, also pass both its patch and the exact base snapshot metadata:

```bash
TANDEM_SRC="$(python3 -c 'import json; print("third_party/engines/tandem-cpp/" + json.load(open("third_party/engines/tandem-cpp/SOURCE.json"))["source_tree"])')"
python3 scripts/capture_engine_build.py --engine tandem-cpp \
  --binary "$HOME/build/tandem-msi/build/bin/llama-server" \
  --build-command "bash $TANDEM_SRC/build.sh $HOME/build/tandem-msi -DCMAKE_CUDA_ARCHITECTURES=86" \
  --build-log artifacts/engine-builds/tandem-cpp/build.log \
  --compiler 'cmake --version' --compiler 'c++ --version' --compiler 'nvcc --version' \
  --backend cuda --feature GGML_CUDA --feature sm_86 \
  --patch "$TANDEM_SRC/tandem.patch" \
  --base-source-meta third_party/engines/llama-cpp-tandem-base/SOURCE.json \
  --output artifacts/engine-builds/tandem-cpp/build.json
```

The runner checks that the build evidence belongs to the configured engine, the Tandem base commit matches its pinned `SOURCE.json`, a patch hash is present when required, and the launched executable SHA-256 equals the captured binary SHA-256.

## Benchmark comparability and MSI handoff

- `llama-cpp` (current upstream), `llama-cpp-tandem-base` (exact base), and `tandem-cpp` are distinct build identities.
- Tandem.cpp and TensorFold are scoped to the CUDA profile in the example because their example builds are CUDA-specific. The runner records skipped profiles rather than trying to launch unsupported CPU variants.
- Kinetic, llama.cpp and RustingStrata use GGUF in this comparison; TensorFold uses its own qualified checkpoint directory. Do not publish a cross-engine ranking unless the checkpoint/tokenizer/template are genuinely equivalent and the artifact differences are explicitly disclosed.
- All commands bind to loopback. The runner loads one engine/profile at a time, captures host/GPU state, stops the process and requires recovery before proceeding.
- Do not run the full matrix until model paths, binary hashes, build JSON files and adapter health/API behavior have been checked.

**The only remaining work that cannot be completed by GitHub CI is the physical build/runtime smoke test and measurement on the MSI**, because it requires the local RTX 3050, its driver, its installed CUDA/NVRTC libraries, available RAM/VRAM and local model artifacts. Until that point the framework, source snapshots and build recipes are prepared but no performance value is MEASURED.


## Project Maya (model-specific engine family; preparation only)

Upstream: https://github.com/mw00/project-maya  
Vendored identity: `third_party/engines/project-maya/SOURCE.json`  
Pinned commit: `a3582528bfb73175fed1757b485bfcaaf01aaeaa` (v1.1.58 release line).

Project Maya is a model-specific C++ inference suite, not one generic binary/model pair. It includes dedicated engines for GLM-5.3, GLM-5.3-Flash, DeepSeek-V4.1-Flash and MiniMax-M3.1-Flash, a browser dashboard/monitor, an OpenAI-compatible `/v1/chat/completions` API and an Anthropic-compatible `/v1/messages` API. It supports NVIDIA and AMD paths; its README documents Linux x86-64, CUDA 12.x (CUDA 13 works for RTX 20 and newer), g++, Python 3.10+ and fast NVMe. The repository is MIT, but that does **not** replace each model's own license.

### Model packs recorded in LEONES

See `configs/models.registry.json` for the machine-readable catalogue. Upstream's smaller packs and approximate sizes:

| Model | Maya setup id | Download | Whole model memory | Recommended VRAM + RAM |
| --- | --- | ---: | ---: | ---: |
| GLM-5.3 (744B) | `glm-5.3-maya-xs` | 170 GB | 176 GB | 192 GB |
| GLM-5.3-Flash (321B) | `glm-maya-xs` | 73.4 GB | 80 GB | 88 GB |
| DeepSeek-V4.1-Flash (748B) | `deepseek-maya-xs` | 277 GB | 121 GB | 128 GB |
| MiniMax-M3.1-Flash (428B) | `minimax-maya-xs` | 93 GB | 100 GB | 128 GB |

These are upstream-published sizes and memory guidance, not LEONES downloads or measured performance. DeepSeek's download includes Engram tables that remain on NVMe and are not counted in resident memory. GLM-5.3 and MiniMax model licenses differ from the project source license; check the exact model card/terms before redistributing weights.

### Setup and build (for a suitable host; not the MSI)

Clone/setup is upstream-managed and selects one model pack per setup:

```bash
git clone https://github.com/mw00/project-maya.git
cd project-maya
./setup.sh
```

The interactive setup checks hardware, offers model packs, downloads verified model files, builds the corresponding model-specific engine and starts the service. To choose a model non-interactively, use the setup IDs above, for example:

```bash
./maya.sh --setup --model glm-maya-xs
```

The normal service listens on `http://127.0.0.1:8080` by default. The dashboard and APIs are documented by upstream. Run `./maya.sh --check` first on a target machine and retain the complete setup/build log, exact source SHA, model pack manifest/checksums, each generated engine binary hash and configuration. The generic LEONES build-capture currently records one primary binary; a proper Maya benchmark adapter must capture all selected model-engine binaries and switch model packs explicitly before it is enabled.

### MSI compatibility gate — do not run setup there

The current MSI Thin 15 has 14 GiB system RAM and 4 GiB VRAM. Project Maya documents **32 GiB system RAM as its minimum floor**, plus a fast NVMe SSD; recommended VRAM+RAM pools for the smallest listed packs start at 88 GiB. The MSI is below even the published minimum system-RAM floor. Do not download these 73–277 GB packs or attempt a runtime benchmark on this machine. The source snapshot and catalogue can be preserved in LEONES without claiming local feasibility.

The `project-maya` benchmark config is deliberately disabled. Enabling it requires a suitable host, a chosen and verified model pack, model-specific binary/build provenance, and a dedicated adapter that can prepare/reload Maya's selected engine and exercise both API protocols as appropriate.


## One-shot sequential build batch for the MSI

The repository includes `scripts/build_engines_msi.sh`. Run it from any directory after updating the LEONES checkout to this branch:

```bash
cd ~/LEONES
git fetch origin
git switch research/kinetic-audit-benchmark 2>/dev/null || \
  git switch --track -c research/kinetic-audit-benchmark origin/research/kinetic-audit-benchmark
git pull --ff-only
chmod +x scripts/build_engines_msi.sh
bash scripts/build_engines_msi.sh
```

The batch is deliberately sequential and limits Cargo/CMake parallelism to two jobs by default. It builds Kinetic, TensorFold, current llama.cpp, the exact llama.cpp Tandem base, Tandem.cpp and RustingStrata. It uses the immutable vendored source trees and separate working/build directories, so compiler output does not dirty the preserved source snapshots. It continues after an individual engine fails, records a per-engine status, and exits non-zero if any build failed. CMake and Cargo build caches remain available for a rerun.

Outputs:
- Logs: `artifacts/engine-builds/<engine>/build.log`
- Build provenance: `artifacts/engine-builds/<engine>/build.json`
- Batch summary: `~/build/leones-engine-builds/build-batch-<UTC timestamp>.tsv`
- Binaries/build trees: `~/build/leones-engine-builds/<engine>/`

The script does not install missing toolchains, download model weights, start servers or run inference. TensorFold is skipped unless the exact Zig version in its `.zig-version` and CUDA NVCC are present. All CUDA CMake builds target `sm_86` and are capped at two jobs to reduce memory pressure. Connect the charger and leave sufficient free disk space before starting. You can interrupt with Ctrl+C; rerunning reuses the CMake/Cargo build directories, although an interrupted individual engine may need its build step repeated.

**Project Maya is intentionally marked SKIPPED.** Its upstream setup flow selects a model pack, downloads large weight bundles and builds model-specific engines; it is not a source-only generic build. Do not run Maya setup on this 14 GiB MSI.

### Expected duration on the MSI

Planning estimate only, not a measured build time: allow **about 2–5 hours** for the six source builds on the i7-12650H, assuming the Rust/Zig/CMake/CUDA toolchains and dependencies are already installed, NVCC works, the machine is on AC power and the build cache is initially cold. Dependency downloads, compiler incompatibilities, low disk space or a retry after a failure can extend this to **5–8 hours or more**. TensorFold and the three CUDA CMake builds are the largest uncertainty. The script is sequential, so the machine will remain occupied until the batch exits; it does not run model inference and does not need the model weights.


To let Ubuntu continue even if the terminal closes, start it under the systemd sleep inhibitor (keep the MSI connected to AC power):

```bash
cd ~/LEONES
mkdir -p "$HOME/build/leones-engine-builds"
nohup systemd-inhibit --what=sleep:idle --why="LEONES sequential engine builds" \
  bash scripts/build_engines_msi.sh \
  > "$HOME/build/leones-engine-builds/launcher.log" 2>&1 < /dev/null &
echo "Build batch PID: $!"
```

Monitor with:

```bash
tail -f "$HOME/build/leones-engine-builds/launcher.log"
```

The inhibitor prevents automatic sleep while the build process is active. Do not power off or disconnect AC. When the process exits, the inhibitor is released. A missing toolchain is reported as `BLOCKED` (and makes the batch exit non-zero); Project Maya alone is an intentional `SKIPPED`.
