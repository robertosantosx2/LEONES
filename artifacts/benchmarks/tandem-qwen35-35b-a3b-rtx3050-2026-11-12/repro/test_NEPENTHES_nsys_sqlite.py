#!/usr/bin/env python3
"""Synthetic SQLite tests for the NEPENTHES Nsight Systems inspector."""
import pathlib
import sqlite3
import tempfile
import unittest

from inspect_NEPENTHES_nsys_sqlite import analyze_database


class NsightSqliteInspectorTests(unittest.TestCase):
    def make_db(self, root):
        path = pathlib.Path(root) / "synthetic.sqlite"
        db = sqlite3.connect(path)
        db.executescript("""
            CREATE TABLE StringIds(id INTEGER PRIMARY KEY, value TEXT);
            CREATE TABLE PROCESSES(globalPid INTEGER, pid INTEGER, name TEXT);
            CREATE TABLE ThreadNames(nameId INTEGER, priority INTEGER, globalTid INTEGER);
            CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(
                globalTid INTEGER, nameId INTEGER, start INTEGER, end INTEGER
            );
            CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(
                start INTEGER, end INTEGER, deviceId INTEGER, contextId INTEGER,
                streamId INTEGER, shortName INTEGER
            );
            CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(
                start INTEGER, end INTEGER, copyKind INTEGER, srcKind INTEGER,
                dstKind INTEGER, bytes INTEGER
            );
        """)
        db.executemany("INSERT INTO StringIds VALUES (?, ?)", [
            (1, "llama-server"), (2, "cudaStreamSynchronize_v3020"),
            (3, "moe_weighted_reduction_f32"), (4, "k_host_add_wait"),
            (5, "k_host_add"),
        ])
        global_pid = 281913466028032
        global_tid = 281913466054168
        db.execute("INSERT INTO PROCESSES VALUES (?, ?, ?)",
                   (global_pid, 26136, "/tmp/llama-server"))
        db.execute("INSERT INTO ThreadNames VALUES (?, ?, ?)",
                   (1, 20, global_tid))
        db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES (?, ?, ?, ?)",
                   (global_tid, 2, 100, 300))
        db.executemany("INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (?, ?, ?, ?, ?, ?)", [
            (1000, 1100, 0, 1, 15, 3),
            (1101, 1200, 0, 1, 15, 4),
            (1201, 1300, 0, 1, 15, 5),
        ])
        db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES (?, ?, ?, ?, ?, ?)",
                   (900, 950, 1, 1, 3, 4096))
        db.commit()
        db.close()
        return path

    def test_separates_runtime_kernel_and_memcpy(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze_database(self.make_db(tmp))
        self.assertEqual(result["runtime"]["total_calls"], 1)
        thread = result["runtime"]["threads"][0]
        self.assertEqual(thread["thread_name"], "llama-server")
        self.assertEqual(thread["process"]["pid"], 26136)
        self.assertEqual(result["kernels"]["total_events"], 3)
        self.assertEqual(result["memcpy"]["total_bytes"], 4096)
        self.assertEqual(result["memcpy"]["by_kind_and_memory"][0]["copy_kind"], "HTOD")
        self.assertEqual(result["memcpy"]["by_kind_and_memory"][0]["src_memory"], "PAGEABLE")
        self.assertEqual(result["memcpy"]["by_kind_and_memory"][0]["dst_memory"], "DEVICE")

    def test_detects_wait_neighbors_without_claiming_cpu_causality(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze_database(self.make_db(tmp))
        waits = result["moe_wait_sequence"]
        self.assertEqual(waits["wait_count"], 1)
        self.assertEqual(waits["neighbor_patterns"][0]["previous"], "moe_weighted_reduction_f32")
        self.assertEqual(waits["neighbor_patterns"][0]["next"], "k_host_add")
        self.assertIn("does not identify the CPU worker", waits["note"])

    def test_opens_database_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.make_db(tmp)
            result = analyze_database(path)
            self.assertTrue(result["runtime"]["available"])
            with self.assertRaises(sqlite3.OperationalError):
                with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
                    db.execute("CREATE TABLE should_fail(x)")

if __name__ == "__main__":
    unittest.main()
