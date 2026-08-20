# Contrato de datos de instalaciones ODS/Magnitude

El registro de una instalación debe distinguir claramente entre lo que LEONES observa, lo que el producto declara y lo que LEONES mide.

## Campos comunes

| Campo | Tipo | Regla |
|---|---|---|
| `installation_id` | string | identificador local, no contiene PII |
| `profile` | enum | `ods-server` o `magnitude-assistant` |
| `observed_at` | datetime | hora de captura |
| `os` | string | distribución y versión cuando sea posible |
| `kernel` | string | opcional |
| `cpu` | string | observado localmente |
| `ram_gb` | number | observado localmente |
| `gpu` | string | `unknown` si no se puede observar |
| `vram_gb` | number/null | `unknown` cuando no se puede determinar |
| `storage_free_gb` | number | espacio libre observado |
| `product_version` | string | versión/ref realmente instalada |
| `model` | string | modelo realmente configurado, no una recomendación hipotética |
| `model_source` | string | Hugging Face, archivo local u origen declarado |
| `quantization` | string/null | solo si está declarada/observada |
| `runtime` | string | backend realmente usado |
| `services` | array | servicios activos cuando el producto los expone |
| `evidence_status` | enum | `estimated`, `reported`, `measured`, `verified` |
| `consent` | boolean | necesario antes de publicar/cargar evidencia |

## Rendimiento

Nunca sobrescribir una estimación con una medición.

```json
{
  "metric": "tokens_per_second",
  "value": 0,
  "unit": "tok/s",
  "evidence_status": "measured",
  "measurement_method": "leones-benchmark",
  "hardware_profile": "captured-local",
  "source": "local-run"
}
```

Las recomendaciones del producto se almacenan como `reported` o `estimated` según su origen. Solo el benchmark LEONES puede generar un resultado `measured` de LEONES.

## Privacidad

No se almacenan por defecto:

- nombres de usuario;
- rutas personales completas;
- contenido de conversaciones;
- claves/API tokens;
- nombres de proyectos privados;
- prompts o archivos usados durante una sesión.

La instalación tampoco envía automáticamente estos datos a Atlas.
