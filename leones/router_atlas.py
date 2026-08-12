"""Load model candidates from Leones Atlas for the Router.

One responsibility: translate Atlas model records into Router candidates.
It does not choose a model, download anything, or execute inference.
"""

from pathlib import Path

from .model_store import ModelStore
from .router_simple import Candidate


def candidates_from_atlas(atlas_path: str | Path) -> list[Candidate]:
    """Return registered models as Router candidates."""
    store = ModelStore(atlas_path)
    with store.path.open("rb"):
        pass
    import sqlite3
    with sqlite3.connect(store.path) as db:
        rows = db.execute(
            "SELECT model_id, capabilities, source FROM model_catalog ORDER BY model_id"
        ).fetchall()
    return [
        Candidate(
            model_id=row[0],
            capabilities=tuple(filter(None, row[1].split(","))),
            backend="llama.cpp" if (row[2] or "").lower().endswith(".gguf") else "llama.cpp",
        )
        for row in rows
    ]
