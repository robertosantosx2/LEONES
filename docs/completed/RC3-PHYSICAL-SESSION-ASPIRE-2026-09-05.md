# RC3 · Sesión física Aspire A515-55 — 2026-09-05

**Estado:** evidencia parcial **OBSERVED** · RC3 físicamente **NO** declarada validada  
**Host:** Acer Aspire A515-55 · Ubuntu 26.04.1 LTS · x86_64  
**Procedencia:** ejecución real en máquina del operador · logs en `results/physical-rc3-20260905/` (local)

## Regla

ESTIMATED ≠ MEASURED. OBSERVED ≠ VALIDATED. PASS de gate CI ≠ handoff físico.  
Esta nota documenta hechos observados. **No** cierra el gate de validación física final de RC3.

## Hechos observados

### Host

| Campo | Valor observado |
|-------|-----------------|
| Chassis | laptop Acer Aspire A515-55 |
| OS | Ubuntu 26.04.1 LTS · kernel 7.0.0-30-generic |
| CPU | Intel Core i5-1035G1 · 4 núcleos / 8 hilos · x86_64 |
| RAM | ~7,03 GiB total · ~1,0–1,5 GiB disponibles durante la sesión |
| GPU | Intel Iris Plus Graphics G1 (Ice Lake) · driver `i915` · `vram_bytes: null` (iGPU) |

### Sonda LEONES (canónica)

| Artefacto | Resultado |
|-----------|-----------|
| `python3 scripts/hardware_profile.py` | JSON con CPU/RAM/GPU observados |
| `python3 scripts/rc3_hardware_discovery.py` | `schema: hardware-profile.v1` · `source: leones-native-ubuntu` |
| Gate `scripts/rc3_release_gate.py` | **PASS** estático · `physical Ubuntu validation: NOT CLAIMED` |
| `pytest tests/test_rc3*.py` | **29 passed** |

### Ecosistema

| Componente | Resultado |
|------------|-----------|
| Hermes | v0.21.0 · `hermes doctor` operativo |
| OMH | v2.0.0 · doctor **48/48** passing · 0 blocking |
| Boundary OMH | runtime Hermes plugin load **not observed** hasta restart/reload |

### Stacks

| Stack | Resultado |
|-------|-----------|
| Magnitude | CLI 0.0.11 · **service Stopped** · datos en `~/.magnitude` |
| ODS | CLI v2.6.0 · stack Docker **Up** · `llama-server` healthy en `127.0.0.1:11435` |
| ODS modelo | tier **T0** · `qwen3.5-2b` · artefacto `Qwen3.5-2B-Q4_K_M.gguf` |
| ODS health/models | `{"status":"ok"}` · modelo listado |
| ODS chat smoke | **timeout 30s** · 0 bytes en cliente |
| llama-server logs | inferencia CPU ~**1,1 tok/s** · una petición corta completó ~23s (HTTP 200); otra **cancelada** por timeout del cliente |

### Avisos del propio ODS (no inventados)

- RAM 7GB below T1 recommendation (16GB)
- CPU fallback selected
- Langfuse / model-router: health débil o no responding en el momento de la captura

## Qué NO se afirma

- [ ] Handoff formal Hermes → Magnitude validado por LEONES
- [ ] Handoff formal Hermes → ODS validado por LEONES
- [ ] Consentimiento + preparación bajo flujo RC3 orquestado
- [ ] Benchmark de tareas LEONES
- [ ] Evidencia **MEASURED** con procedencia LEONES
- [ ] RC3 físicamente validada de punta a punta

## Lectura pedagógica

1. La sonda canónica funciona en este Ubuntu y produce `hardware-profile.v1` sin inventar VRAM.
2. Hermes/OMH están instalados y pasan `doctor`; eso no sustituye la sonda ni autoriza medición.
3. ODS está operativo a nivel de servicios y lista un modelo T0 coherente con 7 GiB.
4. La inferencia en CPU es usable pero lenta; el timeout del cliente ODS puede fallar aunque el servidor genere tokens.
5. Magnitude está instalado pero inactivo: no competir con ODS en 7 GiB sin plan explícito.
6. Cerrar RC3 físico exige handoffs + medición bajo autoridad LEONES, no solo `doctor` y `ods status`.

## Procedencia

- Contrato: `docs/RC3-ARCHITECTURE.md`
- STRICT previo: `docs/completed/RC3-STRICT-2026-09-05.md`
- Gate: `scripts/rc3_release_gate.py`
- Fecha de sesión: 2026-09-05
