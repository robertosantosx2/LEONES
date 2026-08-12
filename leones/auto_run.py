"""Run a task through the first autonomous LEONES path.

One responsibility: connect Atlas candidate discovery, simple routing, model
validation, and local execution. It deliberately does not download models or
change model files.

Example:
    python -m leones.auto_run --atlas leones_atlas.sqlite \
        "Write a Python function that adds two numbers"
"""

import argparse
from pathlib import Path

from .model_prepare import validate
from .router_atlas import candidates_from_atlas
from .router_simple import route
from .run_model import run


def execute(atlas: str | Path, task: str, max_tokens: int = 128) -> str:
    """Route and execute one task using a registered local model."""
    candidates = candidates_from_atlas(atlas)
    decision = route(task, candidates)

    model = Path(decision.model_id)
    validate(model)
    return run(model, task, decision.backend, max_tokens)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one task through LEONES.")
    parser.add_argument("--atlas", required=True)
    parser.add_argument("task")
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()
    print(execute(args.atlas, args.task, args.max_tokens), end="")


if __name__ == "__main__":
    main()
