import sqlite3


def test_hardware_registration_schema(tmp_path):
    path = tmp_path / "atlas.sqlite"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE hardware_profiles (profile_id INTEGER PRIMARY KEY, cpu TEXT, architecture TEXT, ram_gb REAL, cpu_count INTEGER, os TEXT, capabilities TEXT)"
        )
        db.execute(
            "INSERT INTO hardware_profiles(cpu, architecture, ram_gb, cpu_count, os, capabilities) VALUES (?, ?, ?, ?, ?, ?)",
            ("test-cpu", "x86_64", 16, 8, "linux", "x86_64"),
        )
        row = db.execute("SELECT cpu, ram_gb FROM hardware_profiles").fetchone()
    assert row == ("test-cpu", 16)
