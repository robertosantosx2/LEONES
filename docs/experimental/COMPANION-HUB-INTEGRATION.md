# Experimental Companion Hub integration

This branch experiments with Companion Hub as an external local-app runtime that LEONES can discover, provision, and evaluate.

## Upstream

- Repository: https://github.com/companionintelligence/companion-hub
- Upstream branch: `dev`
- Pinned upstream commit: `8362f02bcf662bffbc89a0c84d3ac2a7008dfb4a`
- Local path: `experimental/companion-hub`

## Integration boundary

LEONES remains the authority for hardware discovery and provenance, estimated model/runtime selection, explicit user choice and consent, and physical verification plus measured benchmark evidence.

Companion Hub is treated as an experimental runtime/app orchestration component. Its catalog metadata or recommendations are not LEONES measurements.

## Initial hook

The Companion Hub source is tracked as a Git submodule so the integration remains isolated from the LEONES core and can be updated/pinned independently.

After cloning LEONES:

```bash
git checkout Experimental
git submodule update --init --recursive
```

The submodule should be evaluated against the current LEONES hardware profile before any installation or runtime decision is presented as a LEONES recommendation.

## Upstream runtime notes

Companion Hub documents Docker Compose as a prerequisite and supports Linux desktop/server operation. Its headless server dashboard uses port 5002.

Source: Companion Hub README and installation documentation.
