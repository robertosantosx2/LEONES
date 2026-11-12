# Reproducible engine source snapshots

LEONES stores source code for every benchmarked inference runtime in its own repository. The source snapshot is part of the benchmark evidence: a version string alone is insufficient.

## Layout

```text
third_party/engines/
  <engine-id>/
    SOURCE.json
    source/\n      <commit-sha>/         # immutable complete tracked tree at this commit
      LICENSE / COPYING / NOTICE / ...
```

The source tree is copied into a commit-addressed directory and never overwritten. Updating an engine creates another snapshot and leaves previous source trees intact. The root `SOURCE.json` points to the current snapshot. Each source snapshot is pinned by commit and Git tree SHA. `SOURCE.json` records the upstream URL, requested ref, resolved commit, Git tree SHA, submodule state, Git LFS status and license notice files. The source is not built or executed by the vendoring workflow.

## GitHub-only import

Use Actions → **Vendor inference engine sources** → Run workflow. Supply registry IDs (comma-separated) and, optionally, `id=tag-or-commit` overrides. The workflow:
1. checks out the LEONES benchmark branch;
2. fetches the requested upstream revisions;
3. initializes submodules and Git LFS payloads where available;
4. copies the source tree and provenance metadata;
5. commits the snapshots back to the same LEONES branch.

This avoids requiring a local workstation checkout for source import. The workflow must be run after adding a new engine to the registry.

## Legal and technical preservation

- Keep upstream LICENSE, COPYING, NOTICE, PATENTS, TRADEMARKS and attribution files unchanged.
- Do not claim that Apache-2.0 or another source license grants trademark rights.
- Do not strip build scripts, tests, fixtures, lockfiles, generated source required to build, or model-format definitions.
- Do not include downloaded model weights in the source snapshot. Model files are tracked separately by path, hash, license and provenance.
- For private forks or local patches, register the exact repository and commit. Never substitute a public upstream base and label it as the fork.
- For submodules and Git LFS, verify the snapshot contains the resolved content; incomplete checkouts are a failed vendor operation.

## Benchmark evidence preservation

Each session stores engine source commit/tree, build recipe, binary hash, model/tokenizer/template hashes, effective arguments, redacted environment, logs, full responses, per-request telemetry, and before/during/after machine snapshots. The source snapshot and the run evidence together make the result auditable.
