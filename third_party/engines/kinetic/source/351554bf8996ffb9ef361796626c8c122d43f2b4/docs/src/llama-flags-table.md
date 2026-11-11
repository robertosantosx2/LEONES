| llama.cpp flag | In Kinetic |
|---|---|
| `-sys` | works, as `--system` |
| `--system-prompt` | works, as `--system` |
| `--temperature` | works, as `--temp` |
| `-dev` | works, as `--device` |
| `-np` | works, as `--parallel` |
| `-ctk` | works, as `--cache-type-k` |
| `-ctv` | works, as `--cache-type-v` |
| `-a` | works, as `--alias` |
| `-rea` | works, as `--reasoning` |
| `-ngl`, `--n-gpu-layers` | works: `0` means `--device cpu`, any other number `--device cuda`, `all` as many as fit |
| `-fa`, `--flash-attn`, `--jinja`, `--mmap`, `-cb`, `--cont-batching`, `-nocb`, `--no-cont-batching`, `--no-warmup`, `--metrics`, `--slots`, `--no-webui`, `--embedding`, `--embeddings`, `-no-cnv`, `--no-conversation`, `-st`, `--single-turn`, `-b`, `--batch-size`, `-ub`, `--ubatch-size`, `-tb`, `--threads-batch`, `--cache-reuse`, `--numa`, `--prio`, `--poll`, `-to`, `--timeout`, `--threads-http` | accepted and not needed: Kinetic does this by itself |
| `-sm`, `--split-mode`, `-ts`, `--tensor-split`, `-mg`, `--main-gpu`, `-ot`, `--override-tensor` | Kinetic runs the model wholly on one device; choose it with `--device` |
| `-cnv`, `--conversation`, `-i`, `--interactive`, `--interactive-first` | use `kinetic chat <model>` |
| `--chat-template` | built-in template names are not supported; pass a Jinja file with --chat-template-file |
| `-md`, `--model-draft`, `--draft`, `--draft-max`, `--draft-min`, `-ngld` | speculative decoding is automatic and needs no draft model |
| `-hf`, `--hf-repo`, `-mu`, `--model-url` | download with `kinetic pull <org>/<repo>[:<quant>]`, then run it by name |
| `-f`, `--file` | pipe the prompt in: `kinetic run <model> < prompt.txt` |
| `--image` | send images to the server: `kinetic serve <model> --mmproj <projector>` |
| `--control-vector`, `--control-vector-scaled` | control vectors are not supported yet; LoRA adapters are, with --lora |
| `--grammar`, `--grammar-file`, `-j`, `--json-schema` | constrained output is in the server, through `grammar` and `response_format` |
| `--api-key-file` | pass the key itself with --api-key |
| `--ssl-key-file`, `--ssl-cert-file` | the server speaks plain HTTP; put a TLS proxy in front |
