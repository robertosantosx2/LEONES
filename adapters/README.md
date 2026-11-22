# LEONES adapters

Optional integrations are thin adapters around the pinned reference subprojects. They must never copy upstream source.

Common lifecycle: `probe -> prepare -> run -> normalize -> cleanup`.

Reference backends:

- `llmfit`: first estimate only.
- `Magnitude`: hardware/model/runtime selection support.
- `ODS`: local inference/server surface.
- `Buddy`: knowledge/context and harness candidate.
- `DeepSeek Harness`: harness candidate.

Each adapter is optional. Absence of an upstream project must not break core LEONES tests.