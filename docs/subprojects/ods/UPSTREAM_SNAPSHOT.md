# ODS upstream snapshot

## Canonical source

- Repository: `Osmantic/ODS`
- Upstream branch at audit time: `main`
- LEONES pinned commit: `5a4450765976e2ad2792b9ac8927f4873dac60f6`
- Advertised license: Apache 2.0
- Stable release advertised at the snapshot: `v2.6.0`
- Product/runtime directory: `ods/`

## Snapshot rule

The ODS source used by LEONES is a Git submodule pinned to an immutable upstream commit. Updating ODS requires an explicit SHA change, an upstream diff audit and a fresh CI run.

## Integrity rule

The submodule is kept identical to upstream. LEONES must not edit files inside `subprojects/ODS` to repair upstream behavior.

If LEONES discovers a reproducible upstream problem, the normal path is:

```text
pinned ODS
   |
   v
reproduce + document
   |
   v
report upstream
   |
   +--> upstream fix/merge
   |
   v
update LEONES SHA
```

A temporary LEONES-side adapter/workaround, when unavoidable, must remain outside the submodule and be clearly identified as such.

## Historical local tree

A separate Debian checkout previously inspected under `docs/subprojects/ods/upstream` contained a Python package named `opendeepsearch`. That tree is not the canonical `Osmantic/ODS` source and is not included in this snapshot.

It must not be used to infer ODS APIs, dependencies or defects.

## Validation boundary

GitHub CI validates the reproducible upstream snapshot and integration boundary first. Debian is subsequently used for hardware-specific measurements such as CPU, RAM, disk, GPU and local model performance.
