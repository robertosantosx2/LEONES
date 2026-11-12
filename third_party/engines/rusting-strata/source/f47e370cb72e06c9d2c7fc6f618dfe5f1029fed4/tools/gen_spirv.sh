#!/bin/sh
# Compile every Vulkan kernel (src/vulkan/shaders/*.comp) to SPIR-V. Usage: tools/gen_spirv.sh [absolute out dir]
# (default src/vulkan/spv, which is committed; tests/backend.rs checks that it is up to date).
set -e
cd "$(dirname "$0")/../src/vulkan/shaders"
out=${1:-../spv}
mkdir -p "$out"
for f in *.comp; do glslc --target-env=vulkan1.3 -O -o "$out/${f%.comp}.spv" "$f"; done
