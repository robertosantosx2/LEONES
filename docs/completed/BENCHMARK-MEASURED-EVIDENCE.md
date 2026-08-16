# Benchmarks medidos — evidencia empírica

## Estado

**🟢 Infraestructura terminada.**

> Esto no significa que LEONES ya disponga de una cobertura amplia de mediciones sobre hardware físico. Significa que el circuito técnico para recoger, validar, clasificar y publicar una medición real está implementado.

## Qué resuelve

El circuito evita mezclar tres cosas diferentes:

1. una **estimación** de rendimiento;
2. una **medición real** obtenida al ejecutar un modelo;
3. una **clasificación derivada** como CABE o RULA.

El valor `tokens_per_second` se conserva siempre como dato original. La etiqueta de rendimiento se añade como información derivada.

## Flujo completo

```text
ADAPTADOR DE RUNTIME
        ↓
EJECUCIÓN REAL
        ↓
run_and_record_benchmark.py
        ↓
record_benchmark.py
        ↓
CABE / RULA
        ↓
validate_measured_benchmark.py
        ↓
promote_measured_benchmark.py
        ↓
publish_measured_benchmark.py
        ↓
EVIDENCIA JSONL
        ↓
ATLAS / MATRIZ / RECOMENDADOR
```

## Componentes

### `scripts/record_benchmark.py`

Valida el registro mínimo de una medición y fuerza `measurement_type = measured`. No ejecuta modelos.

### `scripts/run_and_record_benchmark.py`

Ejecuta el comando proporcionado por un adaptador de runtime, busca `tok/s` en su salida y pasa el resultado al contrato común. No utiliza un shell para ejecutar el comando principal.

### `scripts/runtimes/llama_cpp_adapter.py`

Primer adaptador de runtime. Construye los argumentos de `llama.cpp` y proporciona el patrón para localizar `tok/s`.

### `scripts/classify_performance.py`

Aplica la clasificación oficial:

```text
<1       → NO_CABE
1–<10    → CABE
10–100   → RULA
>100     → RULA+
```

Los límites son parte del contrato y están cubiertos por tests.

### `scripts/enrich_measured_performance.py`

Solo acepta registros marcados como `measured` y añade la clasificación sin modificar el valor observado.

### `scripts/validate_measured_benchmark.py`

Es la barrera de promoción. Exige identidad mínima del modelo, hardware y runtime y bloquea estimaciones o datos incompletos.

### `scripts/promote_measured_benchmark.py`

Encadena validación y enriquecimiento y produce un registro listo para publicar.

### `scripts/publish_measured_benchmark.py`

Escribe la evidencia validada como JSONL. No borra observaciones anteriores y no modifica directamente el catálogo canónico.

## Atlas

`scripts/atlas_measured_performance.py` integra únicamente mediciones compatibles con una fila Atlas. La coincidencia exige hardware y runtime y usa `model_id` cuando está disponible.

Una ausencia de medición **no se convierte en una estimación**.

## Tests

El circuito dispone de pruebas unitarias y de integración para:

- contrato de medición;
- runner;
- adaptador llama.cpp;
- integración runner → contrato;
- límites CABE/RULA;
- rechazo de estimaciones;
- validación de identidad;
- promoción;
- publicación;
- integración con Atlas.

Las pruebas de integración que usan una salida simulada sirven para comprobar el cableado del software. **No son benchmarks de rendimiento y no deben contabilizarse como evidencia física.**

## Qué queda fuera del cierre

Todavía hace falta ejecutar el circuito sobre hardware físico representativo y obtener mediciones reproducibles para ampliar la cobertura empírica de LEONES.

Por tanto:

```text
INFRAESTRUCTURA DE MEDICIÓN       🟢
COBERTURA EMPÍRICA REAL           🟡
```

## Regla de no concurrencia

El workflow de benchmark medido está sujeto al grupo global de escritores de LEONES. Los futuros workflows que escriban en `main` deben respetar igualmente `leones-main-writers` y `cancel-in-progress: false`.

## Regla de evidencia

Nunca introducir en Atlas un valor estimado bajo la etiqueta `measured`. Si no existe ejecución real, el dato debe seguir siendo `estimated` o quedar ausente.

## Mantenimiento

Cuando esta infraestructura se modifique, deben actualizarse los tests y este documento. Una ampliación de runtimes debe aportar su adaptador y sus pruebas antes de considerarse operativa.
