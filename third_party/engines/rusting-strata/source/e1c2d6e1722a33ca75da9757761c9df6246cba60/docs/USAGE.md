# Usage

Everything here applies to `rustingstrata chat`, `generate`, `bench` and `serve` unless noted. See the
[README](../README.md) for install and a quick start, and [HOSTING.md](HOSTING.md) for running a server for other people.

## Chat page

`rustingstrata` with no arguments starts the server on http://127.0.0.1:8080 and opens a chat page. The page keeps chats in
the browser, downloads models from Hugging Face (Models and settings; `HF_TOKEN` for gated repos), switches between the
models in the models folder (`%LOCALAPPDATA%\rusting_strata\models` on Windows, `~/.local/share/rusting_strata/models`
elsewhere, or `serve --models-dir`), and shows context use, speed, totals, and CPU, memory and graphics memory use of
the server.

## Flags

- `--ctx` KV cache size in tokens (default 4096).
- `--mtp [N]` speculative decoding with the model's draft head. Greedy tokens stay the same; sampling keeps its
  distribution.
- `--chunk`, `--threads` prefill chunk size and CPU threads. `rustingstrata calibrate` measures the best values for a machine
  and later runs read them from `~/.cache/rusting_strata/strata-<model>.json` unless flags override.
- `--vram-margin` MB of VRAM left free. On a GPU that drives no display, `--vram-margin 256` keeps more experts
  resident (+1-2% prefill); 128 runs out of memory.
- `--kv q8` halves the KV cache (345 instead of 650 MB at 32K) at about 6% slower 32K decode and 14% slower 32K prefill.
- `--allowed-hosts ai-server.lan` (or `STRATA_ALLOWED_HOSTS`) allows a LAN name when `serve` is bound to `0.0.0.0`.
- `--lora PATH:SCALE` applies a LoRA adapter at runtime, see [LORA.md](LORA.md).

## Server API

`serve` speaks the OpenAI chat completions API (`POST /v1/chat/completions`, streamed or not, `GET /v1/models`).

- It runs one request at a time; `--parallel N` (GPU) decodes up to N together (4 requests: 164 tok/s in total on the
  RTX 3060, 41 each; see [HOSTING.md](HOSTING.md)).
- `temperature`, `top_k`, `top_p` and `seed` are honored; decoding is greedy when they are left out.
- `max_tokens` (or `max_completion_tokens`) and `stop` (up to 16 strings) work as in the OpenAI API; `n` must be 1.
- Thinking is off unless a request sets `chat_template_kwargs.enable_thinking` (Anthropic: `thinking: {"type":
  "enabled"}`).
- `tools` and `tool_choice` work as in the OpenAI API: calls come back as `tool_calls` with `finish_reason:
  "tool_calls"`. `tool_choice: "required"` does not force a call.
- The prompt follows the model's own chat template, rendered like llama.cpp's `--jinja`.

`POST /v1/messages` speaks the Anthropic Messages API (text, `tool_use` and `tool_result` blocks, streamed or not, the
key in `x-api-key`, and `POST /v1/messages/count_tokens`), so Claude Code can use the server:

```sh
ANTHROPIC_BASE_URL=http://127.0.0.1:8080 ANTHROPIC_API_KEY=secret ANTHROPIC_MODEL=local ANTHROPIC_SMALL_FAST_MODEL=local claude
```

OpenCode and other agents use the OpenAI address.

## Prompt caching

- When a request repeats the previous request's messages and adds new ones, only the new part is prefilled
  (`usage.prompt_tokens_details.cached_tokens`).
- Qwen3.6's template leaves the think block out of replies before the last user message, so each new user message would
  change the earlier turns and force a full prefill. RustingStrata keeps those blocks by default;
  `--preserve-thinking false` (or `chat_template_kwargs.preserve_thinking` in a request) follows the template.
- A request with another history (an agent's side request for a title or a summary) parks the conversation's state in
  host memory (`--cache-ram`, 4096 MB by default), and the next request that continues it takes it back.
- With customer keys, each key reuses only its own cached conversations; see [HOSTING.md](HOSTING.md).

## Several GPUs

`--device 0,1` splits the layers over the cards in proportion to their free VRAM, so more experts stay resident. The
cards run one after the other, so one request gets more memory, not twice the speed of one card. MTP drafting is off on
a split model. AMD cards clock down in the gaps while the other card works; `echo high >
/sys/class/drm/cardN/device/power_dpm_force_performance_level` (as root, per card) took a two-card split from 44 to 57
tok/s in one report.

## Page cache

Experts that do not fit in VRAM are read from the GGUF through the page cache. A file system that keeps file data out
of the page cache (ZFS with `primarycache=metadata`) makes every run read them from disk again; load the model from a
file system that caches data, or from a tmpfs copy.
