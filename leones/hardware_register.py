"""Register the local hardware profile in Leones Atlas.

This script has one responsibility: detect basic hardware and store that
profile in the SQLite Atlas. It does not inspect models or run inference.

Example:
    python -m leones.hardware_register --atlas leones_atlas.sqlite
"""

import argparse
import sqlite3
from pathlib import Path

from .hardware import HardwareProfiler


SCHEMA = """
CREATE TABLE IF NOT EXISTS hardware_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpu TEXT NOT NULL,
    architecture TEXT,
    ram_gb REAL NOT NULL,
    cpu_count INTEGER NOT NULL,
    os TEXT,
    capabilities TEXT NOT NULL DEFAULT ''
);
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Register local hardware in Leones Atlas.")
    parser.add_argument("--atlas", default="leones_atlas.sqlite", help="SQLite Atlas path")
    args = parser.parse_args()

    snapshot = HardwareProfiler().profile()
    profile = snapshot.profile

    with sqlite3.connect(Path(args.atlas)) as db:
        db.executescript(SCHEMA)
        db.execute(
            "INSERT INTO hardware_profiles(cpu, architecture, ram_gb, cpu_count, os, capabilities) VALUES (?, ?, ?, ?, ?, ?)",
            (
                profile.cpu,
                profile.architecture,
                profile.ram_gb,
                snapshot.cpu_count,
                profile.os,
                ",".join(profile.capabilities),
            ),
        )

    print(f"registered hardware profile in {args.atlas}")


if __name__ == "__main__":
    main()
