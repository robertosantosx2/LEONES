# Quick start

This page assumes `kinetic` is [installed](install.md) and you have a model
file; the examples use `model.gguf`.

## Ask one question

```sh
kinetic run model.gguf "Explain recursion in two sentences."
```

The answer streams to the terminal as it is written. When it is done, a
status line on stderr gives the speed and the device:

```text
Recursion is a programming technique where a function calls itself ...
[45 tokens at 25.5 tok/s; prompt 37 tokens at 62.8 tok/s on the CPU]
```

Without a prompt, `run` reads it from stdin, so files and pipes work:

```sh
kinetic run model.gguf < prompt.txt
git diff | kinetic run model.gguf --system "Write a commit message for this diff." -n 100
```

## Chat

```sh
kinetic chat model.gguf --system "You are a concise assistant."
```

Type a message and press Enter. `/clear` starts a new conversation and
`/exit` (or Ctrl+D) quits. Each turn reuses the work of the previous ones, so
only your new message is processed.

## Pick the sampling

By default Kinetic uses the sampling settings the model file recommends.
Override them as in llama.cpp:

```sh
kinetic run model.gguf "Write a haiku about rivers." --temp 0.8 --top-p 0.95 --seed 42
kinetic run model.gguf "List the planets." --temp 0 -n 64
```

`--temp 0` always takes the likeliest token. With a seed, the same command
gives the same answer every time; speculative decoding never changes that.

## Serve an OpenAI-compatible API

```sh
kinetic serve model.gguf
```

```text
Serving model on the CPU at http://127.0.0.1:8080/v1
```

Any OpenAI client works against this address; the API key can be anything.

```sh
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Name three rivers."}]}'
```

On Windows PowerShell, where `curl` means something else:

```powershell
$body = @{ messages = @(@{ role = "user"; content = "Name three rivers." }) } | ConvertTo-Json -Depth 5
Invoke-RestMethod http://127.0.0.1:8080/v1/chat/completions -Method Post -ContentType application/json -Body $body
```

With the official `openai` package for Python:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="local")
stream = client.chat.completions.create(
    model="model",
    messages=[{"role": "user", "content": "Write a haiku about rivers."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices:
        print(chunk.choices[0].delta.content or "", end="", flush=True)
```

Editors, chat apps and agent frameworks that take an "OpenAI-compatible"
base URL work the same way. The [server API](server.md) lists every endpoint
and field.

## See what a file holds

```sh
kinetic info model.gguf
```

prints the architecture, size, context length, weight types and tokenizer,
and says if the architecture is not supported yet.

## Measure your machine

```sh
kinetic bench model.gguf
```

runs llama-bench's two tests (a 512-token prompt and 128 generated tokens)
and an editing test, and prints a table you can compare with `llama-bench`
on the same file. See [Benchmarks](benchmarks.md).

## Next

- Every option of every command: [Command line](cli.md).
- Images, tools, JSON output, embeddings: [Server API](server.md).
- GPU or CPU, memory, large MoE models: [Devices and offload](devices.md).
