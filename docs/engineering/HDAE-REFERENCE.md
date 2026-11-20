# HDAE reference snapshot for LEONES

**Purpose:** stable, auditable reference for HDAE methodology and Agent Skills.

## Canonical references

- Upstream project: https://github.com/gmkurtzer/hdae
- LEONES-owned fork: https://github.com/robertosantosx2/hdae
- Pinned snapshot: https://github.com/robertosantosx2/hdae/tree/12d1a3389e74642dddee47a6cc4cb217f55f1144
- Pinned commit: `12d1a3389e74642dddee47a6cc4cb217f55f1144`
- Default branch at fork verification: `main`
- License: Apache-2.0 (retain upstream notices and license).

## Rules for agents

1. Consult this pinned snapshot first whenever interpreting or applying HDAE.
2. Do not treat the fork's moving `main` branch as the immutable reference. Use the pinned commit permalink above for normative consultation.
3. The upstream repository is the origin and a source for proposed future updates, not an automatically authoritative replacement for the pinned snapshot.
4. Do not sync, rebase, reset, or advance the pin automatically. A human-approved, reviewable LEONES PR must record the proposed new upstream/fork commit, compare changes, inspect skill behavior and license notices, update this file and the root discovery instructions, and document the decision.
5. The LEONES-specific `HDAE-DIRECTIVE.md` and each project's master INDEX remain authoritative for LEONES governance, priorities and acceptance. Upstream HDAE is the methodology reference; it does not override human decisions, safety constraints, architecture or project INDEXes.
6. A fork is a stable point of reference, not an assurance that upstream will never change or that all skills have been installed in every agent environment.

## Snapshot verification

The fork API identified `robertosantosx2/hdae` as a public GitHub fork whose parent/source is `gmkurtzer/hdae`. The `main` ref resolved to the pinned commit above when this reference was prepared.

