# Scripts

## RC1 benchmark boundary

The minimum RC1 path does not use parallel generic runners. Execution must go through the authorized runtime plan and the canonical execution, benchmark and evidence components.

The following remain active, among others:

- `a01_runtime_benchmark.py` — RC1 A01 vertical.
- `runtime_benchmark_v1.py` — shared `runtime-benchmark.v1` contract.
- `runtime_benchmark_evidence.py` — evidence capture/normalization.
- Authorized runtime adapters and runners.

`record_benchmark.py` remains active as recording support used by the current execution. `run_and_record_benchmark.py` has moved to `scripts/deprecated/`; its historical tests remain under `tests/deprecated/`. Do not create new consumers of the deprecated interface.

The historical `leones-*` family is also outside the RC1 core and is retained under `scripts/deprecated/`. It is not part of the canonical selection, execution, measurement or evidence path.

Other old or specialized scripts are retained until a dependency audit demonstrates that they can be migrated. **Do not delete by intuition: deprecate only when a replacement exists, and preserve provenance.**

## NEPENTHES

- `nepenthes.py` — engine-independent capture CLI; creates an evidence package for each run and provides `verify` to validate integrity.
- `install_nepenthes.sh` — user-space installer under `~/.local/bin` (Python 3.10+, no root); also installs the Nsight importer and migration 002 under `~/.local/share/nepenthes`.
- Usage: `nepenthes self-test` validates installation, `nepenthes run -- <engine> <arguments>` captures a run, and `nepenthes verify <RUN_DIR>` checks the package. See the [NEPENTHES CLI contract](../research/moe/tandem.cpp/NEPENTHES-CLI-EN.md) for scope and limitations.
