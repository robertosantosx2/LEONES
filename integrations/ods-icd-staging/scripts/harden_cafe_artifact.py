"""Harden the candidate cafe-llama extension artifact build in a checked-out ODS fork.

Run from the LEONES repository root after checking out the candidate ODS branch at
ods-src/. This script fails closed if the expected Dockerfile/Compose seams moved.
It does not invent a digest: the caller must provide CAFE_LLAMA_RELEASE_SHA256.
"""
from pathlib import Path

ROOT = Path("ods-src/ods/extensions/library/services/cafe-llama")
DOCKERFILE = ROOT / "Dockerfile"
COMPOSE = ROOT / "compose.yaml"

OLD_INSTALL = "RUN apt-get update \\\n && apt-get install -y --no-install-recommends ca-certificates curl tar \\\n && rm -rf /var/lib/apt/lists/*"
NEW_INSTALL = "RUN apt-get update \\\n && apt-get install -y --no-install-recommends ca-certificates curl tar file coreutils unzip \\\n && rm -rf /var/lib/apt/lists/*"

OLD_BLOCK_START = 'ARG CAFE_LLAMA_RELEASE_URL="https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-bin-ubuntu-x64-cuda-12.4.zip"'
OLD_BLOCK_END = 'COPY entrypoint.sh /usr/local/bin/cafe-llama-entrypoint.sh'
NEW_BLOCK = r'''ARG CAFE_LLAMA_RELEASE_URL="https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-bin-ubuntu-x64-cuda-12.4.zip"
ARG CAFE_LLAMA_RELEASE_SHA256=""

RUN set -eux; \
    : "${CAFE_LLAMA_RELEASE_URL:?CAFE_LLAMA_RELEASE_URL must pin the exact release asset URL}"; \
    : "${CAFE_LLAMA_RELEASE_SHA256:?CAFE_LLAMA_RELEASE_SHA256 must pin the exact asset digest}"; \
    case "${CAFE_LLAMA_RELEASE_SHA256}" in *[!0-9a-fA-F]*|'') echo "Invalid CAFE_LLAMA_RELEASE_SHA256" >&2; exit 1 ;; esac; \
    test "${#CAFE_LLAMA_RELEASE_SHA256}" -eq 64 || { echo "SHA-256 must be 64 hex characters" >&2; exit 1; }; \
    curl -fsSL "${CAFE_LLAMA_RELEASE_URL}" -o /tmp/cafe-asset; \
    printf '%s  %s\\n' "${CAFE_LLAMA_RELEASE_SHA256}" /tmp/cafe-asset | sha256sum -c -; \
    if file /tmp/cafe-asset | grep -qi zip; then unzip -q /tmp/cafe-asset -d /opt/cafe-llama; \
    else tar -xzf /tmp/cafe-asset -C /opt/cafe-llama; fi; \
    rm -f /tmp/cafe-asset; \
    found=$(find /opt/cafe-llama -type f -name llama-server -perm /111 -print -quit || true); \
    if [ -z "$found" ]; then echo "Pinned asset contains no executable llama-server" >&2; exit 1; fi; \
    install -m 0755 "$found" /usr/local/bin/llama-server; \
    /usr/local/bin/llama-server --version

'''
def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if not DOCKERFILE.is_file() or not COMPOSE.is_file():
        raise SystemExit(f"Expected candidate extension files under {ROOT}; checkout the ODS candidate branch first")
    docker = DOCKERFILE.read_text()
    docker = replace_once(docker, OLD_INSTALL, NEW_INSTALL, "Dockerfile dependency list")
    start = docker.find(OLD_BLOCK_START)
    end = docker.find(OLD_BLOCK_END)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit("Dockerfile release download block changed; review and patch manually")
    docker = docker[:start] + NEW_BLOCK + docker[end:]
    compose = COMPOSE.read_text()
    old_arg = "        CAFE_LLAMA_RELEASE_URL: ${CAFE_LLAMA_RELEASE_URL:-}"
    new_arg = "        CAFE_LLAMA_RELEASE_URL: ${CAFE_LLAMA_RELEASE_URL:-https://github.com/quimmedes/cafe-llama.cpp/releases/download/0.75/llama-bin-ubuntu-x64-cuda-12.4.zip}\n        CAFE_LLAMA_RELEASE_SHA256: ${CAFE_LLAMA_RELEASE_SHA256:-}"
    compose = replace_once(compose, old_arg, new_arg, "Compose build args")
    DOCKERFILE.write_text(docker)
    COMPOSE.write_text(compose)
    print("Hardened cafe-llama build: file/unzip/coreutils installed; SHA-256 pin required and verified.")
    print("Build remains intentionally fail-closed until CAFE_LLAMA_RELEASE_SHA256 is set to a verified 64-hex digest.")

if __name__ == "__main__":
    main()
