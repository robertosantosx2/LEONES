# CanIRun.ai — integración LEONES v1

CanIRun.ai entra en LEONES como **estimador externo de compatibilidad**, no como benchmark.

## Upstream

- Web: https://www.canirun.ai/
- Repositorio: https://github.com/midudev/canirun.ai
- API: `POST /api/compatibility` y `POST /api/recommend`

La API pública acepta un perfil `hardware` con `ramGb` y, opcionalmente, CPU y GPU con `name`, `vramGb` y `memoryBandwidthGbps`. La compatibilidad devuelve `status`, `grade`, `score`, cuantización y un bloque `estimated` con tokens/s, memoria y headroom.

## Contrato LEONES

`router/canirun_adapter.py` normaliza esas respuestas a `CanIRunCandidate` y conserva:

- `source = canirun`
- `estimate_status = estimated`
- `estimated_tps`
- `estimated_memory_gb`
- `memory_headroom_gb`
- `grade` y `score` como señales pertenecientes a CanIRun
- `measured_tps = null`
- `measurement_status = not-measured`

No se transforma la nota S–F en un score LEONES.

## Seguridad semántica

El adaptador no puede:

1. escribir `measured_tps`;
2. declarar `verified` por compatibilidad externa;
3. modificar CABE/RULA;
4. autorizar ejecución directamente;
5. sustituir `runtime-selection.v1`.

La autorización sigue siendo posterior a selección, evidencia, runtime y benchmark.

## Flujo

```text
hardware profile
      │
      ├── LLMFit
      └── CanIRun.ai
             │
             ↓
       external candidates
             ↓
       Atlas / evidence
             ↓
       runtime-selection.v1
             ↓
          executor
             ↓
          grader
             ↓
       measured result
```

## Tests

`tests/test_canirun_adapter.py` cubre:

- normalización de `/api/compatibility`;
- normalización de `/api/recommend`;
- separación estimate/measured;
- construcción del perfil hardware con el shape público de CanIRun.

El fixture `tests/fixtures/canirun/compatibility-llama3.1-8b-q4km.json` fija una respuesta representativa para evitar depender de la API durante los contract-tests.

## Criterio de integración

La integración se considera correcta cuando la API puede fallar, cambiar o quedar indisponible sin romper la semántica del selector: CanIRun aporta una **hipótesis estimada**, y LEONES continúa pudiendo seleccionar y medir por sus propios contratos.
