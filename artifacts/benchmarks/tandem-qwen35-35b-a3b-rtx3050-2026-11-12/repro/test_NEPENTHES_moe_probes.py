#!/usr/bin/env python3
"""Unit tests for NEPENTHES MoE probes; standard library only."""
import json
import os
import pathlib
import struct
import tempfile
import time
import unittest

from inspect_NEPENTHES_moe_trace import read_log, read_trace
from moe_runtime_probe import RuntimeProbe
from resource_monitor import parse_pcie_dmon_line


class TraceInspectorTests(unittest.TestCase):
    def test_mct1_layer_routing_summary(self):
        data = bytearray(b"MCT1")
        data += struct.pack("<3I", 1, 2, 1)       # layers, experts/token, groups
        data += struct.pack("<3I", 0, 4, 1)       # device, experts/layer, layers/group
        data += struct.pack("<I", 0)              # layer index
        data += struct.pack("<2d", 1.0, 1.0)      # split, split sum
        data += struct.pack("<3Q", 100, 100, 32) # host, device-host, alignment
        data += struct.pack("<I", 1)              # expert tensor count
        data += struct.pack("<Q", 10)             # expert tensor bytes
        data += struct.pack("<3i", 0, 2, 4)       # layer, top-k, selected IDs
        data += struct.pack("<4i", 1, 2, 1, 3)
        with tempfile.TemporaryDirectory() as tmp:
            trace = pathlib.Path(tmp) / "tiny.trace"
            trace.write_bytes(data)
            result = read_trace(trace)
        layer = result["per_layer"]["0"]
        self.assertEqual(result["routing_events"], 4)
        self.assertEqual(layer["tokens_observed"], 2)
        self.assertEqual(layer["unique_experts_seen"], 3)
        self.assertEqual(tuple(layer["top_experts"][0]), (1, 2))

    def test_verbose_cache_log_aggregation(self):
        log = (
            "llama_moe_cache: ubatch <= 8: hits = 3, misses = 1, hit rate = 75.00%, uploaded = 2.00 MiB\n"
            "llama_moe_cache: ubatch  > 8: hits = 2, misses = 2, hit rate = 50.00%, uploaded = 3.00 MiB\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "server.log"
            path.write_text(log)
            result = read_log(path)
        self.assertEqual(result["cache_log_lines"], 2)
        self.assertEqual(result["hits"], 5)
        self.assertEqual(result["misses"], 3)
        self.assertEqual(result["uploaded_mib"], 5.0)
        self.assertAlmostEqual(result["hit_rate_pct"], 62.5)


class PcieDmonParserTests(unittest.TestCase):
    def test_parse_pcie_dmon_data_row(self):
        row = parse_pcie_dmon_line("    0   2502    207")
        self.assertEqual(row["gpu_index"], 0)
        self.assertEqual(row["pcie_rx_mbps"], 2502.0)
        self.assertEqual(row["pcie_tx_mbps"], 207.0)
        self.assertEqual(row["source"], "nvidia-smi-dmon")

    def test_parse_zero_is_a_valid_measurement(self):
        row = parse_pcie_dmon_line("    0      0      0")
        self.assertEqual(row["pcie_rx_mbps"], 0.0)
        self.assertEqual(row["pcie_tx_mbps"], 0.0)

    def test_ignore_dmon_headers_and_invalid_rows(self):
        self.assertIsNone(parse_pcie_dmon_line("# gpu  rxpci  txpci"))
        row = parse_pcie_dmon_line("    0      -      -")
        self.assertIsNone(row["pcie_rx_mbps"])
        self.assertIsNone(row["pcie_tx_mbps"])


class RuntimeProbeTests(unittest.TestCase):
    def test_process_telemetry_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            probe = RuntimeProbe(tmp, "unit-test", os.getpid(), 0.2)
            probe.start()
            time.sleep(0.25)
            summary = probe.finish()
            path = pathlib.Path(tmp) / "moe_runtime_samples.jsonl"
            rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(summary["request_id"], "unit-test")
        self.assertGreaterEqual(summary["sample_count"], 2)
        self.assertIn("process", rows[0])


if __name__ == "__main__":
    unittest.main()
