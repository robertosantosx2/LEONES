#!/usr/bin/env python3
"""Convert a real llama.cpp execution log into runtime-benchmark-evidence.v1.1.

This bridge is parser-only: it never executes the runtime and never fabricates
performance measurements. Missing measurements remain null. The input log
must contain the command/environment provenance emitted by the JALON 2
physical runner and /usr/bin/time output.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KV_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$")
PERF_RE = re.compile(
    r"(?P<label>prompt eval|eval|generation)[^\n]*?=\s*(?P<ms>[0-9]+(?:\.[0-9]+)?)\s*ms"
    r"\s*/\s*(?P<tokens>[0-9]+)\s*(?:tokens?|runs?)?[^\n]*?"
    r"(?P<tps>[0-9]+(?:\.[0-9]+)?)\s*tokens?/s",
    re.I,
)
TPS_RE = re.compile(
    r"(?:Generation|eval)[^\n]*?[:=]\s*(?P<tps>[0-9]+(?:[.,][0-9]+)?)\s*t/s",
    re.I,
)

LLAMA_SUMMARY_RE = re.compile(
    r"\[\s*Prompt:\s*(?P<prompt>[0-9]+(?:[.,][0-9]+)?)\s*t/s"
    r"\s*\|\s*Generation:\s*(?P<generation>[0-9]+(?:[.,][0-9]+)?)\s*t/s"
    r"\s*\]",
    re.I,
)


MAX_RSS_RE = re.compile(
    r"Maximum resident set size \(kbytes\):\s*(?P<kb>[0-9]+)",
    re.I,
)

ELAPSED_RE = re.compile(
    r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(?P<elapsed>[0-9]+(?::[0-9]+){1,2}(?:\.[0-9]+)?)",
    re.I,
)

def _timestamp(value: str) -> str:
    """Normalize an ISO-8601 timestamp while preserving the UTC instant."""
    from datetime import datetime, timezone

    value = value.strip()
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _first(text: str, pattern: str, default: str | None = None) -> str | None:
    match = re.search(pattern, text, re.I | re.M)
    return match.group(1).strip() if match else default


def _wall_seconds(value: str | None) -> float | None:
    if not value:
        return None

    value = value.strip()

    try:
        parts = value.split(":")

        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds

        return float(value)
    except ValueError:
        return None


CMD_RE = re.compile(
    r'^\s*Command being timed:\s*"(?P<cmd>.*)"\s*$',
    re.M,
)


def _command_and_prompt(text: str) -> tuple[list[str], str | None]:
    # Preferimos el argv exacto conservado por el runner.
    marker = "===== COMMAND ====="
    marker_pos = text.find(marker)

    if marker_pos >= 0:
        command_lines = text[marker_pos + len(marker):].splitlines()

        for line in command_lines:
            line = line.strip()
            if line and not line.startswith("="):
                try:
                    command = shlex.split(line)
                except ValueError:
                    command = line.split()

                prompt = None
                for flag in ("-p", "--prompt"):
                    if flag in command:
                        index = command.index(flag)
                        if index + 1 < len(command):
                            prompt = " ".join(command[index + 1:])
                        break

                return command, prompt

    # Fallback para logs generados directamente por /usr/bin/time.
    match = CMD_RE.search(text)
    if match:
        command_text = match.group("cmd")
        try:
            command = shlex.split(command_text)
        except ValueError:
            command = command_text.split()

        prompt = None
        for flag in ("-p", "--prompt"):
            if flag in command:
                index = command.index(flag)
                if index + 1 < len(command):
                    prompt = " ".join(command[index + 1:])
                break

        return command, prompt

    return [], None


def parse_log(text: str) -> dict[str, Any]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        match = KV_RE.match(line.strip())
        if match:
            metadata[match.group("key")] = match.group("value").strip()

    execution_id = metadata.get("execution_id")
    timestamp_start = metadata.get("timestamp_utc")
    timestamp_end = metadata.get("timestamp_end_utc")
    if not execution_id or not timestamp_start:
        raise ValueError("physical log requires execution_id and timestamp_utc")
    if not timestamp_end:
        raise ValueError("physical log requires explicit timestamp_end_utc")

    command, prompt = _command_and_prompt(text)
    rss = MAX_RSS_RE.search(text)
    peak_memory_mb = float(rss.group("kb")) / 1024 if rss else None
    wall_seconds = _wall_seconds(_first(text, ELAPSED_RE.pattern))

    prompt_ms = None
    generation_ms = None
    output_tokens = None
    measured_tps = None
    for match in PERF_RE.finditer(text):
        label = match.group("label").lower()
        ms = float(match.group("ms"))
        tokens = int(match.group("tokens"))
        tps = float(match.group("tps"))
        if label.startswith("prompt"):
            prompt_ms = ms
        else:
            generation_ms = ms
            output_tokens = tokens
            measured_tps = tps

    prompt_tokens_per_second = None

    summary_match = LLAMA_SUMMARY_RE.search(text)
    if summary_match:
        prompt_tokens_per_second = float(
            summary_match.group("prompt").replace(",", ".")
        )
        measured_tps = float(
            summary_match.group("generation").replace(",", ".")
        )

    # El resumen moderno de llama.cpp expresa throughput del prompt,
    # no TTFT. Solo usamos prompt_ms como TTFT cuando procede del
    # registro explícito "prompt eval time".
    ttft_ms = None if summary_match else prompt_ms

    if measured_tps is None:
        tps_match = TPS_RE.search(text)
        if tps_match:
            measured_tps = float(tps_match.group("tps").replace(",", "."))

    model = metadata.get("model") or ""
    model_sha256 = metadata.get("model_sha256")
    binary_sha256 = metadata.get("runtime_binary_sha256")
    runtime_version = metadata.get("runtime_version") or metadata.get("runtime_package") or "unknown"
    quantization_match = re.search(r"(Q[0-9]+(?:_[A-Z0-9]+)+)(?:\.gguf)?(?:$|\s)", model, re.I)
    quantization = quantization_match.group(1).upper() if quantization_match else "unknown"
    measurement: dict[str, Any] = {
        "iteration": 1,
        "ttft_ms": ttft_ms,
        "first_output_ms": ttft_ms,
        "generation_time_ms": generation_ms,
        "output_tokens": output_tokens,
        "tokens_per_second": measured_tps,
        "total_time_ms": wall_seconds * 1000 if wall_seconds is not None else 0.0,
        "peak_memory_mb": peak_memory_mb,
        "peak_vram_mb": None,
        "power_w": None,
        "exit_code": int(metadata.get("exit_status", "0")),
        "stdout": text,
        "stderr": "",
    }

    return {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": execution_id,
        "timestamp_start": _timestamp(timestamp_start),
        "timestamp_end": _timestamp(timestamp_end),
        "model": {
            "id": model.removesuffix(".gguf"),
            "name": model,
            "revision": "unknown",
            "source": None,
            "artifact": f"artifacts/models/{model}" if model else "",
            "quantization": quantization,
            "context_length": int(metadata.get("ctx_size", "1")),
        },
        "protocol": {
            "prompt_protocol_id": "leones-local-v1",
            "prompt": prompt or "",
            "input_tokens": None,
            "prompt_tokens_per_second": prompt_tokens_per_second,
            "output_token_limit": int(metadata["n_predict"]) if metadata.get("n_predict", "").isdigit() else None,
            "temperature": 0,
            "top_p": None,
            "seed": None,
            "context": int(metadata.get("ctx_size", "1")),
            "warmup_iterations": 1 if metadata.get("warmup", "").lower() == "enabled" else 0,
            "measurement_iterations": 1,
        },
        "runtime": {
            "name": metadata.get("runtime", "llama.cpp"),
            "version": runtime_version,
            "revision": None,
            "backend": "CPU" if "CPU backend" in text else None,
            "command": command,
            "binary": metadata.get("runtime_binary"),
            "binary_sha256": binary_sha256,
        },
        "hardware": {
            "host": metadata.get("host"),
            "os": metadata.get("os", "unknown"),
            "kernel": metadata.get("kernel", "unknown"),
            "architecture": "x86_64",
            "cpu": metadata.get("cpu", "unknown"),
            "cpu_threads": int(metadata["cpu_threads"]) if metadata.get("cpu_threads", "").isdigit() else None,
            "physical_cores": int(metadata["physical_cores"]) if metadata.get("physical_cores", "").isdigit() else None,
            "ram_total_mb": (
                float(metadata["ram_total_mb"])
                if metadata.get("ram_total_mb")
                else _ram_mb(text)
            ),
            "gpu": None,
        },
        "measurements": [measurement],
        "summary": {
            "tokens_per_second": {"mean": measured_tps, "median": measured_tps, "min": measured_tps, "max": measured_tps},
            "ttft_ms": {"mean": ttft_ms, "median": ttft_ms, "min": ttft_ms, "max": ttft_ms},
            "total_time_ms": {"mean": measurement["total_time_ms"], "median": measurement["total_time_ms"], "min": measurement["total_time_ms"], "max": measurement["total_time_ms"]},
            "peak_memory_mb": {"mean": peak_memory_mb, "median": peak_memory_mb, "min": peak_memory_mb, "max": peak_memory_mb},
        },
        "process": {"exit_code": measurement["exit_code"], "stdout": text, "stderr": ""},
        "artifact": {
            "path": f"artifacts/models/{model}" if model else "",
            "sha256": model_sha256 or "0" * 64,
            "size": int(metadata.get("model_size_bytes", "0")),
        },
        "provenance": {
            "prompt_sha256": metadata.get("prompt_sha256"),
            "runtime_binary_sha256": binary_sha256,
            "runtime_binary": metadata.get("runtime_binary"),
            "wall_seconds": wall_seconds,
        },
    }


def _ram_mb(text: str) -> float | None:
    total = re.search(r"^Mem:\s+(?P<total>[0-9]+(?:\.[0-9]+)?)(?P<unit>[MG]i?)", text, re.M)
    if not total:
        return None
    value = float(total.group("total"))
    return value * 1024 if total.group("unit").lower().startswith("g") else value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--timestamp-end", required=True, help="UTC execution end timestamp, ISO-8601")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--execution",
        type=Path,
        help="Optional runtime-execution.v1 JSON used to cross-check execution provenance.",
    )
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8")

    if args.execution:
        execution = json.loads(
            args.execution.read_text(encoding="utf-8")
        )

        if execution.get("schema") != "runtime-execution.v1":
            raise SystemExit(
                "execution artifact is not runtime-execution.v1"
            )

        execution_id = execution.get("execution_id")
        if not execution_id:
            raise SystemExit(
                "execution artifact has no execution_id"
            )

        if f"execution_id={execution_id}" not in text:
            raise SystemExit(
                "execution_id mismatch between execution JSON and log"
            )
    lines = text.splitlines()
    lines.append(f"timestamp_end_utc={args.timestamp_end}")
    evidence = parse_log("\n".join(lines) + "\n")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"schema": evidence["schema"], "execution_id": evidence["execution_id"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
