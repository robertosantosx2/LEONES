# Kinetic upstream snapshot

- Upstream: https://github.com/Veloresearch/kinetic
- Upstream default branch: `main`
- Source license: Apache-2.0 (retain upstream LICENSE and NOTICE files).
- Import method: run `scripts/import_kinetic.sh` from the LEONES repository root.
- Destination: `third_party/kinetic/`
- The import script records the exact upstream commit in `UPSTREAM_COMMIT`.

This directory is intentionally populated by the import script rather than by a partial hand-copy. It copies the complete tracked upstream source tree (excluding its Git metadata) and preserves upstream attribution and license files. Do not present this as an already imported source snapshot until the script has been run and `UPSTREAM_COMMIT` exists.
