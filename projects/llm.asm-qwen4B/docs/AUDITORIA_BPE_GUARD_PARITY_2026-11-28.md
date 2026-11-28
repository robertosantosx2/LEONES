# Auditoría de paridad BPE entre exportador y guards

**Fecha:** 28 de noviembre de 2026  
**Rama:** `research/llm-asm-qwen4b-2026-11-26`  
**Referencia upstream:** `alesha-pro/llm.asm@48feccbfd57cb669440f31ff64958d95bb8b848e`  
**Alcance:** inspección estática del exportador fijado y de los validadores Python/NASM del subproyecto. No se ha modificado upstream ni se ha ejecutado el MSI en esta fase.

## 1. Cómo construye la tabla el exportador

`scripts/export_weights.py::build_tokenizer_blob` recorre `tokenizer.json["model"]["merges"]` mediante `enumerate`. El índice de la iteración se almacena como `rank`; por tanto, el exportador genera ranks consecutivos desde cero y preserva el orden original de merges.

Cada clave se codifica como `(left_id << 32) | right_id`. La tabla usa 524.288 slots, hash Fibonacci y sondeo lineal. El exportador calcula e imprime `max_probe`, pero no establece un límite máximo contractual de sondeos.

La corrección semántica de `left_id`, `right_id` y `merged_id` depende del vocabulario y de la lista original de merges. No puede demostrarse únicamente comprobando que los tres IDs estén dentro del vocabulario.

## 2. Comparación observada

| Invariante | Exportador | Python | NASM |
|---|---|---|---|
| IDs de byte-to-token dentro de vocabulario | Construye desde vocabulario | Sí | Sí |
| IDs byte-to-token distintos | No añade comprobación explícita | Sí | No |
| IDs BPE dentro de vocabulario | Los obtiene del vocabulario | Sí | Sí |
| Rank dentro de rango | Genera por enumeración | Sí | Sí |
| Ranks únicos | Garantizado por enumeración normal | Sí | No |
| Ranks contiguos desde cero | Garantizado por enumeración normal | Sí | No |
| Claves BPE duplicadas | La inserción por clave no se deduplica explícitamente | Sí | Detecta duplicados dentro de la cadena de sondeo |
| Cadena de sondeo sin huecos | Construye mediante sondeo lineal | Sí | Sí |
| Límite de sondeos | Sin límite explícito | 1.024 | 1.024 (alineado en este cambio) |
| Merge semánticamente coherente con tokenizer.json | Fuente original | No | No |

La tabla resume lo que implementa cada pieza, no una garantía de que un checkpoint arbitrario sea válido.

## 3. Hallazgos

### BPE-01 — límites de sondeo incompatibles

Python y NASM aplican ahora el mismo límite de 1.024 posiciones por cadena. El exportador upstream no impone ese límite, por lo que puede producir tablas que ambos guards rechacen. El límite es una política de aceptación de los guards, no una garantía del exportador ni del formato upstream.

El artefacto Qwen3-0.6B ya probado en MSI fue aceptado por ambos guards, pero eso no demuestra que todos los tokenizers de checkpoints futuros respeten el límite de 1.024.

**Acción pendiente:** medir `max_probe` en los tokenizers oficiales soportados y añadir fixtures nativos para una cadena válida superior a 128 (idealmente también próxima al límite de 1.024). Si un tokenizer supera 1.024, el exportador/checker deberá detectarlo y rechazarlo explícitamente antes de publicar el ASMBIN; no se debe elevar el límite sin medir el coste de peor caso.

### BPE-02 — ranks globales incompletos en NASM

Python detecta ranks duplicados y exige que el conjunto sea exactamente `0..N-1`. NASM solo comprueba que cada rank individual sea menor que el vocabulario. Una tabla con ranks duplicados o huecos puede superar la comprobación nativa actual.

**Acción:** añadir pruebas negativas explícitas y diseñar una comprobación nativa de unicidad/continuidad que no modifique la tabla de entrada. No basta con comprobar el rango de cada rank.

### BPE-03 — byte-to-token no inyectivo en NASM

Python exige que los 256 IDs de byte-to-token sean distintos; NASM solo comprueba que cada uno esté dentro del vocabulario.

**Acción:** añadir fixture nativo que duplique un ID y rechazarlo en el guard NASM.

### BPE-04 — semántica del tokenizer no verificable desde ASMBIN aislado

Los guards no reciben el `tokenizer.json` original. Por ello no pueden demostrar que los IDs y resultados de cada merge correspondan al vocabulario original, ni que el orden/rank represente exactamente las reglas de merge del tokenizer de origen.

**Acción:** mantener una verificación de exportación separada que compare el ASMBIN con el tokenizer original antes de publicar el artefacto. Registrar hashes de ambos ficheros y resultados de la comparación.

## 4. Pruebas añadidas

En `tests/test_asmbin_validate.py` se han añadido casos para:

- Rechazar IDs byte-to-token duplicados.
- Rechazar ranks BPE duplicados.
- Rechazar ranks con huecos, aunque cada rank individual esté dentro de rango.

Estos casos fijan el comportamiento Python ya implementado. No deben confundirse con cobertura equivalente del guard NASM: esa paridad sigue pendiente.

## 5. Criterio de salida antes de integrar en model_init

1. Medir `max_probe` en los tokenizers oficiales y validar la política común de 1.024 sondeos; exigir al exportador/checker que rechace tablas que superen ese límite.
2. Añadir fixtures nativos v1/v2 para ranks duplicados, ranks no contiguos, byte IDs duplicados y cadena válida superior a 128 y, preferiblemente, casos cercanos al límite 1.024.
3. Ejecutar los mismos fixtures contra Python y NASM y comparar aceptación/rechazo.
4. Añadir verificación externa de equivalencia entre tokenizer original y tabla exportada.
5. Mantener el guard fuera de `model_init` hasta completar esta paridad y la auditoría de rangos del loader.

## 6. Estado

- La validación Python de unicidad/continuidad de ranks ya existe y queda cubierta por pruebas adicionales.
- El guard NASM continúa siendo una barrera parcial; no se declara paridad completa.
- No se ha modificado el exportador upstream.
- No se ha solicitado ninguna prueba adicional en el MSI.
