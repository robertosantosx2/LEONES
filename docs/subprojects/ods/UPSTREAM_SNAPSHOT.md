# ODS upstream snapshot

## Source

- Repository: `sentient-agi/OpenDeepSearch`
- Branch: `main`
- Audited commit: `ec7aa06dc5ead71821a3d92ea56e54a8a9d16ece`
- License: MIT
- Minimum Python: 3.10

## Snapshot rule

The ODS source used by LEONES must be traceable to an immutable upstream commit. A future update must change the recorded commit explicitly and re-run the ODS audit/CI gates.

## Current integration boundary

The LEONES GitHub branch contains the audit and integration policy, while the complete upstream source snapshot is still pending publication in the LEONES repository. Until that happens, local files under a developer checkout must be treated as a working copy, not as the canonical LEONES integration.

## Required next commit

Publish the upstream tree under the established ODS subproject path and then apply LEONES-specific fixes as separate commits. Do not silently mix an upstream refresh with unrelated LEONES changes.
