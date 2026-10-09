# cafe-llama upstream audit — 2026-10-09

## Current upstream baseline

Repository: `Osmantic/ODS`  
Branch: `main`  
Reviewed tree commit: `d48ec9b1261cb2db3801b0cd767c0749b5d8f875`

The recursive tree for current upstream `main` contains no `cafe-llama` service path. The optional extension must therefore be introduced by the final consolidated PR; it must not be assumed to exist in an upstream install.

## Candidate fork commit

The user's fork branch `feat/cafe-llama-runtime-improvements` is reported as one commit ahead of current `main`, at `a2068a4a12a3cf8cdf27ca047cc28bbceb16df30`. Treat it as a source candidate, not production-ready code.

Review of its Dockerfile diff found these gates:
- It invokes `file` to distinguish zip from tar assets but does not install the `file` utility.
- It downloads a runnable executable without a pinned SHA-256 digest or signature verification.
- Its default artifact is Linux x64 CUDA 12.4, not a generic multi-platform binary.
- The build path must fail if the expected executable is absent rather than silently produce an image without a working runtime.

Before accepting that implementation, pin the exact release artifact and digest, verify it during the build, explicitly validate architecture/backend support, and expose a build identity that ODS can verify. A release URL or binary filename is not provenance.

## Activation gate

The ODS host-agent model activation transaction currently stages the standard llama-server through its platform-specific restart path, verifies model identity/completion, then publishes the route. A cafe implementation must add a distinct runtime adapter and service target to the existing transaction; publish a cafe endpoint only after proof succeeds; record `backend.kind=cafe-llama` consistently in the Python state validator and JSON schema; and restore the prior runtime and route on failure.

The default remains `llama-server`. Do not open the consolidated upstream PR until real ODS-native tests prove both the default path is unchanged and explicit cafe activation, route publication, and rollback work.
