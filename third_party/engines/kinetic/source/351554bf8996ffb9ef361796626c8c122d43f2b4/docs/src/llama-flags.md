# llama.cpp flags

If you use llama.cpp, most of your commands work as they are. These flags
mean the same in Kinetic:

`-m`, `-p`, `-n`, `-c`, `-t`, `-s`, `--temp`, `--top-k`, `--top-p`,
`--min-p`, `--repeat-penalty`, `--host`, `--port` and `--mmproj`.

```sh
llama-cli    -m model.gguf -p "Hello" -n 64 --temp 0 -ngl 99
kinetic run  -m model.gguf -p "Hello" -n 64 --temp 0 -ngl 99

llama-server -m model.gguf -c 8192 --port 8080 -ngl 99
kinetic serve -m model.gguf -c 8192 --port 8080 -ngl 99
```

The commands differ: `llama-cli` is `kinetic run` (one prompt) or `kinetic
chat` (a conversation), `llama-server` is `kinetic serve` and `llama-bench`
is `kinetic bench`.

A copy of `kinetic` named `llama-server`, `llama-cli` or `llama-completion`
runs as `kinetic serve`, `kinetic chat` (or `kinetic run` with a prompt) and
`kinetic run`, for apps that start those binaries by name.

For every other llama.cpp flag below, Kinetic takes it under its own name,
accepts it when it asks for something Kinetic does by itself, or stops with
a line that says what to use instead, rather than a bare "unexpected
argument":

```text
$ kinetic run model.gguf -ts 1,1 "Hello"
kinetic: -ts is a llama.cpp flag: Kinetic runs the model wholly on one device; choose it with --device.
```

<!-- The table is generated from crates/kinetic-cli/src/llama_flags.rs by
     scripts/llama_flags_doc.py; edit the source, not the table. -->

{{#include llama-flags-table.md}}

The flags for prompt files, constrained output and adapters are on the
[roadmap](roadmap.md).
