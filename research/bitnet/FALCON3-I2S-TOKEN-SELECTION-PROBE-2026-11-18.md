# Falcon3 I2_S sampled-token probe

Date: 2026-11-18

## Purpose

Capture the actual token IDs selected by `llama-completion` instead of inferring generation behavior from redirected stdout. The existing scalar runtime is intentionally slow, and previous runs were interrupted before completion; their `Interrupted by user` marker is a signal-handler message, not model output.

## Provenance

- BitNet: `0b341e582afbf9e1011f24744b554c96a3477eb5`
- llama.cpp submodule: `390c307752ab78fd8189f359d6954c9ba1be74af`
- Runtime configuration: `GGML_NATIVE=OFF`, optional x86 SIMD disabled, `GGML_LLAMAFILE=OFF`
- Base research branch: `research/falcon3-i2s-tokenizer-probe-2026-11-18`

## Instrumentation

The GitHub Actions workflow applies a temporary source transformation to
`tools/completion/completion.cpp` in its ephemeral checkout. Immediately after
sampling and accepting a generated token, the executable emits up to 16
`I2S_TOKEN_PROBE` records containing:

- generation index;
- selected token ID;
- whether the selected token is EOG;
- exact token-piece bytes encoded as hexadecimal.

This instrumentation does not alter sampling, logits, token acceptance, model
weights, GGUF metadata, or the local checkout. Hex output preserves whitespace
and non-printable bytes without relying on terminal rendering.

## Run procedure

Download the `falcon3-i2s-token-selection-probe-runtime` artifact from the
workflow run. Extract it, set `LD_LIBRARY_PATH` to the extracted directory,
and run the command in its `README.txt` with the existing local Falcon3 GGUF.
Allow the command to finish; do not interrupt it. Inspect
`I2S_TOKEN_PROBE` records in `token-diagnostics.log`, not the stdout file.

## Interpretation

- IDs whose `piece_hex` decodes to spaces, tabs, or line feeds indicate the
  model actually selected whitespace tokens.
- An EOG record identifies a selected end-of-generation token.
- Ordinary printable UTF-8 bytes indicate lexical output even if stdout
  rendering or buffering obscures it.
- A coherent token sequence would shift investigation toward display/stop
  handling; repeated whitespace or control IDs would keep attention on model
  logits, conversion, and I2_S arithmetic.

The probe is diagnostic only. It does not establish the cause of the model's
poor output until the artifact has been run and its records inspected.
