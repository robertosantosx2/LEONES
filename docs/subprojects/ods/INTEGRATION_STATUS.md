# ODS integration status

**Status:** audit/cleanup in progress; not yet production-ready.

## Done

- Identified the upstream repository and audited the `main` tree at commit `ec7aa06dc5ead71821a3d92ea56e54a8a9d16ece`.
- Recorded packaging, import, ranking, context-building, and source-processor defects.
- Correctly identified the ranking API (`BaseSemanticSearcher`, `InfinitySemanticSearcher`, `JinaReranker`).
- Established CPU/GPU dependency separation as an integration requirement.
- Established the CI-versus-Debian validation split.

## Remaining

- Bring the upstream snapshot into the LEONES repository as an identifiable subproject revision.
- Apply source fixes on top of the snapshot rather than modifying an untracked local clone.
- Add deterministic contract tests.
- Add ODS-specific CI.
- Re-run CI and review the resulting failures.
- Only then run hardware-specific validation on Debian.

## Important provenance rule

Do not claim an ODS fix is integrated into LEONES merely because it exists in a developer's local clone. The fix is integrated only after it is represented by a Git commit in the LEONES repository and covered by the appropriate CI gate.
