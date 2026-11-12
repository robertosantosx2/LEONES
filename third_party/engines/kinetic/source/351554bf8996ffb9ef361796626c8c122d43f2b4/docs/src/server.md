# Server API

`kinetic serve <model>` speaks the OpenAI API at `http://127.0.0.1:8080/v1`.
Any OpenAI client works: point its base URL there and give any API key.

| Endpoint | Method | Served for |
|---|---|---|
| `/v1/health` | GET | every model |
| `/v1/models` | GET | every model |
| `/v1/chat/completions` | POST | text models |
| `/v1/completions` | POST | text models |
| `/v1/embeddings` | POST | embedding models |
| `/v1/rerank` (or `/v1/reranking`) | POST | ranking models |

The paths also answer without the `/v1` prefix, except `/completions` and
`/embeddings`, which are llama-server's there (see
[llama-server API](#llama-server-api)). Bodies are JSON, sent with
`Content-Type: application/json`. A request to an endpoint the loaded model
does not serve, such as `/v1/embeddings` on a text model, is answered with a
400 error that says which endpoint to use.

`/v1/health` answers `{"status": "ok"}` once the model is loaded.

## Models

```sh
curl http://127.0.0.1:8080/v1/models
```

```json
{"object": "list", "data": [{"id": "model", "object": "model", "created": 1762171200,
  "owned_by": "kinetic", "context_length": 32768}]}
```

The id is the model's file name without its extension. One model is served;
the `model` field of requests is accepted and not checked.

## Chat completions

```sh
curl http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" -d '{
  "messages": [
    {"role": "system", "content": "Answer briefly."},
    {"role": "user", "content": "What is the capital of France?"}
  ],
  "max_tokens": 64,
  "temperature": 0
}'
```

The messages go through the model's own chat template. Content is a string
or a list of parts of type `text` and `image_url`.

| Field | Meaning |
|---|---|
| `messages` | the conversation |
| `max_tokens`, `max_completion_tokens` | most tokens to generate [default: until the answer ends or the context is full] |
| `temperature` | 0 to 100; 0 always takes the likeliest token |
| `top_p`, `top_k`, `min_p` | sampling filters; `top_k` 0 or below keeps all tokens |
| `repeat_penalty` (or `repetition_penalty`) | 1 for none |
| `presence_penalty`, `frequency_penalty` | -2 to 2 |
| `seed` | makes sampled answers repeatable |
| `logit_bias` | `{"token id": bias}`, -100 to 100 added to the logit; -100 bans the token |
| `logprobs`, `top_logprobs` | `true` and 0 to 20 alternatives: each token's log-probability, in `choices[].logprobs.content`, streamed chunks included |
| `typical_p` | locally typical sampling; 1 for none |
| `top_n_sigma` | keep tokens within N standard deviations of the best logit; -1 for none |
| `xtc_probability`, `xtc_threshold` | XTC: with that chance, drop every token at least `xtc_threshold` likely but the least likely one [default: 0, 0.1] |
| `dry_multiplier`, `dry_base`, `dry_allowed_length`, `dry_penalty_last_n`, `dry_sequence_breakers` | DRY repetition penalty [default: 0 (off), 1.75, 2, -1 (all), `["
", ":", "\"", "*"]`] |
| `mirostat`, `mirostat_tau`, `mirostat_eta` | Mirostat 1 or 2 in place of the penalties and filters [default: 0 (off), 5, 0.1] |
| `stop` | a string or a list of strings that end the answer |
| `stream` | send the answer as server-sent events |
| `stream_options.include_usage` | add a last chunk with the token counts |
| `response_format` | `{"type": "json_object"}` for any JSON, or `{"type": "json_schema", "json_schema": {"schema": {...}}}` for JSON that matches a schema |
| `grammar` | a GBNF grammar the answer must follow, as llama-server takes it |
| `chat_template_kwargs` | variables for the chat template, such as `{"enable_thinking": true}` |
| `tools` | functions the model may call, as `{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}` |
| `tool_choice` | `auto` (the default), `none`, `required`, or `{"type": "function", "function": {"name": ...}}` to offer only that function |

Defaults come from the model file's recommended sampling where it has them.

Samplers run in llama.cpp's default order: logit bias, repeat, presence and
frequency penalties, DRY, top-n-sigma, top-k, typical, top-p, min-p, XTC,
temperature. With Mirostat it is logit bias, temperature, Mirostat. The
names and meanings follow llama-server's. Log-probabilities are those of the
model's raw logits, as llama-server reports them, before any sampler. With
speculative decoding every sampler stays exact: a seeded answer and its
log-probabilities are the same with drafting as without.

`/v1/completions` takes `logprobs` as a count of alternatives, 0 to 20, and
answers in the legacy shape: `tokens`, `token_logprobs`, `top_logprobs` and
`text_offset`.
Speculative decoding never changes an answer: greedy requests give exactly
the plain greedy tokens, and seeded ones the same answer for the same seed.

The response:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1762171200,
  "model": "model",
  "choices": [{"index": 0,
    "message": {"role": "assistant", "content": "Paris."},
    "logprobs": null, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 25, "completion_tokens": 3, "total_tokens": 28,
    "prompt_tokens_details": {"cached_tokens": 0}}
}
```

`finish_reason` is `stop` when the model ended its answer or a stop string
was reached, `tool_calls` when it called tools, and `length` when
`max_tokens` or the context ran out. For
models that think before they answer, with `enable_thinking` on, the
thinking comes separately as `reasoning_content`. `cached_tokens` counts the
prompt tokens that were not recomputed because an earlier request already
ran them.

### Streaming

With `"stream": true` the answer comes as `chat.completion.chunk` events,
each with a `delta`, and ends with `data: [DONE]`:

```
data: {"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Par"},"finish_reason":null}],...}
data: {"object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"is."},"finish_reason":null}],...}
data: {"object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],...}
data: [DONE]
```

### Tool calls

With `tools`, the model may answer with calls instead of, or after, text:

```json
"message": {"role": "assistant", "content": null, "tool_calls": [
  {"id": "call-...", "type": "function",
   "function": {"name": "get_weather", "arguments": "{\"city\":\"Paris\"}"}}]}
```

Send the call back as the assistant message and each result as a message
with role `tool`, and the model answers from them:

```json
"messages": [
  {"role": "user", "content": "What is the weather in Paris?"},
  {"role": "assistant", "content": "", "tool_calls": [
    {"id": "call-1", "type": "function",
     "function": {"name": "get_weather", "arguments": "{\"city\":\"Paris\"}"}}]},
  {"role": "tool", "tool_call_id": "call-1", "content": "{\"temp_c\": 18, \"sky\": \"clear\"}"}
]
```

Give the assistant message's `content` as a string, `""` when it has only
calls; some chat templates fail on a `null` content. Streamed, text before the
calls comes as it is written and the calls arrive whole in one
`delta.tool_calls` chunk, numbered by `index`. Kinetic reads the call
formats of Qwen3.5, Qwen3, LFM3, LFM2, Llama 3 and Mistral models.

`"tool_choice": "required"` and `{"type": "function", "function": {"name":
"get_weather"}}` hold the reply to calls with a grammar in the chat
template's own call format: XML calls for Qwen3.5 and LFM3, JSON in
`<tool_call>` for Qwen3 and Hermes-style templates, a JSON list in LFM2's
markers or after Mistral's `[TOOL_CALLS]`, and a bare JSON object for Llama 3
and other templates. Names and arguments follow each tool's JSON Schema (in
the XML format, the parameter names; values are free text). An open
`<think>` block is closed first, and templates that know `<think>` may
reason in a whole block before the call. The reply holds one call unless
the request sets `"parallel_tool_calls": true`, as in llama-server. Drafted tokens are checked against the same
grammar, so speculative decoding gives the reply plain decoding gives.
`"none"` hides the tools; a forced call cannot be combined with `grammar` or
`response_format`.

### Structured output

`response_format` and `grammar` hold the answer to a shape while it is
generated, so it always parses:

```sh
curl http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" -d '{
  "messages": [{"role": "user", "content": "Give me a person."}],
  "temperature": 0,
  "response_format": {"type": "json_schema", "json_schema": {"name": "person", "schema": {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    "required": ["name", "age"]}}}
}'
```

```json
"message": {"role": "assistant", "content": "{
  \"name\": \"Ethan\",
  \"age\": 25
}"}
```

`{"type": "json_object"}` allows any JSON value, and `grammar` takes a GBNF
grammar in llama.cpp's syntax, such as `root ::= "yes" | "no"`. A request
may use one of `grammar` and `response_format`, not both.

### Receipts

`"receipt": true` on `/v1/chat/completions` or `/v1/completions` adds a
`receipt` object to the response (to the last chunk of a stream) that
`kinetic verify-receipt` can rerun; see [Receipts](receipts.md). A request
without a `seed` gets a fresh one, recorded in the receipt. Receipts are
signed when the server was started with `--sign-key`. Requests with images
cannot have a receipt yet.

```sh
curl http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" -d '{
  "messages": [{"role": "user", "content": "Name three rivers."}],
  "temperature": 0.8, "seed": 42, "receipt": true
}' | python -c "import json,sys; json.dump(json.load(sys.stdin)['receipt'], open('answer.json','w'))"
kinetic verify-receipt answer.json
```

### Reasoning

Models that think before they answer, such as Qwen3 and Qwen3.5, do so when
their template's `enable_thinking` is on, which is the template's own
default unless you set it:

```json
"chat_template_kwargs": {"enable_thinking": true}
```

The thinking then comes apart from the answer, as `reasoning_content` in the
message (or in `delta.reasoning_content` when streamed), and `content` holds
only the answer.

### Images

Started with `--mmproj`, a vision model reads images given as parts of a
message, in PNG or JPEG. Images must be inline base64 data URLs; the server
fetches nothing.

```json
{"role": "user", "content": [
  {"type": "text", "text": "What is in this picture?"},
  {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgo..."}}
]}
```

## Prefill

```sh
curl http://127.0.0.1:8080/v1/prefill -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Here is the report: ... What does it"}]}'
```

[Zero Wait](how-it-is-fast.md#zero-wait) for apps: send the conversation
while the user is still writing the last message, as often as it changes,
and the chat completion that follows only runs what is new. The body is
that of a chat completion; only `messages`, `tools` and
`chat_template_kwargs` matter, and they must match the request that
follows. The prompt is run up to just before the last word of the last
message, which may still grow, so the reply waits for that part, in whole
batches, on a free slot. It answers once that is done, or as soon as a
newer prefill or a real request comes in:

```json
{"object": "prefill", "cached_tokens": 19968}
```

It never changes what a request generates, and a request never waits for
more than one batch of it.

## Completions

```sh
curl http://127.0.0.1:8080/v1/completions -H "Content-Type: application/json" \
  -d '{"prompt": "The capital of France is", "max_tokens": 8, "temperature": 0}'
```

Continues `prompt`, a string or a list of one string, exactly as written,
without the chat template. It takes the same fields as chat completions
apart from `messages` and `chat_template_kwargs`, and answers with
`text_completion` objects whose choices carry `text`.

## Embeddings

```sh
kinetic serve bge-small-en-v1.5-f16.gguf
curl http://127.0.0.1:8080/v1/embeddings -H "Content-Type: application/json" \
  -d '{"input": ["a cat", "a dog"]}'
```

`input` is a string, a list of up to 256 strings, a list of token ids, or a
list of such lists. `encoding_format` is `float` (the default) or `base64`
for little-endian 32-bit floats.

```json
{"object": "list", "model": "bge-small-en-v1.5-f16",
 "data": [{"object": "embedding", "index": 0, "embedding": [0.0123, ...]}, ...],
 "usage": {"prompt_tokens": 8, "total_tokens": 8}}
```

## Rerank

```sh
kinetic serve qwen3-reranker-0.6b-q8_0.gguf
curl http://127.0.0.1:8080/v1/rerank -H "Content-Type: application/json" -d '{
  "query": "What is the capital of China?",
  "documents": ["The capital of China is Beijing.", "Gravity pulls bodies together."],
  "top_n": 2, "return_documents": true
}'
```

Each document, a string or an object with `text`, is scored against the
query with the model's rerank template; up to 256 at once. The answer lists
them most relevant first, `top_n` of them [default: all]:

```json
{"object": "list", "model": "qwen3-reranker-0.6b-q8_0",
 "results": [{"index": 0, "relevance_score": 0.9996, "document": {"text": "The capital of China is Beijing."}},
             {"index": 1, "relevance_score": 0.00004, "document": {"text": "Gravity pulls bodies together."}}],
 "usage": {"prompt_tokens": 152, "total_tokens": 152}}
```

The scores are probabilities, as llama-server's are for the same model.

## Errors

Errors come in the OpenAI shape with a matching HTTP status:

```json
{"error": {"message": "max_tokens must be at least 1", "type": "invalid_request_error", "param": null, "code": null}}
```

| Status | When |
|---|---|
| 400 | the request is invalid or cannot be served, such as a prompt longer than the context |
| 404 | no such endpoint |
| 405 | wrong method for the endpoint |
| 415 | the body is not sent as `application/json` |
| 503 | 64 connections are already open |

Not supported yet: `n` other than 1.

## Requests at once

The server accepts up to 64 connections. With `--parallel N` (llama.cpp's
`-np N`) up to N requests run at once and share each pass over the weights, on the
CPU and on CUDA when the whole model is on the GPU; every answer is exactly
what that request would get on its own. The CPU default fits as many
full-context sequences as half the free memory holds, up to 4. With a layer
split, expert offload or on Vulkan, requests take turns. `/health` and
`/slots` report idle and busy slots.

A request that continues the previous conversation reuses its work, so only
the new tokens run, and any prompt that starts like an earlier one resumes
from where that one's state was kept, when that is faster than recomputing
it (see [Warm Start](how-it-is-fast.md#warm-start)). `cached_tokens` in the
usage says how many prompt tokens were reused.

## Ollama API

The same server answers Ollama's API, so apps written for Ollama work
unchanged; `kinetic serve <model> --ollama` listens on Ollama's port 11434.

| Endpoint | Does |
|---|---|
| `GET /api/version`, `GET /api/tags`, `GET /api/ps` | the version and the one model served |
| `POST /api/show` | its details, metadata, chat template and capabilities |
| `POST /api/chat`, `POST /api/generate` | answers, streamed as NDJSON unless `"stream": false` |
| `POST /api/embed`, `POST /api/embeddings` | vectors, from an embedding model |

`options` takes `temperature`, `top_k`, `top_p`, `min_p`, `seed`,
`num_predict`, `stop`, `repeat_penalty`, `repeat_last_n`,
`presence_penalty` and `frequency_penalty`; `format` takes `"json"` or a JSON
schema; `tools`, `think` and `images` work as in Ollama, and tool call
arguments come back as objects. `suffix`, `template` and `context` are
refused with an error. Requests whose browser `Origin` is not this computer
are refused, since Ollama clients send bodies of any content type.

## llama-server API

The same server answers llama.cpp's own server API, so scripts and apps
written for `llama-server` work unchanged.

| Endpoint | Does |
|---|---|
| `POST /completion` (or `/completions`) | continues `prompt`, streamed as server-sent events with `"stream": true` |
| `POST /tokenize`, `POST /detokenize` | text to token ids (with `add_special`, `parse_special`, `with_pieces`) and back |
| `GET /props`, `GET /slots` | the model, its context and sampling defaults, and the slots: per slot `id_task`, `n_prompt_tokens`, `n_prompt_tokens_processed`, `n_prompt_tokens_cache`, `params`, `next_token` (`n_decoded`, `n_remain`) and `prompt` of its current or last request |
| `GET /metrics` | Prometheus text, under llama-server's `llamacpp:` names |
| `POST /embedding` | vectors, from an embedding model |

`/completion` takes `prompt` (text or token ids), `n_predict`, `temperature`,
`top_k`, `top_p`, `min_p`, `repeat_penalty`, `presence_penalty`,
`frequency_penalty`, `seed`, `stop`, `stream`, `grammar` and `json_schema`;
`cache_prompt` is always on. `n_probs` is accepted but token probabilities
are not returned yet, a stop string reads as `"stop_type": "eos"`, and
streamed pieces carry no token ids. `scripts/llama_server_compat.py` runs
both servers on one GGUF and lists every field that still differs. Like the
Ollama routes, these take bodies of any content type and refuse requests
whose browser `Origin` is not this computer.

## Metrics

`GET /metrics` (also `/v1/metrics`) answers in Prometheus' text format with
llama-server's metric names, so its dashboards work unchanged. Counters
since start: `llamacpp:requests_total`, `prompt_tokens_total` (prompt tokens
run), `prompt_tokens_cached_total` (prompt tokens reused from an earlier
request), `prompt_seconds_total`, `tokens_predicted_total`,
`tokens_predicted_seconds_total` and `n_tokens_max`. Gauges:
`prompt_tokens_seconds` and `predicted_tokens_seconds` (average prompt and
generation speed since start), `requests_processing` and
`requests_deferred` (waiting for a free slot). It is always on; llama.cpp's
`--metrics` and `--slots` are accepted and change nothing.

```sh
curl -s localhost:8080/metrics | grep -v '^#'
```

## Security

The server listens on `127.0.0.1` by default and has no authentication
unless started with `--api-key KEY`; then every route but `/health` needs
`Authorization: Bearer KEY` (or `X-Api-Key: KEY`, as llama-server takes it)
and answers 401 with an `authentication_error` otherwise. Listening on
another address with `--host` makes the model usable by anyone who can reach
that address; use `--api-key` there, and a TLS proxy if the key crosses an
untrusted network. Browsers cannot send JSON to the server from another site, so web
pages you visit cannot use it. A client has 30 seconds to send its request.
Kinetic never connects to the network, except when you run `kinetic pull`.
The server never downloads anything.
