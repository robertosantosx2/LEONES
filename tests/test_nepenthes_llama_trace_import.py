from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nepenthes_llama_trace_import import import_trace  # noqa: E402


def event(event_id: str, kind: str, request_id: int = 0, duration_ns: int = 0,
          monotonic_ns: int = 100, timestamp_unix_ns: int = 1_800_000_000_000_000_000,
          correlation_token: int | None = None, attribution_level: str | None = None,
          label: str = "test.label", source: str = "llama.cpp") -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "test-run",
        "event_id": event_id,
        "source": source,
        "timestamp_unix_ns": timestamp_unix_ns,
        "monotonic_ns": monotonic_ns,
        "request_id": request_id,
        "correlation_token": correlation_token,
        "attribution_level": attribution_level,
        "clock_domain": "steady_clock",
        "event_kind": kind,
        "label": label,
        "value0": 0,
        "value1": 0,
        "duration_ns": duration_ns,
        "flags": 0,
    }


def summary(events_drained: int, dropped: int = 0, write_errors: int = 0, source: str = "llama.cpp") -> dict:
    return {
        "schema_version": "1.0",
        "run_id": "test-run",
        "event_id": f"llama-{events_drained + 1}",
        "source": source,
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


    def test_explicit_correlation_and_host_clock_calibration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("llama-1", "clock_calibration", monotonic_ns=100,
                      timestamp_unix_ns=1_000_000, label="clock.calibration.start"),
                event("llama-2", "request_start", request_id=42, monotonic_ns=200,
                      timestamp_unix_ns=1_000_100, correlation_token=77, attribution_level="exact"),
                event("llama-3", "request_end", request_id=42, monotonic_ns=900,
                      timestamp_unix_ns=1_000_800, correlation_token=77, attribution_level="exact"),
                event("llama-4", "clock_calibration", monotonic_ns=1_000,
                      timestamp_unix_ns=1_000_900, label="clock.calibration.end"),
                summary(4),
            ])
            result = import_trace(path)
        self.assertEqual(result["request_lifecycle"]["correlation_token_start_events"], 1)
        self.assertEqual(result["request_lifecycle"]["correlation_token_end_events"], 1)
        self.assertEqual(result["request_lifecycle"]["unmatched_correlation_starts"], 0)
        self.assertEqual(result["attribution_level_counts"]["exact"], 2)
        self.assertEqual(result["host_clock_calibration"]["point_count"], 2)
        self.assertEqual(result["host_clock_calibration"]["offset_start_ns"], 999900)
        self.assertEqual(result["host_clock_calibration"]["offset_end_ns"], 999900)
        self.assertEqual(result["host_clock_calibration"]["drift_ppm"], 0)
        self.assertFalse(result["host_clock_calibration"]["nsight_clock_calibrated"])

    def test_exact_attribution_requires_explicit_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = event("llama-1", "kernel", attribution_level="exact")
            path = self.write_trace(directory, [bad, summary(1)])
            with self.assertRaisesRegex(ValueError, "exact attribution requires correlation_token"):
                import_trace(path)

    def test_invalid_unsigned_correlation_token_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = event("llama-1", "request_start", request_id=42,
                        correlation_token=-1, attribution_level="exact")
            path = self.write_trace(directory, [bad, summary(1)])
            with self.assertRaisesRegex(ValueError, "positive unsigned 64-bit integer"):
                import_trace(path)

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

    def test_prompt_or_token_payload_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = event("llama-1", "sync")
            bad["prompt"] = "must never be captured"
            path = self.write_trace(directory, [bad, summary(1)])
            with self.assertRaisesRegex(ValueError, "forbidden text/token fields"):
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




    def test_registered_tensorfold_source_uses_shared_validator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("tf-1", "request_start", request_id=7, source="tensorfold"),
                event("tf-2", "request_end", request_id=7, source="tensorfold"),
                summary(2, source="tensorfold"),
            ])
            result = import_trace(path, source="tensorfold")
        self.assertEqual(result["source"], "tensorfold")
        self.assertEqual(result["event_count"], 2)
        self.assertTrue(result["capture_complete"])

    def test_unknown_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [event("llama-1", "sync"), summary(1)])
            with self.assertRaisesRegex(ValueError, "unregistered trace source"):
                import_trace(path, source="unknown-engine")

    def test_event_source_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("tf-1", "sync", source="tensorfold"),
                summary(1),
            ])
            with self.assertRaisesRegex(ValueError, "source must be llama.cpp"):
                import_trace(path)

    def test_summary_source_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("llama-1", "sync"),
                summary(1, source="tensorfold"),
            ])
            with self.assertRaisesRegex(ValueError, "source must be llama.cpp"):
                import_trace(path)

    def test_tensorfold_rejects_unsupported_clock_domain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = event("tf-1", "sync", source="tensorfold")
            bad["clock_domain"] = "device_clock"
            path = self.write_trace(directory, [bad, summary(1, source="tensorfold")])
            with self.assertRaisesRegex(ValueError, "unsupported tensorfold clock_domain"):
                import_trace(path, source="tensorfold")

    def test_duplicate_summary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_trace(directory, [
                event("llama-1", "sync"), summary(1), summary(1)
            ])
            with self.assertRaisesRegex(ValueError, "sink_summary must be the final"):
                import_trace(path)

    def test_empty_event_or_run_identifier_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad_event_id = event("", "sync")
            path = self.write_trace(directory, [bad_event_id, summary(1)])
            with self.assertRaisesRegex(ValueError, "invalid event_id"):
                import_trace(path)
            bad_run_id = event("llama-2", "sync")
            bad_run_id["run_id"] = ""
            path = self.write_trace(directory, [bad_run_id, summary(1)])
            with self.assertRaisesRegex(ValueError, "invalid run_id"):
                import_trace(path)

    def test_unsigned_fields_enforce_u64_bounds(self) -> None:
        for field in ("request_id", "value0", "value1", "duration_ns", "timestamp_unix_ns", "monotonic_ns"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                bad = event("llama-1", "sync")
                bad[field] = 0x10000000000000000
                path = self.write_trace(directory, [bad, summary(1)])
                with self.assertRaisesRegex(ValueError, "exceeds"):
                    import_trace(path)

    def test_summary_accounting_enforces_u64_bounds_and_exact_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = summary(1)
            bad["write_errors"] = 0x10000000000000000
            path = self.write_trace(directory, [event("llama-1", "sync"), bad])
            with self.assertRaisesRegex(ValueError, "exceeds"):
                import_trace(path)
            bad = summary(1)
            bad["extra"] = 1
            path = self.write_trace(directory, [event("llama-1", "sync"), bad])
            with self.assertRaisesRegex(ValueError, "unexpected sink summary fields"):
                import_trace(path)




    def test_summary_missing_required_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = summary(1)
            del bad["events_drained"]
            path = self.write_trace(directory, [event("llama-1", "sync"), bad])
            with self.assertRaisesRegex(ValueError, "sink summary missing fields"):
                import_trace(path)

    def test_summary_empty_identifiers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = summary(1)
            bad["event_id"] = ""
            path = self.write_trace(directory, [event("llama-1", "sync"), bad])
            with self.assertRaisesRegex(ValueError, "invalid summary event_id"):
                import_trace(path)
            bad = summary(1)
            bad["run_id"] = ""
            path = self.write_trace(directory, [event("llama-1", "sync"), bad])
            with self.assertRaisesRegex(ValueError, "invalid summary run_id"):
                import_trace(path)

    def test_flags_are_limited_to_unsigned_16_bits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bad = event("llama-1", "sync")
            bad["flags"] = 65536
            path = self.write_trace(directory, [bad, summary(1)])
            with self.assertRaisesRegex(ValueError, "flags exceeds 65535"):
                import_trace(path)


if __name__ == "__main__":
    unittest.main()
