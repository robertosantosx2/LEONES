# RC2-B — Magnitude Hardware Block

**Status:** BLOCKED — no locally executable model on the validation host

## Host

- Machine: Aspire A515-55
- CPU: Intel Core i5-1035G1
- Logical cores: 8
- RAM: 7.0 GiB
- Available RAM during validation: ~1.1 GiB
- Accelerator: Intel UHD Graphics (ICL GT1), Vulkan, system memory
- Magnitude CLI: 0.0.8

## Result

Magnitude hardware detection and the model catalog work correctly.

Bonsai 8B Q1 is installed, but Magnitude reports `DoesNotFit` / `insufficient_resources`:

- required: 8,938,643,264 bytes
- capacity: 7,549,534,208 bytes
- deficit: 3,536,592,704 bytes

Smaller candidates were then tested through the setup/residency path. They also failed with explicit `LowMemory` errors:

- Gemma 4 E2B Q4: required 5,032,641,548 bytes + 1,073,741,824-byte system reserve; short by 5,047,063,565 bytes.
- LFM2.5 2.6B Q4: required 4,087,026,712 bytes + 1,073,741,824-byte system reserve; short by 3,984,897,049 bytes.
- LFM2.5 2.6B Q5: required 4,352,316,440 bytes + 1,073,741,824-byte system reserve; short by 4,619,949,081 bytes.

No installed model reached locally executable residency. The failure is physical memory pressure, not a download or CLI failure.

## Installer observability

The LEONES Magnitude installer was hardened to show periodic activity while `npm install -g @magnitudedev/cli` is running, so a slow installation is visibly active rather than appearing hung. This is locked in commit `f7bb924`.

## Decision

RC2-B is **not promoted to VALIDATED** on this host.

No model will be installed blindly or forced beyond Magnitude's hardware gate.

The current 7 GiB host is retained as a valid negative hardware-gate test case. The next positive physical validation requires a host with substantially more available system memory.
