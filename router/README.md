# Router — preselección y decisión de modelos

## Flujo

```text
hardware + intención
        ↓
llmfit (estimación inicial)
        ↓
Atlas / identidad / evidencia
        ↓
JGB + licencia + self-hostability
        ↓
CABE / RULA + mediciones
        ↓
Router LEONES
        ↓
modelo/runtime recomendado
```

`llmfit_adapter.py` solo normaliza la salida externa. No calcula un `fit_score` LEONES y no transforma estimaciones en mediciones.

## Contrato de entrada del adaptador

Se aceptan respuestas con candidatos bajo `models`, `candidates` o `results`. Los campos se conservan con nombres `llmfit_*` cuando representan valores externos.

## Contrato de salida

Cada candidato contiene como mínimo `model`, `source="llmfit"` y los campos disponibles. `attach_provenance()` añade `llmfit_source_version` y `estimate_status="estimated"`.

## Regla de degradación

El Router debe poder funcionar sin llmfit. Si no está instalado, no responde o devuelve un catálogo incompatible, se continúa con la matriz de hardware y las fuentes internas de LEONES. La ausencia de llmfit nunca debe impedir la ejecución del sistema.

## Validación

```bash
python -m unittest router/llmfit_adapter_test.py -v
```
