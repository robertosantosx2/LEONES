# Client compatibility

What was checked against `kinetic serve` on Windows 11 (CPU, LFM3 1.7B
Q4_K_M with `-c 512`, and bge-small for embeddings). The client libraries
themselves were not installed: each row replays the HTTP requests that client
sends, with the same paths, fields and headers, from a Python script using
`requests` (`User-Agent: OpenAI/Python`, `Authorization: Bearer ...`).

| Client | Requests replayed | Result |
| --- | --- | --- |
| OpenAI Python SDK | `GET /v1/models`; chat with `stream`, `stream_options.include_usage`; embeddings with the SDK's default `encoding_format: "base64"` | works |
| Open WebUI | `GET /v1/models`, streaming chat; in Ollama mode `GET /api/tags`, `GET /api/version`, streaming `POST /api/chat` | works |
| Continue | streaming chat with a `stop` list and `temperature`; autocomplete on `/v1/completions` with `stop` | works; `suffix` (fill in the middle) is accepted and ignored |
| SillyTavern | text completion on `/v1/completions` with `top_k`, `min_p`, `repetition_penalty`, `typical_p`, `seed`, `logit_bias`, streaming; chat with `presence_penalty`, `frequency_penalty`, `seed` | works, also on the llama-server `/completion` endpoint; sampler fields Kinetic does not have are ignored |
| LangChain `ChatOpenAI` | chat with `n: 1`; `bind_tools` with `tool_choice: "auto"` and `parallel_tool_calls: false`, also streamed; `with_structured_output` (`json_schema`, `strict: true`); a tool result sent back | works; tool calls come back as `tool_calls` |
| LlamaIndex `OpenAILike` | chat with `response_format: {"type": "json_object"}`, content as a list of text parts, `max_completion_tokens` | works; `json_object` allows any JSON value, as in llama.cpp |
| Embeddings (OpenAI, LlamaIndex, LangChain) | `/v1/embeddings` with a string, a list, token ids, `base64`; Ollama `/api/embed`; llama-server `/embedding` | works |
| llama-server clients | `/completion` (plain, streamed, token-id prompts, `grammar`, `json_schema`), `/tokenize` with pieces, `/detokenize`, `/props`, `/slots` | works |

Refused with a 400 and a message, as intended: `n` other than 1, an empty
`messages` list, a prompt longer than the context, `max_tokens` below 1,
`temperature` or `top_p` out of range, unknown `response_format` types and
invalid schemas or grammars. `logprobs: true` with `top_logprobs: 2` returns
each token's log-probability; `top_logprobs` above 20 is refused.

## Robustness

`scripts/server_abuse.py` sends malformed JSON, wrong types, oversized bodies
and headers, chunked bodies, HTTP/2 prefaces, bad input to the llama-server and Ollama routes, a client that sends one byte at
a time, clients that disconnect before the body and in the middle of a
stream, 100 parallel connections and 8 parallel chats, then checks that the
server still answers:

```sh
python scripts/server_abuse.py -- kinetic serve model.gguf -c 512 --port 8091
```

A client that sends its headers and then stalls is disconnected after 30
seconds (`--long` checks this). Up to 64 connections are served at once;
more get a 503.
