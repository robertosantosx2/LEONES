"""Small command-line entry point for LEONES.

Design rule: one script, one job. This module only translates CLI arguments
into a request and asks the LEONES engine for a route. It does not download,
install or benchmark anything.
"""

import argparse

from .atlas import AtlasRecord, InMemoryAtlas
from .core.contracts import HardwareProfile, ModelCandidate
from .engine import LeonesEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask LEONES which local model to use.")
    parser.add_argument("request", help="Task to perform")
    parser.add_argument("--ram", type=float, default=16, help="Available RAM in GB")
    args = parser.parse_args()

    atlas = InMemoryAtlas([
        # Development candidate. Real Atlas data will replace this list.
        AtlasRecord(ModelCandidate(
            model_id="qwen3-8b",
            quantization="Q4_K_M",
            formats=("GGUF",),
            capabilities=("coding", "filesystem", "shell"),
        ))
    ])
    hardware = HardwareProfile(cpu="unknown", ram_gb=args.ram)
    decision = LeonesEngine(atlas).decide(args.request, hardware)

    print(f"task: {decision.task_type}")
    print(f"model: {decision.route.model_id}")
    print(f"quantization: {decision.route.quantization}")
    print(f"backend: {decision.route.backend}")
    print(f"device: {decision.route.device}")


if __name__ == "__main__":
    main()
