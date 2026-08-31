# RC2-B — ODS Physical Installation Block

**Date:** 2026-08-31  
**Status:** BLOCKED — external connectivity  
**Component:** ODS official installer

## Physical preflight

- Ubuntu physical host: PASS
- CPU / memory / GPU detection: PASS
- Docker available: PASS
- LLMFit available: PASS
- Git working tree: CLEAN

## Installation flow

The RC2 installation flow:

1. requests explicit installation consent;
2. downloads the official ODS installer;
3. displays download activity;
4. refuses to execute an incomplete installer;
5. reports the installation failure.

## Connectivity evidence

DNS resolution for `install.osmantic.com` succeeds.

IPv4 addresses returned:

- `188.114.97.5`
- `188.114.96.5`

Direct HTTPS connection to both endpoints times out.

Control tests succeeded:

- `https://1.1.1.1` → HTTP 301
- `https://github.com` → HTTP 200

Therefore this is not a general HTTPS connectivity failure on the host.

## Result

ODS was **not installed**.

The failure occurs before installer execution and is external to the LEONES installer flow.

No incomplete or unverified installer was executed.

## RC2 decision

This evidence does **not** promote RC2-B to VALIDATED.

RC2-B remains **BLOCKED pending successful access to the official ODS installer endpoint**.

LEONES must not create or substitute a parallel ODS installer to bypass this gate.
