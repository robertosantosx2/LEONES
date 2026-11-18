# Falcon3-10B-Instruct-1.58bit I2_S — cierre fallido de la campaña E2E

**Fecha de cierre:** 2026-11-18  
**Proyecto:** LEONES / BitNet  
**Estado final:** **FAILED — no se obtuvo inferencia semánticamente válida.**  
**Alcance:** investigación archivada; no se ha identificado ni corregido la causa raíz E2E.

## 1. Veredicto

La campaña termina como fallida desde el objetivo operativo: ejecutar Falcon3-10B-Instruct-1.58bit cuantizado a I2_S y obtener respuestas coherentes en el runtime CPU de BitNet/llama.cpp.

Se reprodujo una selección patológica de tokens en el runtime escalar no-AVX2: los 16 pasos seleccionaron el ID 38, cuyo texto exacto es `>>POS_12<<`. El token tiene `attr=8`, `control=1` y `eog=0`. La salida stdout fueron únicamente dos bytes LF (`0a 0a`). Esto confirma que el modelo/runtime seleccionó repetidamente un token de control posicional, no que fallara su renderizado.

**No se ha demostrado la causa raíz.** En particular, el defecto aritmético sintético del vec-dot AVX2 existe, pero las sondas no lo conectaron causalmente con el fallo E2E de Falcon3.

## 2. Evidencia final del probe de selección

Runtime: `falcon3-i2s-token-selection-probe-runtime`, workflow run [#44407617465](https://github.com/robertosantosx2/LEONES/actions/runs/44407617465), commit LEONES `95964ad2a33a98a99cf08758553b80a3a68ec0a0`.

Artefacto:
- ID: `14475082673`
- SHA-256 ZIP comunicado por CI: `32dd7a0fe5300319bbfffd9df48967ae06a58c5d78e4dcf1a52c958d30aa0382`
- Runtime descargado por el usuario: `~/falcon3-i2s-token-selection-probe-44407617465/runtime`
- llama.cpp: `390c307752ab78fd8189f359d6954c9ba1be74af`
- Compilación escalar: `GGML_NATIVE=OFF`; AVX/SSE/FMA/BMI2 OFF; LLAMAFILE OFF.

Resultado medido (16/16):
```
id=38 attr=8 control=1 eog=0
raw_hex=3e3e504f535f31323c3c
piece_hex=3e3e504f535f31323c3c
```
Los campos raw y piece coinciden y decodifican como `>>POS_12<<`. No es EOS. La instrumentación inicial que usaba `common_token_to_piece(..., false)` ocultaba deliberadamente tokens CONTROL/UNKNOWN; la instrumentación corregida lee `llama_vocab_get_text()` y representa el token con `special=true`. La sonda corregida eliminó ese falso vacío de diagnóstico.

Ejecución: prompt `<|user|>\n¿Qué es Falcon3?\n<|assistant|>\n`, `-n 16 -c 256 -no-cnv --ignore-eos --temp 0 --seed 42`. stdout: `0a 0a`. Tiempo de generación: 15 runs en ~31,9 s, aproximadamente 0,47 tok/s en el equipo de validación.

## 3. Matriz de resultados de la campaña

| Experimento | Configuración / resultado | Conclusión |
|---|---|---|
| Inferencias iniciales | Varias rutas CLI, salida incoherente | Fallo E2E reproducido |
| `llama-completion` | Evita el parser de conversación; salida incoherente | PEG no explica el fallo |
| BOS desactivado | Sin mejora | BOS no es explicación suficiente |
| Tokenizer probe | LF=12, TAB=13; prompt tokeniza de forma estable | No se encontró fallo básico de tokenización |
| Token-selection probe inicial | 16/16 ID 38, piece vacío por usar `special=false` | Instrumentación insuficiente; no interpretar como token vacío |
| Token-selection probe corregido | 16/16 ID 38 = `>>POS_12<<`, control=1, EOG=0 | Selección repetida de token de control confirmada |
| Runtime no-AVX2 con completion | Salida whitespace / EOS en ejecuciones previas | Desactivar SIMD no resuelve el síntoma |
| Runtime AVX2 fallback | 64 llamadas I2_S; K=3072, activaciones min=-127 max=88; máximo lane=452; cero overflow observado | No se observó overflow en esas llamadas |
| Runtime LLAMAFILE | 128 registros LLAMAFILE; ruta tinyBLAS activa | La inferencia probada pasó por LLAMAFILE, no por vec-dot |
| Probe de logits | No realizado | No se sabe si ID 38 domina los logits o interviene el sampler |

## 4. Hallazgo AVX2: válido, pero no causalmente atribuido

Se mantiene el hallazgo aritmético sintético documentado en [FALCON3-10B-I2_S-AVX2-OVERFLOW-INVESTIGATION-2026-11-18.md](FALCON3-10B-I2_S-AVX2-OVERFLOW-INVESTIGATION-2026-11-18.md): `ggml_vec_dot_i2_i8_s_1x1()` acumula en lanes int16 y puede desbordar para entradas I8_S válidas.

El harness sintético K=3072 reproduce overflow para +127 uniforme y para 90% +127 / 10% -127; los controles alternos y +64 coinciden. Sin embargo:
- La ruta LLAMAFILE observada intercepta I2_S y evita ese vec-dot.
- En la prueba AVX2 fallback real, ninguna de las primeras 64 llamadas registradas mostró overflow; máximo absoluto por lane 452.
- No se dispone de comparación E2E de la misma inferencia con una corrección escalar/SIMD diferencial.

Por tanto, el defecto del vec-dot queda como **defecto independiente confirmado para entradas sintéticas**, no como causa demostrada de la generación fallida.

## 5. Tokenizador y metadatos

Datos registrados:
- Vocabulario GGUF: 131072; tokenizer GPT-2 con pretokenizer Falcon3.
- EOS ID 11; PAD ID 2023; LF ID 12; TAB ID 13.
- El GGUF no declara explícitamente BOS; llama.cpp infiere BOS=11 en esta revisión. La configuración HF también registra BOS/EOS ID 11 en generation config.
- Desactivar BOS no corrigió el síntoma.
- El aviso `model vocab missing newline token` se observó, pero `llama-tokenize` sí produjo LF [12] y TAB [13]. No se ha demostrado causalidad del warning.

## 6. Procedencia de runtimes y artefactos

Todos los runtimes se compilaron en GitHub Actions y se descargaron para validación local. No se modificó el GGUF original ni el checkout original por esta campaña.

| Runtime | Run | Artefacto / ID |
|---|---:|---|
| LLAMAFILE diagnostics | [44298433322](https://github.com/robertosantosx2/LEONES/actions/runs/44298433322) | `falcon3-i2s-llamafile-diag-runtime` / `14423909257` |
| AVX2 fallback diagnostics | [44303652672](https://github.com/robertosantosx2/LEONES/actions/runs/44303652672) | `falcon3-i2s-avx2-fallback-runtime` / `14426624455` |
| Non-AVX2 control | [44347302916](https://github.com/robertosantosx2/LEONES/actions/runs/44347302916) | `falcon3-i2s-nonavx2-control-runtime` / `14445744473` |
| Non-AVX2 + llama-completion | [44350530227](https://github.com/robertosantosx2/LEONES/actions/runs/44350530227) | `falcon3-i2s-nonavx2-control-runtime` / `14448057862` |
| Tokenizer probe | [44396625961](https://github.com/robertosantosx2/LEONES/actions/runs/44396625961) | `falcon3-i2s-tokenizer-probe-runtime` / `14469977141` |
| Token selection probe v1 | [44402117521](https://github.com/robertosantosx2/LEONES/actions/runs/44402117521) | `falcon3-i2s-token-selection-probe-runtime` / `14472806832` |
| Token selection probe corregido | [44407617465](https://github.com/robertosantosx2/LEONES/actions/runs/44407617465) | `falcon3-i2s-token-selection-probe-runtime` / `14475082673` |

Los artefactos de Actions tienen retención limitada; los run IDs y los commits son las referencias permanentes de procedencia. Los archivos grandes del modelo permanecen fuera de LEONES.

## 7. Estado de hipótesis

| Hipótesis | Estado |
|---|---|
| Overflow del vec-dot AVX2 para todas las entradas válidas | **Confirmado como defecto sintético** |
| Ese overflow causa la salida incoherente de Falcon3 | **No demostrado; evidencia E2E insuficiente** |
| LLAMAFILE tinyBLAS es la ruta de la inferencia instrumentada | **Confirmado para esa ejecución** |
| Overflow en las activaciones reales capturadas por vec-dot | **No observado en 64 llamadas** |
| Token ID 38 representa texto normal | **Falso: es `>>POS_12<<`, token CONTROL** |
| Error de renderizado causa piece vacío | **Falso para el probe corregido; el probe inicial tenía un parámetro inadecuado** |
| Tokenizador LF/TAB está ausente | **No confirmado; tokenize devuelve IDs 12 y 13** |
| Causa raíz del token 38 repetido | **Desconocida** |

## 8. Motivo de cierre y trabajo futuro

La campaña se marca **FAILED** porque no alcanzó el criterio de aceptación: una respuesta semánticamente válida de Falcon3. Se cierra como investigación fallida/no resuelta, no como prueba de que el modelo sea irrecuperable ni como confirmación de una causa específica.

No se debe reabrir la hipótesis AVX2 como explicación E2E sin evidencia nueva. Si se retoma, el siguiente experimento técnicamente discriminante sería instrumentar los logits previos al sampler (top-20, logit/rango de ID 38 y EOS ID 11) y contrastar una ruta de logits independiente. Esa prueba no forma parte de esta campaña y queda fuera del alcance cerrado.

## 9. Referencias de investigación

- [Issue LEONES #157](https://github.com/robertosantosx2/LEONES/issues/157)
- [Informe AVX2 original](FALCON3-10B-I2_S-AVX2-OVERFLOW-INVESTIGATION-2026-11-18.md)
- [Sonda de activaciones AVX2](AVX2-ACTIVATION-PROBE.md)
- [Rama de token selection probe](https://github.com/robertosantosx2/LEONES/tree/research/falcon3-i2s-token-selection-probe-2026-11-18)

---
**Estado final: FAILED / ARCHIVED / ROOT CAUSE UNKNOWN.**
