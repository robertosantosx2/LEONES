"""Register one model description in Leones Atlas.

One job only: read explicit metadata from the command line and store it.
No network access, download, license verification, or inference is performed.

Example:
    python -m leones.model_register --atlas leones_atlas.sqlite \
        --id qwen3-8b --family Qwen3 --format GGUF \
        --quant Q4_K_M --size 5.0 --license Apache-2.0
"""

import argparse

from .model import ModelInfo
from .model_store import ModelStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Register model metadata in Leones Atlas.")
    parser.add_argument("--atlas", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--family")
    parser.add_argument("--revision")
    parser.add_argument("--format")
    parser.add_argument("--quant")
    parser.add_argument("--size", type=float)
    parser.add_argument("--license")
    parser.add_argument("--source")
    parser.add_argument("--capability", action="append", default=[])
    args = parser.parse_args()

    model = ModelInfo(
        model_id=args.id,
        family=args.family,
        revision=args.revision,
        format=args.format,
        quantization=args.quant,
        size_gb=args.size,
        capabilities=tuple(args.capability),
        license=args.license,
        source=args.source,
    )
    ModelStore(args.atlas).add(model)
    print(f"registered: {model.model_id}")


if __name__ == "__main__":
    main()
