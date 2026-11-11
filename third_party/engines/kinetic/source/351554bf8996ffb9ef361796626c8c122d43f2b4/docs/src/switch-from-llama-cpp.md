# Switch from llama.cpp

Your GGUF files work unchanged when their model family is supported (see
[Models and formats](models.md)). Each case below is one step.

## You run llama-server

Write `kinetic serve` where you wrote `llama-server`, and keep every flag:

```sh
llama-server  -m model.gguf -c 8192 -ngl 99 -fa on --jinja --port 8080
kinetic serve -m model.gguf -c 8192 -ngl 99 -fa on --jinja --port 8080
```

The same address answers llama-server's own API (`/completion`,
`/tokenize`, `/detokenize`, `/props`, `/slots`, `/health`, `/embedding`),
the OpenAI API under `/v1` and Ollama's under `/api`:

```text
$ curl -s http://127.0.0.1:8080/completion -d '{"prompt": "The capital of France is", "n_predict": 4, "temperature": 0}'
{"index":0,"content":" Paris, and the","tokens":[],"id_slot":0,"stop":true,"model":"LFM3-1.7B-Q4_K_M","tokens_predicted":4,"tokens_evaluated":5,...,"stop_type":"limit",...}
```

If an app starts a binary named `llama-server` itself, copy `kinetic` to
that name instead; it then behaves as `kinetic serve`. `llama-cli` becomes
`kinetic chat`, or `kinetic run` when given a prompt, and
`llama-completion` becomes `kinetic run`:

```sh
cp kinetic llama-server            # Windows: copy kinetic.exe llama-server.exe
```

Flags for what Kinetic does by itself, such as `-fa`, `--jinja` or `-b`,
are accepted and ignored. The few with no equivalent stop with a
line saying what to use; `-hf` points at `kinetic pull`. The full list:
[llama.cpp flags](llama-flags.md). What still differs in the HTTP API is
listed under [llama-server API](server.md#llama-server-api).

## You use llama-cpp-python

```sh
pip install llama-cpp-kinetic
```

`import llama_cpp` then loads Kinetic's version of the `Llama` class, so
your code runs unchanged:

```text
$ cat app.py
from llama_cpp import Llama

llm = Llama(model_path="LFM3-1.7B-Q4_K_M.gguf", n_ctx=4096, n_gpu_layers=0, verbose=False)
out = llm("The capital of France is", max_tokens=4, temperature=0)
print(out["choices"][0]["text"])
$ python app.py
 Paris, and the
```

An installed llama-cpp-python is shadowed, not touched:
`pip uninstall llama-cpp-kinetic` brings it back. The covered API is in
[Python, C and Rust](bindings.md#python).

## You use Ollama

Stop Ollama, then serve the model on Ollama's port:

```sh
kinetic serve qwen3:4b --ollama
```

Open WebUI, Continue and other Ollama clients keep their settings, since
the server answers at `http://127.0.0.1:11434`. `kinetic models` lists the
models Ollama already downloaded, and a name like `qwen3:4b` runs Ollama's
own file.

```text
$ curl -s http://127.0.0.1:11434/api/version
{"version":"0.13.0"}
$ curl -s http://127.0.0.1:11434/api/chat -d '{"model": "LFM3-1.7B-Q4_K_M", "messages": [{"role": "user", "content": "Say hi in two words."}], "stream": false}'
{"model":"LFM3-1.7B-Q4_K_M","created_at":"2026-11-08T12:01:01.544798100Z","message":{"role":"assistant","content":"Hi there! ..."},"done":true,"done_reason":"stop",...}
```

## You link libllama

Not yet: there is no drop-in `libllama` library. Kinetic has its own C API,
[`kinetic.h`](bindings.md#c), which covers loading a model, generating and
embedding, but code written against `llama.h` needs porting to it.
