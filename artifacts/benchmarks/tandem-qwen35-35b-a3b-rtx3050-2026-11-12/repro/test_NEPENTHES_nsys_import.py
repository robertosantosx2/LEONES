#!/usr/bin/env python3
"""Offline tests for importing Nsight SQLite activity into NEPENTHES runs."""
import hashlib
import json
import pathlib
import sqlite3
import tempfile
import unittest

from import_NEPENTHES_nsys_sqlite import import_database


class NsightImportTests(unittest.TestCase):
    def make_database(self, root):
        path = pathlib.Path(root) / "capture.sqlite"
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE StringIds(id INTEGER PRIMARY KEY, value TEXT);
            CREATE TABLE PROCESSES(globalPid INTEGER, pid INTEGER, name TEXT);
            CREATE TABLE ThreadNames(nameId INTEGER, priority INTEGER, globalTid INTEGER);
            CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(
                globalTid INTEGER, nameId INTEGER, start INTEGER, end INTEGER,
                correlationId INTEGER
            );
            CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(
                start INTEGER, end INTEGER, deviceId INTEGER, contextId INTEGER,
                streamId INTEGER, shortName INTEGER, correlationId INTEGER
            );
            CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(
                start INTEGER, end INTEGER, copyKind INTEGER, srcKind INTEGER,
                dstKind INTEGER, bytes INTEGER, correlationId INTEGER
            );
        """)
        db.executemany("INSERT INTO StringIds VALUES (?, ?)", [
            (1, "llama-server"), (2, "cudaStreamSynchronize_v3020"),
            (3, "moe_weighted_reduction_f32"), (4, "k_host_add_wait"),
        ])
        global_pid = 281913466028032
        global_tid = 281913466054168
        db.execute("INSERT INTO PROCESSES VALUES (?, ?, ?)", (global_pid, 26136, "/tmp/llama-server"))
        db.execute("INSERT INTO ThreadNames VALUES (?, ?, ?)", (1, 20, global_tid))
        db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES (?, ?, ?, ?, ?)",
                   (global_tid, 2, 100, 300, 7001))
        db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (1000, 1100, 0, 1, 15, 3, 7002))
        db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (900, 950, 1, 1, 3, 4096, 7003))
        db.commit()
        db.close()
        return path

    def make_run(self, root):
        run = pathlib.Path(root) / "run"
        (run / "events").mkdir(parents=True)
        (run / "profiles").mkdir()
        (run / "requests").mkdir()
        (run / "samples").mkdir()
        (run / "run_manifest.json").write_text(json.dumps({"run_id": "run-test"}))
        (run / "collection_report.json").write_text(json.dumps({"coverage": {}}))
        return run

    def test_imports_runtime_kernel_and_memcpy_with_separate_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            db = self.make_database(root)
            run = self.make_run(root)
            report = import_database(db, run)
            events = [json.loads(line) for line in (run / "events/nsys_activity.jsonl").read_text().splitlines()]
            self.assertEqual(report["run_id"], "run-test")
            self.assertEqual(report["imported_event_count"], 3)
            self.assertEqual(report["events_by_kind"]["sync"], 1)
            self.assertEqual(report["events_by_kind"]["kernel"], 1)
            self.assertEqual(report["events_by_kind"]["transfer"], 1)
            self.assertTrue(all(event["monotonic_ns"] is None for event in events))
            self.assertTrue(all(event["source_clock"] == "nsys_activity_ns" for event in events))
            runtime = next(event for event in events if event["source_table"].endswith("RUNTIME"))
            self.assertEqual(runtime["process"]["pid"], 26136)
            self.assertEqual(runtime["thread_name"], "llama-server")
            self.assertEqual(runtime["correlation_id"], 7001)
            collection = json.loads((run / "collection_report.json").read_text())
            self.assertTrue(collection["coverage"]["nsys_profile_import"])
            self.assertEqual(collection["nsys_imported_event_count"], 3)
            for line in (run / "SHA256SUMS").read_text().splitlines():
                digest, relative = line.split("  ", 1)
                self.assertEqual(hashlib.sha256((run / relative).read_bytes()).hexdigest(), digest)

    def test_source_database_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            db = self.make_database(root)
            run = self.make_run(root)
            import_database(db, run)
            with self.assertRaises(sqlite3.OperationalError):
                with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
                    conn.execute("CREATE TABLE must_not_write(x)")

    def test_missing_tables_are_reported_not_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            db = root / "empty.sqlite"
            sqlite3.connect(db).close()
            run = self.make_run(root)
            report = import_database(db, run)
            self.assertEqual(report["imported_event_count"], 0)
            self.assertEqual(report["tables"], {})
            self.assertFalse(report["events_by_kind"])

    def test_refuses_to_overwrite_existing_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            db = self.make_database(root)
            run = self.make_run(root)
            import_database(db, run)
            with self.assertRaises(FileExistsError):
                import_database(db, run)


if __name__ == "__main__":
    unittest.main()
