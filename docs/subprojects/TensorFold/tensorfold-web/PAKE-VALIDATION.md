# Pake validation record

Status: **not yet executed on the target Ubuntu workstation**.

This file is the evidence log for the first native desktop packaging test. Do not mark a check as passed from a successful build alone.

## Build environment

| Field | Result |
|---|---|
| Date | Pending |
| OS / release | Pending |
| Architecture | Pending |
| Pake CLI version | Pending |
| Node.js version | Pending |
| Rust version | Pending |
| WebKitGTK version | Pending |
| Build command | `./build-pake.sh` |
| Build exit code | Pending |
| Output artifacts | Pending |

## Runtime checks

| Check | Result | Evidence / notes |
|---|---|---|
| Pake window opens | Pending | |
| Local bridge reachable at 127.0.0.1:8787 | Pending | |
| Engine health visible | Pending | |
| Models discovered | Pending | |
| Chat SSE streams progressively | Pending | |
| Native dashboard works with Engine `--dashboard` | Pending | |
| Responsive layout at reduced window size | Pending | |
| Closing Pake does not stop bridge | Pending | |
| Closing Pake does not stop Engine | Pending | |

## Scope and known limits

- Pake packages the frontend in a native WebView; it is not the Engine or bridge installer.
- The Python bridge must be started separately in this first iteration.
- The Engine and model files remain independently installed and managed.
- The first build targets Ubuntu x86_64 DEB and AppImage, retaining a standalone binary.
- Windows and macOS must be built and tested on native runners before claiming support.
- PWA offline support caches only the static shell. No inference, chat, models, statistics or dashboard is available offline.

## Reproduction

Terminal 1:

```bash
./run-tensorfold-web.sh
```

Terminal 2:

```bash
curl -fsS http://127.0.0.1:8787/ >/dev/null
./build-pake.sh
```

Open the generated DEB/AppImage or standalone executable and complete the runtime checklist above.
