"""Bootstrap proxy for direct execution of scripts from the repository."""
from pathlib import Path

# When a script is executed as ``python3 scripts/<name>.py``, Python puts
# ``scripts/`` first on sys.path. Expose the real top-level runtime_selection
# package without duplicating its implementation.
__path__ = [str(Path(__file__).resolve().parents[2] / "runtime_selection")]
