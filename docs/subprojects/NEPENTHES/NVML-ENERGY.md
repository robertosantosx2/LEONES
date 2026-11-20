# NEPENTHES — NVML sampler y contabilidad energética

## Objetivo

Capturar telemetría GPU de NVIDIA desde NVML con timestamps de pared y monotónicos, identidad estable del dispositivo y una política explícita de energía. El módulo es independiente de AIPerf y se puede probar en CI mediante un proveedor NVML simulado.

## Ejecución

Requiere Python 3 y el driver NVIDIA operativo. Instalar el binding en un entorno aislado:

```bash
python3 -m pip install nvidia-ml-py
```

Ejecutar una captura de 30 segundos a 500 ms:

```bash
python3 scripts/nepenthes_nvml_sampler.py \
  --duration-seconds 30 \
  --interval-ms 500 \
  --output artifacts/nepenthes/nvml-smoke-001.jsonl
```

Produce:
- `nvml-smoke-001.jsonl`: una muestra por GPU y ciclo.
- `nvml_energy_summary.json`: energía por dispositivo, método y calidad.

El directorio de salida debe ser nuevo; no se sobrescriben campañas previas.

## Señales y unidades

| Campo | Unidad | Interpretación |
|---|---|---|
| `power_w` | W | Potencia instantánea |
| `energy_counter_mj` | mJ | Contador acumulado NVML |
| `gpu_utilization_percent` | % | Utilización GPU |
| `memory_utilization_percent` | % | Utilización de ancho de banda de memoria |
| `memory_used_bytes`, `memory_total_bytes` | bytes | Memoria de dispositivo |
| `temperature_c` | °C | Temperatura |
| `graphics_clock_mhz`, `memory_clock_mhz` | MHz | Frecuencias reportadas |

Se conservan UUID, índice, nombre de GPU y PCI bus ID. No se recogen PID ni estadísticas por proceso.

## Política de energía

1. **Preferir contador NVML**: `nvmlDeviceGetTotalEnergyConsumption` devuelve mJ acumulados; el delta entre primera y última muestra se convierte a J.
2. **Fallback trapezoidal**: si el contador no existe o se reinicia, integrar potencia entre muestras consecutivas:
   `E = Σ ((Pᵢ + Pᵢ₊₁) / 2) × Δt`.
3. No integrar intervalos no monótonos, sin potencia o superiores a `--max-gap-seconds`; informar gaps y degradar la calidad.
4. No convertir una estimación incompleta en una medida exacta. El summary distingue `measured_counter`, `estimated`, `partial_estimate` y `unavailable`.

## Energía incremental y tokens/J

La función `derive_energy_efficiency` escala la energía de baseline idle a la duración de la ejecución:

`E_incremental = E_run - E_idle × (T_run / T_idle)`

Solo calcula tokens/J y J/token si:
- ambas ventanas de energía y duración son válidas;
- el incremento es estrictamente positivo;
- el número de tokens de salida es conocido y positivo.

No sustituye el baseline por cero ni clampa incrementos negativos. Si faltan datos, los ratios quedan `null`.

## Límites y atribución

NVML reporta señales de **todo el dispositivo**. En equipos compartidos, no se pueden atribuir al proceso llama.cpp. Las métricas se etiquetan `device_level_not_process_level`. AIPerf también puede emitir `gpu_telemetry_export.jsonl`; no sumar ambas fuentes de energía en una misma campaña. Usar el sampler independiente como fuente canónica o como contraste, registrando la decisión en el manifiesto.

## Validación

`tests/test_nepenthes_nvml_sampler.py` usa un NVML simulado y cubre identidad, potencia, contador acumulado, fallback trapezoidal, gaps, reset de contador, normalización de baseline y tokens/J. No requiere GPU, driver, NVML real ni MSI.
