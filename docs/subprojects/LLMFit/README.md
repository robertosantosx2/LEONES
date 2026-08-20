# LEONES LLMFit subproject

This directory is a Git submodule pinned to the upstream LLMFit repository.

- Upstream: https://github.com/AlexsJones/llmfit
- Pinned revision: `70fea7d2eb42d887700cb5d146879f463f37fc98`
- Role in LEONES: hardware-aware first-pass model selection and estimation.

## Integration boundary

LEONES does not fork or modify the upstream implementation here. The integration lives in LEONES adapters and contracts; this submodule provides the reproducible upstream source tree used by development, inspection and local validation.

```text
LEONES
  └── subprojects/LLMFit  (git submodule)
          ↓
     llmfit CLI / JSON / API / MCP
          ↓
     LEONES adapter
          ↓
     Atlas + evidence + measured performance
```

## Updating the pin

Update the submodule only after the LEONES adapter contract, offline tests and relevant smoke tests pass. Record the upstream revision in the corresponding integration documentation.
