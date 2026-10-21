# Magnitude 0.2.10 + Qwen3.5-4B — cierre de prueba (2026-10-21)

## Decisión

**Prueba cerrada sin inferencia completada.** Magnitude queda fuera de la tabla de rendimiento medida para Qwen3.5-4B en esta sesión. No se asignan valores de prefill, generación, TTFT, latencia ni VRAM porque no hubo una petición de inferencia satisfactoria.

## Entorno observado

- Sistema: Ubuntu nativo.
- CPU: Intel Core i7-12650H, 16 CPU lógicas.
- RAM: 14,8 GB.
- GPU: NVIDIA GeForce RTX 3050 Laptop, 3,7 GiB de VRAM reportados por Magnitude.
- Magnitude CLI: `0.2.10`.
- `magnitude update check` / `magnitude update status`: Magnitude se declara actualizada.
- Servicio: `Runtime Ready`, dirección local `http://127.0.0.1:10100`, modelo activo `None`.
- En la medición de `magnitude hardware`: 9,3/14,8 GB RAM usados y 5,5 GB libres. Esto es una observación del momento, no prueba de la causa del fallo.

## Artefactos descargados e integridad

Repositorio de pesos: `unsloth/Qwen3.5-4B-MTP-GGUF`, revisión `86835bf9949e4d14d6860f7910b1340ad4f271a9`.

| Archivo | Tamaño | SHA-256 | Verificación |
|---|---:|---|---|
| `Qwen3.5-4B-UD-Q4_K_XL.gguf` | 2.990.664.000 bytes | `d2bfbee4de17c74e6308a4dc750be4c2271f92ae2df1e28f5c5afa0dcdb6fccc` | Coincide |
| `mmproj-BF16.gguf` | 675.569.216 bytes | `169ee40fb1e234ff38b2d814eb8633611a54b6f941f11b700d96dec02cb44ddf` | Coincide |

Total registrado: 3.666.233.216 bytes. Los snapshots contienen enlaces simbólicos válidos a los blobs. La integridad se comprobó con `stat` y `sha256sum`. El artefacto principal es **Q4_K_XL**, no el GGUF **Q4_K_M** utilizado en las pruebas de llama.cpp; no son cuantizaciones idénticas.

También se descargó el artefacto de dependencia DFlash:
- Repositorio: `magnitudedev/Qwen3.5-4B-DFlash-GGUF`
- Revisión: `0094e74a88676605d53b79c7c3d26096335c9746`
- Archivo: `Qwen3.5-4B-DFlash-Q8_0.gguf`
- Tamaño: 685.134.176 bytes.
- No se necesitó para una inferencia porque no se llegó a activar el modelo.

## Evidencias del catálogo y del estado

### Inventario

`/var/lib/magnitude/cache/indexes/inventory.json` contiene el registro:

- ID interno: `mdl_d548e185b006408807ee3d7a7face22441bca84cdb61a5eecd3e1f00db0a6f5d`
- Nombre: `Qwen3.5-4B`
- Disponibilidad: `available`
- Ubicación: `magnitude_cache`
- Arquitectura: `qwen35`
- Cuantización declarada: `Q4_K - Medium`
- Parámetros: 4.326.350.848
- Operaciones declaradas: `load`, `unload`, `delete`

El registro interno no implica que la CLI pueda cargar el modelo; eso no se logró demostrar.

### Afiliaciones

`/var/lib/magnitude/models/catalog-affiliations.json` contiene `qwen3.5-4b`:
- Variante `gguf:q4`, repositorio objetivo `unsloth/Qwen3.5-4B-MTP-GGUF`.
- Dependencia `magnitudedev/Qwen3.5-4B-DFlash-GGUF`.
- También aparecen asociaciones de la dependencia para variantes `gguf:q5`, `gguf:q6` y `gguf:q8`.

### Catálogo publicado

`magnitude catalog status`: evaluación completa, 73/73 modelos evaluados.

`magnitude catalog list` solo muestra tres modelos compatibles:
- Gemma 4 E2B (Q4 QAT): `gemma-4-e2b-it-qat:gguf:q4`
- MiniCPM5 1B (Q4): `minicpm5-1b:gguf:q4`
- MiniCPM5 1B (Q8): `minicpm5-1b:gguf:q8`

Qwen no aparece en la lista.

## Intentos y resultado

| Comando/acción | Resultado |
|---|---|
| `magnitude catalog show qwen3.5-4b` | `Invalid catalog model ID` |
| `magnitude catalog show 'qwen3.5-4b:gguf:q4'` | `Unknown catalog model` |
| `magnitude models load 'hf:unsloth/Qwen3.5-4B-MTP-GGUF/Qwen3.5-4B-UD-Q4_K_XL.gguf'` | `Invalid catalog model ID` |
| `magnitude models status` | `No local models are on this computer` |
| `magnitude models status <ID interno>` | `Invalid catalog model ID` |
| `magnitude models status 'Qwen3.5-4B'` | `Invalid catalog model ID` |
| `magnitude status` | Servicio listo, modelo activo `None` |

El estado `/var/lib/magnitude/state/models.json` contiene `slots: {}`, listas `recentModels` vacías y `favorites: []`.

## Diagnóstico final

**Hecho observado:** hay artefactos descargados e íntegros y referencias en inventario/afiliaciones, pero la CLI instalada no reconoce un ID canónico de Qwen y no lista ningún modelo local.

**No demostrado:** que la causa exacta sea memoria, falta de compatibilidad de la arquitectura, defecto de catálogo o defecto de versión. Tampoco se ha demostrado que Qwen3.5-4B no pueda ejecutarse en este hardware con otro runtime o con una ruta de carga compatible.

**No hay resultados de rendimiento de Magnitude** y no se deben inventar ni completar por estimación.

## Cierre y mantenimiento

- No borrar los blobs verificados ni volver a descargar los aproximadamente 3,67 GB del artefacto principal + proyector.
- No editar manualmente `models.json` ni `catalog-affiliations.json`.
- No reinstalar Magnitude a ciegas: la CLI informa que está actualizada.
- Marcar Magnitude como **intento bloqueado por catálogo/CLI; inferencia no medida** en la comparativa.
- Reabrir la prueba solo si una actualización/corrección de Magnitude publica Qwen como compatible o documenta un flujo de registro/carga aplicable a esta versión. Entonces ejecutar una petición real y medir TTFT, prefill, generación, duración, memoria y configuración exacta.

## Referencias cruzadas

- [Inventario comparativo Qwen3.5: TensorFold, llama.cpp y prueba de Magnitude](../experimental/inventario-comparativo-qwen35-tensorfold-llamacpp-2026-10-20.md)
- [Comparativa medida de tres runtimes (2026-10-20)](qwen35-4b-three-runtimes-2026-10-20.md)
