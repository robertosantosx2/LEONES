# Magnitude 0.2.9 on Ubuntu: health endpoint reports Intel/Vulkan while inference uses NVIDIA/CUDA

**Report type:** Reproducible diagnostic report and proposed upstream fix  
**Prepared in:** [robertosantosx2/LEONES](https://github.com/robertosantosx2/LEONES)  
**Affected application:** Magnitude Desktop / `magnitude-service` 0.2.9 (revision 59)  
**Platform:** Ubuntu Linux, x86-64  
**Status:** Reproduced locally; root cause in the installed binary is not yet proven; fix proposal needs maintainer review.

## 1. Executive summary

On a Linux laptop with an Intel integrated GPU and an NVIDIA RTX 3050 Laptop GPU, Magnitude's inference engine demonstrably uses the NVIDIA GPU through CUDA. However, the local service's `GET /health` response reports the Intel integrated GPU and the Vulkan backend as the hardware in use.

Three independent observations establish that this is a reporting inconsistency, not evidence that CUDA inference is failing:

1. `~/.magnitude/logs/inference.log` repeatedly records the NVIDIA GeForce RTX 3050 Laptop GPU and `backend="cuda"`.
2. The same log records the model becoming ready on that CUDA device.
3. `nvidia-smi` reports the running `magnitude-inference` process using 1,423 MiB of NVIDIA GPU memory during the observation.

By contrast, `http://127.0.0.1:10100/health` reports `backend: "vulkan"` and `gpuName: "Intel(R) Graphics (ADL GT2)"`.

**Requested maintainer action:** trace how the service builds the health hardware summary and ensure it describes the actual selected/loaded inference device (or explicitly distinguishes the host's available devices from the active inference device). Add a hybrid Intel+iGPU / NVIDIA+dGPU regression test.

This report does not claim the precise root cause is proven. The available evidence narrows the problem to a mismatch between the inference engine's active-device record and the hardware summary exposed by the service.

## 2. Test machine

| Property | Observed value |
|---|---|
| OS | Ubuntu Linux (native Linux installation) |
| CPU | 12th Gen Intel(R) Core(TM) i7-12650H |
| CPU topology | 10 physical cores reported by Magnitude; 16 logical processors |
| System memory | Approximately 14 GiB usable; API reports 15,914,074,112 bytes |
| Integrated GPU | Intel(R) Graphics (ADL GT2) |
| Discrete GPU | NVIDIA GeForce RTX 3050 Laptop GPU |
| NVIDIA VRAM | 4 GiB |
| NVIDIA driver / CUDA reported by host | NVIDIA driver 580.178.04; CUDA 13.0 |
| Vulkan enumeration | Intel, NVIDIA, and llvmpipe are present |
| Magnitude Desktop | 0.2.9 |
| Service revision | 59 |
| Model used in the inference test | `minicpm5-1b:gguf:q4` |
| Service port | 10100 on loopback for the health request |

The machine has both Intel integrated graphics and NVIDIA discrete graphics. The fact that multiple Vulkan devices are enumerated is relevant, but by itself does not establish why the health summary selects Intel.

## 3. Exact health endpoint result

Command:

```bash
curl -s http://127.0.0.1:10100/health | python3 -c 'import json,sys; d=json.load(sys.stdin); print(json.dumps({"version":d.get("version"),"hardware":d.get("state",{}).get("hardware")},indent=2))'
```

Observed output:

```json
{
  "version": "0.2.9",
  "hardware": {
    "backend": "vulkan",
    "gpuName": "Intel(R) Graphics (ADL GT2)",
    "gpuKind": "integrated",
    "gpuMemoryBytes": 15914074112,
    "gpuCount": 2,
    "cpuModel": "12th Gen Intel(R) Core(TM) i7-12650H",
    "cpuCores": 10,
    "memoryBytes": 15914074112
  }
}
```

The health summary reports 15,914,074,112 bytes as both `gpuMemoryBytes` and `memoryBytes`. This strongly suggests that the displayed Intel device's memory figure is associated with system/unified memory rather than 4 GiB of dedicated NVIDIA VRAM. That interpretation should be verified against the health schema and runtime memory-domain semantics; the report does not assume that the field is necessarily intended to mean dedicated VRAM.

The `gpuCount: 2` value is consistent with the two physical GPUs relevant to this report, although the Vulkan loader also exposes llvmpipe as a software device. The exact counting/deduplication semantics should be confirmed by maintainers.

## 4. Evidence that inference uses NVIDIA CUDA

### 4.1 Inference assessment log

Command:

```bash
grep -iE 'assessment environment established|model ready|gpuName|gpuMemoryBytes' ~/.magnitude/logs/inference.log | tail -5
```

Observed output:

```text
2026-10-15T19:53:29.670494Z  INFO tokio-rt-worker magnitude_service_server::assessment::environment: assessment environment established device=cuda:ac6951ca-4c9e-5d78-d295-8b6e23d03178 device.name=NVIDIA GeForce RTX 3050 Laptop GPU backend="cuda" bandwidth.bytes_per_second=176032000000 bandwidth.source="reported"
2026-10-16T20:30:46.294944Z  INFO tokio-rt-worker magnitude_service_server::assessment::environment: assessment environment established device=cuda:ac6951ca-4c9e-5d78-d295-8b6e23d03178 device.name=NVIDIA GeForce RTX 3050 Laptop GPU backend="cuda" bandwidth.bytes_per_second=176032000000 bandwidth.source="reported"
2026-10-16T20:45:12.281874Z  INFO tokio-rt-worker magnitude_service_server::residency::controller: model ready device=cuda:ac6951ca-4c9e-5d78-d295-8b6e23d03178
2026-10-16T21:00:31.949500Z  INFO tokio-rt-worker magnitude_service_server::assessment::environment: assessment environment established device=cuda:ac6951ca-4c9e-5d78-d295-8b6e23d03178 device.name=NVIDIA GeForce RTX 3050 Laptop GPU backend="cuda" bandwidth.bytes_per_second=176032000000 bandwidth.source="reported"
2026-10-16T21:03:34.942063Z  INFO tokio-rt-worker magnitude_service_server::residency::controller: model ready device=cuda:ac6951ca-4c9e-5d78-d295-8b6e23d03178
```

The same CUDA device identifier is reported across assessment and model residency events. These are runtime log records, not an inference drawn from the health response.

### 4.2 NVIDIA process memory

Command:

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

Observed output:

```text
pid, process_name, used_gpu_memory [MiB]
390616, /home/ssantos/.magnitude/releases/artifacts/0.2.9/linux-x64-gnu/icn-base-linux-x64-gnu/4371067faa367264e55fab68e7e010d294c71c5b33988a231ccd42c797343953/bin/magnitude-inference, 1423 MiB
```

This confirms that the Magnitude inference process had 1,423 MiB of NVIDIA GPU memory allocated at the time of the check. A previous live observation during inference also showed approximately 91–98% NVIDIA GPU utilization, with around 1.4 GiB used; utilization fell after inference ended.

### 4.3 Process serving `/health`

Commands:

```bash
readlink -f /proc/388905/exe
tr '\0' ' ' </proc/388905/cmdline; echo
```

Observed output:

```text
/usr/lib/magnitude-desktop/resources/magnitude-service
/usr/lib/magnitude-desktop/resources/magnitude-service serve --data-dir /home/ssantos/.magnitude --port 10100
```

The health endpoint is served by the installed `magnitude-service` process, not by the `magnitude-inference` executable directly. The inference engine is a separate process. This makes the service's health-summary construction and its data source a key area to inspect.

## 5. Relevant log context

The service log records startup and model-store initialization, but no explicit GPU selection in the inspected lines:

```text
[2026-10-16T21:00:29.844Z] magnitude-service started (pid 388905)
[23:00:30.581] INFO (#12): Network access resolved
  bind: 0.0.0.0
  requireApiKey: false
[23:00:30.672] INFO (#62): Model store resolved
  root: /home/ssantos/.magnitude/models
  source: Default
```

The inference log, in contrast, explicitly records CUDA device assessment and model readiness. A search for the health field names under `~/.magnitude` found them only in `~/.magnitude/logs/inference.log`; the service log did not explain the mismatch.

## 6. Reproduction procedure

The issue can be checked without modifying application files or configuration:

1. Start Magnitude Desktop normally on a machine with Intel integrated graphics and NVIDIA discrete graphics.
2. Run a local inference request using a supported model, such as the tested `minicpm5-1b:gguf:q4`.
3. Inspect `~/.magnitude/logs/inference.log` for `assessment environment established` and `model ready`.
4. During or immediately after inference, run:
   ```bash
   nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
   ```
5. Query:
   ```bash
   curl -s http://127.0.0.1:10100/health
   ```
6. Compare the device/backend reported by the inference log and NVIDIA process accounting with the hardware summary returned by `/health`.

**Observed result on the reported machine:** inference log and NVIDIA accounting identify NVIDIA/CUDA, while `/health` identifies Intel/Vulkan.

**Expected result:** the health API should clearly and accurately report the active inference device/backend. If it is designed to report a different concept (for example, a default device or the host's preferred device), that distinction should be explicit in the schema and documentation, rather than presented as though it were the active inference device.

## 7. Related upstream reports and source leads

These upstream reports are relevant context, but are not identical reproductions of this Ubuntu health-endpoint issue:

- [Magnitude issue #154 — 0.2.3 selects the AMD iGPU as primary device on hybrid machines; dGPU VRAM excluded from model fit](https://github.com/magnitudedev/magnitude/issues/154). This reports a Windows hybrid AMD iGPU + NVIDIA RTX 5070 system where the integrated GPU became the primary reported device after an upgrade. It describes incorrect memory/fit consequences and points to GPU-view deduplication changes as a possible regression window. That issue's OS, GPUs, CLI reporting path, and version differ from this case.
- [Magnitude issue #141 — Dual GPU configuration report](https://github.com/magnitudedev/magnitude/issues/141). Reports duplicate GPU listings and incomplete multi-GPU use.
- [Magnitude issue #151 — Vulkan iGPU auto-selected on an iGPU-only system](https://github.com/magnitudedev/magnitude/issues/151). Reports automatic selection problems and limited ability to choose a device.

A source file worth reviewing in the current upstream tree is:

- [`packages/acn-protocol/src/schemas/inference-projection.ts`](https://github.com/magnitudedev/magnitude/blob/main/packages/acn-protocol/src/schemas/inference-projection.ts)

The current implementation includes `summarizeInferenceHardware(loaded, hardware)`. It derives a backend from the loaded startup backend when available, otherwise falls back to a usable device after sorting device views by reported memory, then selects a device by matching backend. This is a plausible source-level area to investigate: backend equality alone may be insufficient to identify a physical device when one GPU is exposed through multiple backends or when the service's `loaded` state and hardware snapshot have different scopes.

**Important limitation:** the inspected source was from the current upstream branch, not verified as byte-for-byte equivalent to the installed 0.2.9 service. The code path responsible for the installed health response has not yet been proven, and the source hypothesis must be validated against the 0.2.9 tag/commit and the service's actual call path.

## 8. Proposed solution

### 8.1 Separate active inference device from host inventory

The health model should distinguish at least these concepts:

- **Available hardware:** all discovered accelerators and their memory domains.
- **Active inference device:** the exact device identifier selected by the inference runtime, when one is loaded.
- **Active backend:** the backend used by that device for the current runtime/model.
- **Selection state/reason:** active, available but not selected, unavailable, or not yet known.

If backward compatibility prevents changing the current fields, keep them stable and add explicit fields or a versioned representation. Document whether the existing `hardware` object means host default, available inventory, or active inference device.

### 8.2 Use stable device identity, not backend alone

Where the API intends to report the active inference device, derive the device name, kind and memory domain from the actual selected device ID/UUID returned by the engine. Do not infer physical identity by choosing the first/largest device whose backend equals `cuda` or `vulkan`.

Where a device appears through both CUDA and Vulkan, deduplicate the two views only when there is evidence that they represent the same physical device (for example, a stable UUID or backend-provided physical identity). Never merge distinct GPUs merely because they share a backend or similar names.

If the service currently has only the backend but not the active device identifier, expose that missing identity from the engine/service boundary rather than guessing. When the active device is unknown, report it as unknown and preserve the complete available-device inventory.

### 8.3 Keep memory domains semantically correct

Do not label system RAM as dedicated GPU VRAM. Report separately:

- Dedicated device-local memory/VRAM capacity.
- Unified/shared memory capacity where applicable.
- System physical memory.
- Current free/available memory, if reliably measured.
- The provenance and semantics of each value.

On an integrated GPU, shared system memory may be relevant to inference capacity, but it must not be presented as dedicated VRAM. On a discrete NVIDIA GPU, use the appropriate CUDA device's memory-domain data for that CUDA device.

### 8.4 Add regression tests

Add deterministic unit tests around the health projection and hardware summary using a synthetic hybrid topology:

1. Intel integrated GPU available through Vulkan.
2. NVIDIA discrete GPU available through CUDA and Vulkan, with both views mapped to the same physical identity.
3. An active loaded CUDA device whose identity is the NVIDIA GPU.
4. Different memory capacities for system RAM and NVIDIA VRAM.

Assertions:

- Active backend is CUDA and active GPU name is NVIDIA RTX 3050 when the loaded device ID is the NVIDIA CUDA device.
- Intel remains in the available inventory but is not reported as the active inference GPU.
- CUDA and Vulkan views of the same NVIDIA card count as one physical GPU.
- Intel and NVIDIA remain distinct physical GPUs.
- System RAM is not exposed as NVIDIA dedicated VRAM.
- If there is no loaded device, the response does not silently imply that the largest or first backend-matching device is active.
- Tests cover no-device, CPU-only, iGPU-only, dGPU-only, and hybrid configurations.

Add an integration test that compares the service health summary with the selected-device identifier reported by the inference runtime after a model becomes ready.

### 8.5 Make the health contract unambiguous

Suggested conceptual response shape (illustrative only; not a claim about the current API contract):

```json
{
  "hardware": {
    "activeInferenceDevice": {
      "id": "cuda:<stable-device-id>",
      "name": "NVIDIA GeForce RTX 3050 Laptop GPU",
      "backend": "cuda"
    },
    "availableDevices": [
      {
        "name": "Intel(R) Graphics (ADL GT2)",
        "backend": "vulkan",
        "kind": "integrated"
      },
      {
        "name": "NVIDIA GeForce RTX 3050 Laptop GPU",
        "backend": "cuda",
        "kind": "discrete"
      }
    ]
  }
}
```

The precise field names and backward-compatibility approach are for maintainers to decide. The important requirement is that an active-device field must come from the runtime's actual device identity, not a heuristic based only on backend.

## 9. Acceptance criteria

The issue should be considered fixed when:

- [ ] On a hybrid Intel + NVIDIA Linux host, inference logs identify the NVIDIA CUDA device and the health endpoint reports that same active device while the model is loaded.
- [ ] The integrated Intel GPU remains visible as available hardware but is not mislabeled as the active CUDA inference device.
- [ ] Dedicated GPU memory and system/shared memory are represented distinctly and correctly.
- [ ] Multiple backend views of one physical GPU are deduplicated without merging separate physical GPUs.
- [ ] Tests cover hybrid topology and verify active device identity, backend, and memory semantics.
- [ ] Existing CPU-only, integrated-only, and single-discrete-GPU behavior remains correct.
- [ ] The API documentation specifies what the hardware summary represents when no model is loaded.

## 10. Safety and scope

No configuration files were changed, no Vulkan ICD was disabled, no backend was forced, and no application was reinstalled during this investigation. CUDA inference already works on the test machine. The proposed change should fix reporting and identity consistency without introducing a workaround that hides devices or changes the user's runtime selection.

## 11. Request to maintainers

Could the Magnitude maintainers please:

1. Confirm whether the 0.2.9 health response is intended to represent the active inference device or a separate host-level/default hardware assessment.
2. Trace the source and call path used to populate `state.hardware` in `GET /health`.
3. Compare the installed 0.2.9 path with the current implementation of `summarizeInferenceHardware` and the device catalog/identity changes around the 0.2.x releases.
4. Confirm or reject the device-identity hypothesis and advise whether this belongs with the existing dual-GPU/hardware-reporting issues or warrants a separate issue.
5. Review the proposed regression tests and the separation of active device from available hardware.

The report is intentionally evidence-led: CUDA use is confirmed; the exact cause of the health-summary mismatch remains to be established by source tracing and maintainer review.
