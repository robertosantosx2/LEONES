# RC2-B — Magnitude Hardware Block

**Status:** BLOCKED — no locally executable model

## Result

Magnitude CLI 0.0.8 installed successfully.

Physical hardware detection succeeds.

Bonsai 8B Q1 is installed, but Magnitude reports:

- `DoesNotFit`
- `insufficient_resources`
- required: 8,938,643,264 bytes
- available capacity: 7,549,534,208 bytes
- deficit: 3,536,592,704 bytes

No installed model is reported as locally `Available`.

## Decision

RC2-B is not promoted to VALIDATED.

No model will be installed blindly or forced beyond Magnitude's hardware gate.
