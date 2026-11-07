#!/usr/bin/env bash
# Reproduction commands for Pithos 0.5.1 / LFM3-1.7B on the MSI Thin 15.
# Run from ~/Pithos-0.5.1/pithos-0.5.1-linux-x64
set -euo pipefail
MODEL="models/LFM3-1.7B-Q4_K_M.gguf"

echo "=== NVIDIA RTX 3050 Vulkan ==="
./pithos -m "$MODEL" --gpu vulkan --gpu-device 1 --bench

echo "=== Intel ADL GT2 Vulkan optimized ==="
PITHOS_VK_INTEL=1 ./pithos -m "$MODEL" --gpu vulkan --gpu-device 0 --bench

echo "=== Intel ADL GT2 Vulkan standard ==="
PITHOS_VK_INTEL=0 ./pithos -m "$MODEL" --gpu vulkan --gpu-device 0 --bench

echo "=== Intel Core i7-12650H CPU ==="
./pithos -m "$MODEL" --cpu --bench

echo "=== NVIDIA prompt sweep (validated range in this campaign) ==="
./pithos -m "$MODEL" --gpu vulkan --gpu-device 1 --bench 2048,256
./pithos -m "$MODEL" --gpu vulkan --gpu-device 1 --bench 4096,256
./pithos -m "$MODEL" --gpu vulkan --gpu-device 1 --bench 8192,256

# Do not run PP > 8192 until the effective context handling has been verified.
