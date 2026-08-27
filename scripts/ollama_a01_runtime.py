#!/usr/bin/env python3
"""Bridge a local Ollama model to LEONES' canonical A01 JSONL contract.

The process receives the A01 prompt as its final argv argument, calls the
local Ollama API, and emits exactly two canonical tool-request JSON lines.
Runtime-reported throughput is emitted as a separate JSON line so LEONES can
record measured_tps without inventing it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama API request failed: {exc}") from exc


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "lookup_model",
                "description": "Look up the selected LEONES model by its exact model id.",
                "parameters": {
                    "type": "object",
                    "required": ["model_id"],
                    "properties": {"model_id": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_report",
                "description": "Write the A01 report artifact.",
                "parameters": {
                    "type": "object",
                    "required": ["path"],
                    "properties": {"path": {"type": "string"}},
                },
            },
        },
    ]


def get_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    calls = message.get("tool_calls")
    return calls if isinstance(calls, list) else []


def canonical_call(call: dict[str, Any]) -> dict[str, Any]:
    function = call.get("function") or {}
    name = function.get("name")
    arguments = function.get("arguments") or {}
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    if not isinstance(arguments, dict):
        raise ValueError("Ollama returned non-object tool arguments")
    return {"tool": name, "arguments": arguments}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:0.5b-instruct-q4_K_M")
    parser.add_argument("--url", default="http://127.0.0.1:11434/api/chat")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("prompt", nargs="?", default="Execute A01. Return only JSONL tool calls.")
    args = parser.parse_args()

    system = (
        "You are the LEONES A01 execution agent. You MUST use the supplied tools. "
        "First call lookup_model with the exact selected model id: " + args.model + ". "
        "After receiving its result, call write_report with path report.txt. "
        "Do not answer conversationally. Do not call any other tool."
    )
    tools = tool_definitions()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": args.prompt},
    ]
    total_eval_tokens = 0
    total_eval_seconds = 0
    first = post_json(args.url, {
        "model": args.model,
        "messages": messages,
        "tools": tools,
        "stream": False,
        "options": {"temperature": 0},
    }, args.timeout)
    total_eval_tokens += int(first.get("eval_count") or 0)
    total_eval_seconds += int(first.get("eval_duration") or 0)
    message = first.get("message") or {}
    calls = get_tool_calls(message)
    if not calls:
        raise RuntimeError("Ollama model did not produce a tool call")

    # Some runtimes may emit both calls in one response. If so, preserve order.
    if len(calls) >= 2:
        canonical = [canonical_call(call) for call in calls[:2]]
    else:
        first_call = canonical_call(calls[0])
        if first_call["tool"] != "lookup_model":
            raise RuntimeError("A01 first tool call must be lookup_model")
        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_name": "lookup_model",
            "content": json.dumps({"id": args.model, "name": args.model}, ensure_ascii=False),
        })
        second = post_json(args.url, {
            "model": args.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": 0},
        }, args.timeout)
        total_eval_tokens += int(second.get("eval_count") or 0)
        total_eval_seconds += int(second.get("eval_duration") or 0)
        second_calls = get_tool_calls(second.get("message") or {})
        if not second_calls:
            raise RuntimeError("Ollama model did not produce write_report after lookup_model")
        canonical = [first_call, canonical_call(second_calls[0])]

    if [item.get("tool") for item in canonical] != ["lookup_model", "write_report"]:
        raise RuntimeError("A01 requires lookup_model followed by write_report")
    if canonical[0].get("arguments", {}).get("model_id") != args.model:
        raise RuntimeError("A01 lookup_model model_id does not match selected model")

    print(json.dumps(canonical[0], ensure_ascii=False))
    print(json.dumps(canonical[1], ensure_ascii=False))
    if total_eval_tokens > 0 and total_eval_seconds > 0:
        measured_tps = total_eval_tokens / (total_eval_seconds / 1_000_000_000)
        print(json.dumps({"measured_tps": round(measured_tps, 4)}, ensure_ascii=False))
    else:
        print(json.dumps({"measurement_status": "runtime_value_not_reported"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
