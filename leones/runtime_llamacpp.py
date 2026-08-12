"""llama.cpp runtime adapter boundary.

The adapter deliberately uses subprocess rather than importing a Python binding,
keeping the core usable with any llama.cpp installation exposing llama-cli.
"""

import shutil
import subprocess
from collections.abc import Iterator
from typing import Any

from .core.contracts import RouteDecision
from .runtime import RuntimeAdapter


class LlamaCppRuntime(RuntimeAdapter):
    name = "llama.cpp"

    def __init__(self, executable: str = "llama-cli") -> None:
        self.executable = executable
        self.model_path: str | None = None

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def load(self, decision: RouteDecision) -> None:
        # Model resolution is intentionally owned by Atlas/Runtime preparation.
        path = decision.parameters.get("model_path")
        if not path:
            raise ValueError("RouteDecision requires parameters['model_path'] for llama.cpp")
        self.model_path = str(path)

    def generate(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        if not self.model_path:
            raise RuntimeError("No model loaded")
        command = [self.executable, "-m", self.model_path, "-p", prompt, "-n", str(kwargs.get("max_tokens", 256))]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        yield result.stdout

    def unload(self) -> None:
        self.model_path = None
