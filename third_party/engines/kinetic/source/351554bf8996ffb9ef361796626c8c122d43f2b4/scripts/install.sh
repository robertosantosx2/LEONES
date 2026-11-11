#!/bin/sh
# Installs Kinetic for the current user on Linux x86-64.
#
# Downloads a Kinetic release from GitHub (the full build, which runs on
# NVIDIA GPUs through CUDA, on AMD and Intel GPUs through Vulkan and on the
# CPU; --cpu takes the smaller CPU-only build), checks it against the
# release's SHA256SUMS and installs it into ~/.local/bin, with its C library
# and header in ~/.local/lib and ~/.local/include. Needs no root.
#
#   curl -fsSL https://raw.githubusercontent.com/Veloresearch/kinetic/main/scripts/install.sh | sh
#   curl -fsSL .../install.sh | sh -s -- --version 0.1.0 --cpu
set -eu

repo=Veloresearch/kinetic
prefix="${HOME}/.local"
version=
variant=

usage() {
    echo "usage: install.sh [--version VERSION] [--cpu]"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --version) [ $# -ge 2 ] || { usage >&2; exit 2; }; version="$2"; shift 2 ;;
        --version=*) version="${1#--version=}"; shift ;;
        --cpu) variant=cpu; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

fail() {
    echo "install.sh: $*" >&2
    exit 1
}

[ "$(uname -s)" = Linux ] || fail "this script is for Linux; on Windows use install.ps1"
[ "$(uname -m)" = x86_64 ] || fail "Kinetic is built for x86-64, not $(uname -m)"

if command -v curl >/dev/null 2>&1; then
    fetch() { curl -fsSL "$1" -o "$2"; }
elif command -v wget >/dev/null 2>&1; then
    fetch() { wget -q "$1" -O "$2"; }
else
    fail "needs curl or wget"
fi

if command -v sha256sum >/dev/null 2>&1; then
    sha256() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
    sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
    fail "needs sha256sum or shasum to check the download"
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM

if [ -z "$version" ]; then
    fetch "https://api.github.com/repos/$repo/releases/latest" "$tmp/latest.json"
    version=$(sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' "$tmp/latest.json" | head -n 1)
    [ -n "$version" ] || fail "could not read the latest release"
fi
version="${version#v}"

# the cuda archive is the full build: CUDA, Vulkan and the CPU in one binary
[ -n "$variant" ] || variant=cuda

name="kinetic-${version}-linux-x86_64-${variant}"
base="https://github.com/$repo/releases/download/v${version}"
echo "Downloading Kinetic ${version} (${variant} build)"
fetch "$base/$name.tar.gz" "$tmp/$name.tar.gz"
fetch "$base/SHA256SUMS" "$tmp/SHA256SUMS"

expected=$(awk -v f="$name.tar.gz" '$2 == f || $2 == "*" f { print $1 }' "$tmp/SHA256SUMS")
[ -n "$expected" ] || fail "SHA256SUMS does not list $name.tar.gz"
actual=$(sha256 "$tmp/$name.tar.gz")
[ "$actual" = "$expected" ] || fail "checksum mismatch for $name.tar.gz: expected $expected, got $actual"

tar -xzf "$tmp/$name.tar.gz" -C "$tmp"
mkdir -p "$prefix/bin" "$prefix/lib" "$prefix/include"
install -m 755 "$tmp/$name/kinetic" "$prefix/bin/kinetic"
cp "$tmp/$name/lib/"* "$prefix/lib/"
cp "$tmp/$name/include/"* "$prefix/include/"

"$prefix/bin/kinetic" --version
case ":${PATH}:" in
    *":$prefix/bin:"*) ;;
    *) echo "Add $prefix/bin to your PATH, for example: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.profile" ;;
esac
echo "Installed in $prefix/bin. Try: kinetic doctor"
