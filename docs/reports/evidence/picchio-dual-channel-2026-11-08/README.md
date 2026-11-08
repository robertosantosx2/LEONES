# Picchio dual-channel benchmark evidence — 2026-11-08

This evidence set was supplied as `picchio-dual-channel-evidence-20261108.tar.gz` and inspected in the ChatGPT session.

## Archive verification

- Archive size: 13 KiB (compressed).
- Archive SHA-256: `123f70148c8f8d05066b75aaabb46925f683e3af6bd3d498e58e3cb1de599244`
- Gzip integrity: passed.
- Members:
  - `results/dual-channel/run1-4threads.log` — 6,110 bytes
  - `results/dual-channel/run1-8threads.log` — 6,110 bytes
  - `results/dual-channel/run2-8threads.log` — 6,110 bytes
  - `results/dual-channel/run2-4threads.log` — 6,110 bytes
  - `results/dual-channel/picchio_usage.baseline` — 24,592 bytes (binary)

## Baseline integrity

SHA-256 of the baseline contained in the archive:
`ae2ae0bc78853f3c0d9847f187a310c67660c4ea8de7970de779cc7963902efe`

This matches the checksum previously recorded for the restored model hot-store at `$MODEL/.picchio_usage`.

## Raw observations confirmed from the logs

| Run | Threads | Timestamp (+01:00) | Total | MoE | Attention | LM head | Disk I/O |
|---|---:|---|---:|---:|---:|---:|---:|
| run1 | 4 | 01:28:43 | 100.9 s | 70.52 s | 24.66 s | 3.28 s | 39.09 s |
| run1 | 8 | 01:30:34 | 105.3 s | 74.53 s | 25.75 s | 2.83 s | 40.75 s |
| run2 | 8 | 01:32:29 | 108.7 s | 76.93 s | 26.73 s | 2.87 s | 42.08 s |
| run2 | 4 | 01:34:26 | 109.0 s | 75.17 s | 28.75 s | 2.86 s | 42.09 s |

All four logs report seed 12345, 128 output tokens, 1,182,336 hot-store routings, 41,453/52,300 cache hits (79.3%), and 10,847 disk reads. The second 8-thread run records a pre-run CPU package temperature of 96 °C; this is an important confounder.

## Important limitation

The uploaded archive was validated, but this manifest is not a substitute for the original binary archive or the four full logs. Keep the original `picchio-dual-channel-evidence-20261108.tar.gz` with the experiment artifacts. The archive's exact bytes are identified by the SHA-256 above.
