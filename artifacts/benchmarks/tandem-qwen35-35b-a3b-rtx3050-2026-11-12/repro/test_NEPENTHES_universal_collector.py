#!/usr/bin/env python3
"""Offline tests for the engine-agnostic NEPENTHES collector."""
import hashlib
import json
import pathlib
import tempfile
import time
import unittest
from unittest import mock

from nepenthes_universal_collector import UniversalCollector, read_proc, read_meminfo


class UniversalCollectorTests(unittest.TestCase):
    def test_creates_unique_run_with_manifest_samples_report_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = UniversalCollector(tmp, "fixture-engine", "fixture-model",
                                           pid=None, interval=0.2)
            run_dir = collector.start()
            time.sleep(0.25)
            saved = collector.finish()
            self.assertEqual(run_dir, saved)
            self.assertTrue((saved / "run_manifest.json").is_file())
            self.assertTrue((saved / "samples/telemetry.jsonl").is_file())
            self.assertTrue((saved / "collection_report.json").is_file())
            self.assertTrue((saved / "SHA256SUMS").is_file())
            rows = [json.loads(line) for line in (saved / "samples/telemetry.jsonl").read_text().splitlines()]
            self.assertGreaterEqual(len(rows), 2)
            self.assertTrue(all(row["run_id"] == collector.run_id for row in rows))
            report = json.loads((saved / "collection_report.json").read_text())
            self.assertGreaterEqual(report["sample_count"], 2)
            self.assertFalse(report["coverage"]["process_samples"])
            for line in (saved / "SHA256SUMS").read_text().splitlines():
                digest, relative = line.split("  ", 1)
                self.assertEqual(hashlib.sha256((saved / relative).read_bytes()).hexdigest(), digest)

    def test_engine_events_are_correlated_and_reject_unknown_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = UniversalCollector(tmp, "engine", "model", interval=0.2)
            root = collector.start()
            event = collector.event("cache_miss", {"layer": 7, "expert": 12},
                                    request_id="req-1", source="engine-adapter")
            self.assertEqual(event["run_id"], collector.run_id)
            self.assertEqual(event["request_id"], "req-1")
            self.assertEqual(event["payload"]["expert"], 12)
            with self.assertRaises(ValueError):
                collector.event("invented", {})
            collector.finish()

    def test_request_record_is_written_with_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = UniversalCollector(tmp, "engine", "model")
            root = collector.start()
            collector.request_record("request-01", {"finish_reason": "stop", "ttft_ms": 12.5})
            record = json.loads((root / "requests/request-01.json").read_text())
            self.assertEqual(record["run_id"], collector.run_id)
            self.assertEqual(record["finish_reason"], "stop")
            collector.finish()

    def test_procfs_and_memory_probes_have_explicit_availability(self):
        self.assertIn("available", read_meminfo())
        self.assertFalse(read_proc(None)["available"])

    def test_gpu_unavailable_is_not_reported_as_zero(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "nepenthes_universal_collector.shutil.which", return_value=None
        ):
            collector = UniversalCollector(tmp, "engine", "model", interval=0.2)
            root = collector.start()
            time.sleep(0.05)
            collector.finish()
            row = json.loads((root / "samples/telemetry.jsonl").read_text().splitlines()[0])
            self.assertFalse(row["gpu"]["available"])
            self.assertNotIn("gpu_util_pct", row["gpu"])


if __name__ == "__main__":
    unittest.main()
