# Kinetic for Python

Kinetic: open engine for running AI locally. Runs your GGUF models today, and .ktc models verified and tuned for your hardware.

Windows and Linux, x86-64. Everything runs on your computer. Kinetic never connects to the network, except when you run `kinetic pull`.

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

`max_tokens`, `temperature` and `seed` are optional; without them the model file's recommended sampling is used and the answer runs until it ends. Calls release the GIL, so other Python threads keep running while the model works.

## Build from source

```sh
pip install maturin
maturin build --release
pip install target/wheels/kinetic_engine-*.whl
```

Licensed under the Apache License 2.0. Copyright 2026 Velocity.
