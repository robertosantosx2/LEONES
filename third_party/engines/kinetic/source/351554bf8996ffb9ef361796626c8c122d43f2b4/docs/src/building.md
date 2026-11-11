# Building from source

Kinetic is a Cargo workspace of small crates. Building it needs only Rust;
the CUDA kernels also need the CUDA toolkit.

## Requirements

- **Rust 1.91 or newer.** Install it with [rustup](https://rustup.rs).
- **Windows:** the MSVC build tools (Visual Studio 2022 or its Build Tools,
  with "Desktop development with C++").
- **Linux:** a C toolchain (`build-essential` on Debian and Ubuntu).
- **For NVIDIA GPUs:** the [CUDA toolkit](https://developer.nvidia.com/cuda-downloads)
  12.8 or newer, for `nvcc`. It is needed only at build time: the binary opens
  the driver at runtime and links no CUDA library.

## Build

```sh
git clone https://github.com/Veloresearch/kinetic
cd kinetic
cargo build --release -p kinetic-cli
target/release/kinetic --version
```

The `cuda` feature is on by default. The build looks for `nvcc` in `$NVCC`,
then in `$CUDA_PATH/bin`, then on `PATH`. Without it the build still
succeeds and prints `warning: nvcc not found: CUDA kernels not built`; that
binary runs on the CPU and says so when you ask for `--device cuda`. To build
without CUDA at all:

```sh
cargo build --release -p kinetic-cli --no-default-features
```

On Windows, `nvcc` needs `cl.exe`. From a plain shell, the build finds the
newest MSVC toolset through `vswhere` and passes it to `nvcc`, so a developer
prompt is not required.

The kernels are compiled for every NVIDIA architecture from Turing (sm_75) to
Blackwell (sm_120), plus PTX that newer drivers can compile for later GPUs.

Install the binary into `~/.cargo/bin`:

```sh
cargo install --path crates/kinetic-cli
```

## The libraries

```sh
cargo build --release -p kinetic-capi        # kinetic_capi.dll / libkinetic_capi.so
```

The Python package lives outside the workspace, so that building the engine
never needs Python, and builds with [maturin](https://www.maturin.rs):

```sh
cd bindings/python
pip install "maturin>=1.5,<2"
maturin build --release
pip install target/wheels/kinetic_engine-*.whl
```

## Docker

```sh
docker build -f docker/Dockerfile -t kinetic .              # CPU
docker build -f docker/Dockerfile.cuda -t kinetic:cuda .    # NVIDIA GPUs
```

Both images run `kinetic serve` on port 8080 as an unprivileged user; see
[Install](install.md#docker).

## Tests

```sh
cargo test --release --workspace
```

Tests that need a real model are marked `#[ignore]`. Point them at a file
with `KINETIC_TEST_GGUF` and include them:

```sh
KINETIC_TEST_GGUF=SmolLM2-135M-Instruct-f16.gguf \
  cargo test --release -p kinetic-models --test architectures -- --ignored
```

The CUDA kernel tests run when a GPU and the kernels are present and print
`skipped: ...` otherwise; the model tests on the GPU take `--features cuda`
on `kinetic-models`. Test in release mode: real models in a debug build are
very slow.

## Checks before a pull request

```sh
cargo fmt --all -- --check
cargo clippy --release --workspace --all-targets --all-features -- -D warnings
cargo test --release --workspace
```

CI runs the same on Windows and Linux, builds the C example with `gcc` and
`cl`, and builds and tests the Python package.

## The documentation

This book is built with [mdBook](https://rust-lang.github.io/mdBook/):

```sh
cargo install mdbook --locked
python scripts/llama_flags_doc.py    # refresh the llama.cpp flag table
mdbook serve docs
```
