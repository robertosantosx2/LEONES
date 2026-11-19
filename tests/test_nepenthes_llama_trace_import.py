from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nepenthes_llama_trace_import import import_trace  # noqa: E402


def event(event_id: str, kind: str, request_id: int = 0, duration_ns: int = 0,
          monotonic_ns: int = 100) -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "test-run",
        "event_id": event_id,
        "source": "llama.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_000_000,
        "monotonic_ns": monotonic_ns,
        "request_id": request_id,
        "event_kind": kind,
        "label": "test.label",
        "value0": 0,
        "value1": 0,
        "duration_ns": duration_ns,
        "flags": 0,
    }


def summary(events_drained: int, dropped: int = 0, write_errors: int = 0) -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "test-run",
        "event_id": f"llama-{events_drained + 1}",
        "source": "llama.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_000_100,
        "event_kind": "sink_summary",
        "events_drained": events_drained,
        "dropped_events": dropped,
        "write_errors": write_errors,
    }


class LlamaTraceImportTests(unittest.TestCase):
    def write_trace(self, directory: str, records: list[dict]) -> Path:
        path = Path(directory) / "trace.jsonl"
        path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
        return path

    def test_valid_trace_and_request_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("llama-1", "request_start", request_id=42, monotonic_ns=300),
                event("llama-2", "graph_compute", duration_ns=200, monotonic_ns=100),
                event("llama-3", "request_end", request_id=42, monotonic_ns=200),
                summary(3),
            ])
            result = import_trace(path)
        self.assertTrue(result["capture_complete"])
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["run_id"], "test-run")
        self.assertEqual(result["event_kind_counts"]["graph_compute"], 1)
        self.assertEqual(result["duration_by_event_kind"]["graph_compute"]["mean_ns"], 200)
        self.assertEqual(result["request_lifecycle"]["request_start_events"], 1)
        self.assertEqual(result["request_lifecycle"]["request_end_events"], 1)
        self.assertEqual(result["monotonic_range_ns"], {"min": 100, "max": 300})

    def test_queue_loss_marks_capture_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [event("llama-1", "sync"), summary(1, dropped=2)])
            result = import_trace(path)
        self.assertFalse(result["capture_complete"])
        self.assertEqual(result["sink_summary"]["dropped_events"], 2)

    def test_missing_summary_requires_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [event("llama-1", "sync")])
            with self.assertRaisesRegex(ValueError, "missing final sink_summary"):
                import_trace(path)
            result = import_trace(path, allow_incomplete=True)
        self.assertFalse(result["capture_complete"])
        self.assertTrue(result["quality"]["summary_missing"])

    def test_mixed_run_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            second = event("llama-2", "sync")
            second["run_id"] = "other-run"
            path = self.write_trace(directory, [event("llama-1", "sync"), second, summary(2)])
            with self.assertRaisesRegex(ValueError, "mixed run_id"):
                import_trace(path)

    def test_duplicate_event_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("llama-1", "sync"), event("llama-1", "kv_cache"), summary(2)
            ])
            with self.assertRaisesRegex(ValueError, "duplicate event_id"):
                import_trace(path)

    def test_boolean_is_not_accepted_as_integer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = event("llama-1", "sync")
            bad["value0"] = True
            path = self.write_trace(directory, [bad, summary(1)])
            with self.assertRaisesRegex(ValueError, "value0 must be"):
                import_trace(path)

    def test_event_after_summary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("llama-1", "sync"), summary(1), event("llama-2", "sync")
            ])
            with self.assertRaisesRegex(ValueError, "sink_summary must be the final"):
                import_trace(path)

    def test_drained_count_mismatch_marks_capture_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [event("llama-1", "sync"), summary(2)])
            result = import_trace(path)
        self.assertFalse(result["capture_complete"])
        self.assertTrue(result["quality"]["drained_count_mismatch"])


if __name__ == "__main__":
    unittest.main()
