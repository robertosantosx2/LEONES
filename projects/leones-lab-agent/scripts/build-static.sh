#!/usr/bin/env sh
set -eu

TARGET="x86_64-unknown-linux-musl"
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v cargo >/dev/null 2>&1; then
    echo "error: cargo no está instalado" >&2
    exit 1
fi
if ! command -v musl-gcc >/dev/null 2>&1; then
    echo "error: falta musl-gcc (Ubuntu: sudo apt-get install musl-tools)" >&2
    exit 1
fi
if ! rustup target list --installed | grep -qx "$TARGET"; then
    echo "error: falta el target Rust $TARGET" >&2
    echo "Instálalo con: rustup target add $TARGET" >&2
    exit 1
fi

cargo fmt --all -- --check
cargo test --locked
CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER=musl-gcc cargo build --release --locked --target "$TARGET"

BIN="target/$TARGET/release/lab-agent"
test -x "$BIN"
if command -v readelf >/dev/null 2>&1 && readelf -l "$BIN" | grep -q INTERP; then
    echo "error: el ELF contiene un intérprete dinámico" >&2
    exit 1
fi

echo "Binario estático generado: $ROOT/$BIN"
file "$BIN" 2>/dev/null || true
