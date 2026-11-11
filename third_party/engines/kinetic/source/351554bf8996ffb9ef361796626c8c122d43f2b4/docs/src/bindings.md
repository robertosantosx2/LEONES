# Python, C and Rust

Besides the command line and the server, Kinetic is a library. All three
interfaces load the same `.gguf` and `.ktc` files, use the model file's
recommended sampling by default and give the same exactness guarantees. A
text model runs on the GPU when the build has CUDA and the model fits,
otherwise on the CPU, as `--device auto` does.

## Python

```sh
pip install kinetic-engine
```

```python
import kinetic

model = kinetic.Model("SmolLM2-135M-Instruct-f16.gguf")

# Chat through the model's own template.
print(model.chat([{"role": "user", "content": "Name three rivers."}], max_tokens=64))

# Stream the answer as it is written.
for piece in model.chat([{"role": "user", "content": "Tell me a story."}], stream=True):
    print(piece, end="", flush=True)

# Continue a raw prompt; temperature 0 always takes the likeliest token.
print(model.generate("The capital of France is", max_tokens=8, temperature=0))

# Sampled output repeats for the same seed.
print(model.generate("Once upon a time", max_tokens=32, temperature=0.8, seed=42))

# Embedding models turn texts into vectors.
embedder = kinetic.Model("bge-small-en-v1.5-f16.gguf")
vectors = embedder.embed(["a cat", "a dog"])
```

| | |
|---|---|
| `kinetic.Model(path)` | loads a model; raises `RuntimeError` when the file cannot be loaded |
| `model.name` | the file name without its extension |
| `model.chat(messages, max_tokens=None, temperature=None, seed=None, stream=False)` | answers a list of `{"role": ..., "content": ...}` dicts; returns the text, or an iterator of pieces with `stream=True` |
| `model.generate(prompt, max_tokens=None, temperature=None, seed=None, stream=False)` | continues `prompt` exactly as written, without the chat template |
| `model.embed(texts)` | one vector (a list of floats) per text, from an embedding model |
| `kinetic.__version__` | the version, such as `"0.1.0"` |

Without `max_tokens` an answer runs until it ends or fills the context.
Calls release the GIL, so other Python threads keep running while the model
works; requests from several threads take turns on one model. Dropping a
stream stops its generation.

The published wheels run on the CPU. For the GPU, build the package from
source with the CUDA toolkit installed (see
[Building from source](building.md#the-libraries)), or run `kinetic serve` and
use the `openai` package against it, which also gives you tools, JSON
output and images.

`kinetic.llama_cpp` offers the commonly used part of `llama-cpp-python`'s
`Llama` class. `pip install llama-cpp-kinetic` makes `import llama_cpp` load
it, so code written for llama-cpp-python runs unchanged; an installed
llama-cpp-python is shadowed, not touched, and comes back when you uninstall
`llama-cpp-kinetic`. Or change one import:

```python
from kinetic.llama_cpp import Llama   # was: from llama_cpp import Llama

llm = Llama(model_path="model.gguf", n_ctx=4096, n_gpu_layers=-1, seed=42)
out = llm("Q: Name the planets. A:", max_tokens=64, stop=["Q:"])
for chunk in llm.create_chat_completion(messages=[{"role": "user", "content": "Hi"}], stream=True):
    print(chunk["choices"][0]["delta"].get("content", ""), end="")
```

It covers `__call__`/`create_completion`, `create_chat_completion` (with
`stream`), `embed`, `create_embedding`, `tokenize`, `detokenize`, `n_ctx`,
`token_bos` and `token_eos`, with the same response shapes and defaults.
`n_gpu_layers=0` runs on the CPU and any other value on the GPU when the
model fits. Grammars, tools, `response_format` and logprobs raise
`NotImplementedError` rather than being ignored.

## C

The release archives carry `include/kinetic.h` and the library:
`lib/kinetic_capi.dll` with its import library `kinetic_capi.dll.lib` on
Windows, `lib/libkinetic_capi.so` on Linux. To build it yourself:
`cargo build --release -p kinetic-capi`.

This program, [`examples/chat.c`](https://github.com/Veloresearch/kinetic/blob/main/crates/kinetic-capi/examples/chat.c),
asks one question and streams the answer:

```c
#include <stdio.h>

#include "kinetic.h"

static bool print_text(const char *text, size_t len, void *user_data) {
    (void)user_data;
    fwrite(text, 1, len, stdout);
    fflush(stdout);
    return true;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s MODEL PROMPT\n", argv[0]);
        return 2;
    }
    kinetic_model *model = kinetic_model_load(argv[1]);
    if (!model) {
        fprintf(stderr, "kinetic: %s\n", kinetic_last_error());
        return 1;
    }
    kinetic_session *session = kinetic_session_new(model, NULL);
    if (!session) {
        fprintf(stderr, "kinetic: %s\n", kinetic_last_error());
        kinetic_model_free(model);
        return 1;
    }
    kinetic_params params = kinetic_params_default();
    params.max_tokens = 128;
    int64_t tokens = kinetic_session_generate(session, argv[2], &params, print_text, NULL);
    if (tokens < 0) {
        fprintf(stderr, "kinetic: %s\n", kinetic_last_error());
    } else {
        fprintf(stderr, "\n[%lld tokens, kinetic %s]\n", (long long)tokens, kinetic_version());
    }
    kinetic_session_free(session);
    kinetic_model_free(model);
    return tokens < 0;
}
```

Build and run it:

```sh
# Linux
gcc -std=c99 -I include examples/chat.c -L lib -lkinetic_capi -o chat
LD_LIBRARY_PATH=lib ./chat model.gguf "Name three rivers."
```

```bat
:: Windows, in a Visual Studio developer prompt
cl /I include examples\chat.c lib\kinetic_capi.dll.lib
copy lib\kinetic_capi.dll .
chat.exe model.gguf "Name three rivers."
```

The API in brief; [`kinetic.h`](https://github.com/Veloresearch/kinetic/blob/main/crates/kinetic-capi/include/kinetic.h)
documents every function:

| Function | Does |
|---|---|
| `kinetic_model_load(path)` | loads a model; `NULL` on failure |
| `kinetic_session_new(model, system)` | starts a conversation with an optional system prompt |
| `kinetic_session_generate(session, message, params, on_text, user_data)` | adds a user message, streams the answer to `on_text` (return `false` to stop) and adds it to the conversation; returns the number of tokens, or -1 |
| `kinetic_params_default()` | no token limit, the model's temperature, no seed |
| `kinetic_embedding_size(model)`, `kinetic_embed(model, text, out)` | vectors from an embedding model |
| `kinetic_last_error()` | why the last failing call on this thread failed |
| `kinetic_session_free`, `kinetic_model_free` | free them; a model is freed once its sessions are |

Strings are UTF-8. A model may be shared between threads, whose requests
take turns on it; a session belongs to one thread at a time. Each turn of a
session reuses the work of the previous ones.

## Rust

Add the [`kinetic`](https://github.com/Veloresearch/kinetic/tree/main/crates/kinetic)
crate from the repository:

```toml
[dependencies]
kinetic = { git = "https://github.com/Veloresearch/kinetic" }
```

```rust
fn main() -> Result<(), kinetic::Error> {
    let model = kinetic::Model::open("model.gguf")?;
    let request = model.request();
    let messages = [kinetic::Message::new("user", "Name three rivers.")];
    let answer = model.chat(&messages, &request, &mut |text| {
        print!("{text}");
        true
    })?;
    println!("\n{} tokens", answer.completion_tokens);
    Ok(())
}
```

`model.request()` starts from the file's recommended sampling; change its
`sampling` (temperature, top-k, top-p, seed and the rest) and `max_tokens`
fields before passing it. `generate` continues a raw prompt and `embed`
returns vectors from an embedding model. The `cuda` feature is on by
default; `default-features = false` builds a CPU-only library.

The crates below `kinetic` (`kinetic-models`, `kinetic-server` and the
others) are the engine itself. Their APIs are public so that the tools in
this repository can use them, but they change between releases.
