# ODS integration status

**Status:** upstream provenance corrected; integration boundary under validation.

## Done

- Identified the canonical upstream as `Osmantic/ODS`.
- Pinned the LEONES submodule to `5a4450765976e2ad2792b9ac8927f4873dac60f6`.
- Confirmed that the official ODS tree is the Osmantic local-AI server stack, with its runtime under `ods/`.
- Corrected the earlier audit that had accidentally inspected a different/historical `sentient-agi/OpenDeepSearch` Python tree.
- Established the rule that the ODS submodule remains identical to upstream.
- Established the GitHub-CI-before-Debian validation boundary.
- Defined an upstream-reporting path for genuine ODS defects.

## Remaining

- Validate the pinned ODS snapshot with a lightweight upstream smoke gate.
- Keep CI independent of Docker, GPU and local model availability for the baseline contract.
- Review ODS release/support evidence and record any reproducible findings.
- Prepare a concise upstream improvement report rather than modifying the ODS submodule.
- After software CI is green, run hardware-specific validation on Debian.

## Provenance rule

The local Debian `opendeepsearch` checkout is not the ODS reference and must not be copied into LEONES. A finding is an ODS finding only when it is reproduced against the pinned `Osmantic/ODS` tree.
