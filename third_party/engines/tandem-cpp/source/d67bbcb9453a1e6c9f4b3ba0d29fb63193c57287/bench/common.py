"""Shared helpers for the tandem.cpp benchmarks (stdlib only, OpenAI-compatible servers)."""
import json
import os
import time
import urllib.request


def stream_chat(port, model, messages, max_tokens, extra=None):
    """One streamed greedy chat completion. Returns (metrics, text).
    gen_s = last token time - first token time; ttft_s = first token - request start.
    text = answer content only; metrics["reasoning"] = the separated thinking text."""
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0, "stream": True, "ignore_eos": True,
            "stream_options": {"include_usage": True}}
    # LC_SAMPLING=default: the model's own sampling (Qwen3.8 generation_config: T 1.0, top_k 20, top_p 0.95).
    if os.environ.get("LC_SAMPLING") == "default":
        body.update({"temperature": 1.0, "top_k": 20, "top_p": 0.95, "seed": int(os.environ.get("LC_SEED", "1"))})
    # LC_SAMPLING=gptoss: gpt-oss's recommended sampling (T 1.0, top_p 1.0, no top-k)
    elif os.environ.get("LC_SAMPLING") == "gptoss":
        body.update({"temperature": 1.0, "top_k": 0, "top_p": 1.0, "seed": int(os.environ.get("LC_SEED", "1"))})
    # LC_SAMPLING=ds4: DeepSeek-V4.1's evaluation sampling (README: T 1.0, top_p 0.95, no top-k)
    elif os.environ.get("LC_SAMPLING") == "ds4":
        body.update({"temperature": 1.0, "top_k": 0, "top_p": 0.95, "seed": int(os.environ.get("LC_SEED", "1"))})
    # LC_SAMPLING=server: no sampling fields, the server's own defaults (models whose GGUF records none, e.g. GLM-4.5-Air)
    elif os.environ.get("LC_SAMPLING") == "server":
        del body["temperature"]
        body["seed"] = int(os.environ.get("LC_SEED", "1"))
    # LC_THINK_OFF=1: thinking off per request (engines without a server switch like -rea off)
    if os.environ.get("LC_THINK_OFF") == "1":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    body.update(extra or {})
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first = last = None
    text, reasoning, usage = [], [], None
    with urllib.request.urlopen(req, timeout=3600) as r:
        for line in r:
            if not line.startswith(b"data: ") or line.strip() == b"data: [DONE]":
                continue
            ev = json.loads(line[6:])
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices", []):
                d = ch.get("delta", {})
                piece = (d.get("content") or "") + (d.get("reasoning_content") or d.get("reasoning") or "")
                if piece:
                    last = time.perf_counter()
                    if first is None:
                        first = last
                text.append(d.get("content") or "")
                reasoning.append(d.get("reasoning_content") or d.get("reasoning") or "")
    t1 = time.perf_counter()
    n = (usage or {}).get("completion_tokens", 0)
    gen_s = (last - first) if first and last and last > first else 0.0
    return {"ttft_s": (first or t1) - t0, "gen_s": gen_s, "wall_s": t1 - t0,
            "completion_tokens": n, "prompt_tokens": (usage or {}).get("prompt_tokens", 0),
            "reasoning": "".join(reasoning)}, "".join(text)
