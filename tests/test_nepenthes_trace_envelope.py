from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from nepenthes_llama_trace_import import import_trace  # noqa: E402


def event(source: str = "tensorfold", **overrides: object) -> dict:
    record = {
        "schema_version": "1.0", "run_id": "tf-run", "event_id": "tf-1",
        "source": source, "timestamp_unix_ns": 1_800_000_000_000_000_000,
        "monotonic_ns": 100, "request_id": 7, "event_kind": "request_start",
        "label": "server.request", "value0": 0, "value1": 0,
        "duration_ns": 0, "flags": 0, "clock_domain": "steady_clock",
    }
    record.update(overrides)
    return record


def summary(source: str = "tensorfold", **overrides: object) -> dict:
    record = {
        "schema_version": "1.0", "run_id": "tf-run", "event_id": "tf-summary",
        "source": source, "timestamp_unix_ns": 1_800_000_000_000_000_100,
        "event_kind": "sink_summary", "events_drained": 1,
        "dropped_events": 0, "write_errors": 0,
    }
    record.update(overrides)
    return record


class SharedEnvelopeTests(unittest.TestCase):
    def write_trace(self, records: list[dict]) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "trace.jsonl"
        path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
        return path

    def test_registered_tensorfold_source_accepts_event_and_summary(self) -> None:
        result = import_trace(self.write_trace([event(), summary()]), source="tensorfold")
        self.assertEqual(result["source"], "tensorfold")
        self.assertEqual(result["event_count"], 1)
        self.assertTrue(result["capture_complete"])

    def test_registered_llama_source_remains_compatible(self) -> None:
        llama_event = event("llama.cpp", event_id="llama-1")
        llama_event.pop("clock_domain")
        llama_summary = summary("llama.cpp", event_id="llama-summary")
        result = import_trace(self.write_trace([llama_event, llama_summary]))
        self.assertEqual(result["source"], "llama.cpp")
        self.assertTrue(result["capture_complete"])

    def test_unknown_source_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered NEPENTHES source"):
            import_trace(self.write_trace([event("other-engine"), summary("other-engine")]),
                         source="other-engine")

    def test_event_source_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "event source mismatch"):
            import_trace(self.write_trace([event("tensorfold"), summary("llama.cpp")]),
                         source="llama.cpp")

    def test_summary_source_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "sink summary source mismatch"):
            import_trace(self.write_trace([event("llama.cpp", event_id="llama-1"),
                                           summary("tensorfold")]), source="llama.cpp")

    def test_source_profile_accepts_declared_clock_domain(self) -> None:
        for source in ("llama.cpp", "tensorfold", "tandem.cpp"):
            with self.subTest(source=source):
                result = import_trace(self.write_trace([
                    event(source, event_id=f"{source}-1"),
                    summary(source, event_id=f"{source}-summary"),
                ]), source=source)
                self.assertTrue(result["capture_complete"])

    def test_unsupported_clock_domain_is_rejected_per_source(self) -> None:
        for source in ("llama.cpp", "tensorfold"):
            with self.subTest(source=source):
                bad = event(source, clock_domain="device_clock")
                with self.assertRaisesRegex(ValueError, "unsupported .* clock_domain"):
                    import_trace(self.write_trace([
                        bad, summary(source, event_id=f"{source}-summary")
                    ]), source=source)

    def test_clock_calibration_requires_declared_domain(self) -> None:
        bad = event(event_kind="clock_calibration")
        bad.pop("clock_domain")
        with self.assertRaisesRegex(ValueError, "clock_calibration requires a supported"):
            import_trace(self.write_trace([bad, summary()] ), source="tensorfold")

    def test_duplicate_summary_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "sink_summary must be the final JSONL record"):
            import_trace(self.write_trace([event(), summary(),
                                           summary(event_id="tf-summary-2")]),
                         source="tensorfold")

    def test_summary_missing_and_extra_fields_are_rejected(self) -> None:
        missing = summary()
        del missing["write_errors"]
        with self.assertRaisesRegex(ValueError, "sink summary missing fields"):
            import_trace(self.write_trace([event(), missing]), source="tensorfold")
        extra = summary(unexpected="no")
        with self.assertRaisesRegex(ValueError, "unexpected sink summary fields"):
            import_trace(self.write_trace([event(), extra]), source="tensorfold")

    def test_empty_identifiers_are_rejected(self) -> None:
        for field in ("event_id", "run_id"):
            with self.subTest(field=field):
                bad = event(**{field: ""})
                with self.assertRaisesRegex(ValueError, f"invalid {field}"):
                    import_trace(self.write_trace([bad, summary()]), source="tensorfold")

    def test_unsigned_integer_boundaries_are_enforced(self) -> None:
        for field in ("request_id", "value0", "value1", "duration_ns",
                      "timestamp_unix_ns", "monotonic_ns"):
            with self.subTest(field=field):
                bad = event(**{field: 1 << 64})
                with self.assertRaisesRegex(ValueError, f"{field} exceeds"):
                    import_trace(self.write_trace([bad, summary()]), source="tensorfold")
        bad_flags = event(flags=65536)
        with self.assertRaisesRegex(ValueError, "flags exceeds 65535"):
            import_trace(self.write_trace([bad_flags, summary()]), source="tensorfold")

    def test_bool_is_not_an_unsigned_integer(self) -> None:
        bad = event(request_id=True)
        with self.assertRaisesRegex(ValueError, "request_id must be a non-negative integer"):
            import_trace(self.write_trace([bad, summary()]), source="tensorfold")

    def test_invalid_correlation_attribution_is_rejected(self) -> None:
        bad = event(correlation_token=9, attribution_level="windowed")
        with self.assertRaisesRegex(ValueError, "correlation_token requires exact"):
            import_trace(self.write_trace([bad, summary()]), source="tensorfold")
        bad = event(correlation_token=0, attribution_level="exact")
        with self.assertRaisesRegex(ValueError, "positive unsigned 64-bit"):
            import_trace(self.write_trace([bad, summary()]), source="tensorfold")

    def test_forbidden_private_payload_is_rejected(self) -> None:
        bad = event(prompt="must-not-be-present")
        with self.assertRaisesRegex(ValueError, "forbidden text/token fields"):
            import_trace(self.write_trace([bad, summary()]), source="tensorfold")


if __name__ == "__main__":
    unittest.main()
