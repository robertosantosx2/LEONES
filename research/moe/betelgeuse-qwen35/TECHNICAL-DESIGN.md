# Diseño técnico: Qwen3.5 trunk-only para Betelgeuse

## 1. Contrato de entrada

GGUF de referencia:

- Arquitectura: `qwen35moe`
- Bloques: 41
- Expertos: 256; expertos activos por token: 8
- Dimensiones gate/up: (2048, 512, 256)
- Dimensión down: (512, 2048, 256)
- Archivo: 10,676,139,840 bytes
- SHA-256: `479cc80b2500f7ba5f6131986da188ecb406cf7855094c5d8ae0ec332a715105`

Distribución de tipos observada en los tensores expertos:

| Tensor | Capas | Tipo |
|---|---:|---|
| gate/up | 0–39 | IQ2_XXS |
| gate/up | 40 | Q8_0 |
| down | 0–4, 36–39 | IQ2_XS |
| down | 5–35 | IQ2_XXS |
| down | 40 | Q8_0 |

Son 123 tensores expertos en total: 40 capas trunk × 3 matrices + 3 matrices del bloque 40. El inventario detallado contiene 120 tensores paginables (capas 0–39) y 3 tensores MTP (capa 40).

## 2. Límites de capa

La diferencia entre 41 bloques GGUF y 40 capas paginables es intencionada:

- Los bloques `blk.0`–`blk.39` pertenecen al tronco principal.
- `blk.40` contiene tensores `nextn` del predictor auxiliar.
- El paginador reserva índices según `n_layer × n_expert × 3`; debe recibir 40 como número de capas trunk.
- Nunca pasar 41 al paginador para este modo: eso haría que intente resolver como MoE paginable el bloque auxiliar.

La confirmación final debe provenir del cargador de modelo y del runtime compilado, no solo de la inspección de nombres.

## 3. Reglas de empaquetado

1. Seleccionar únicamente `blk.{0..39}.ffn_{gate,up,down}_exps.weight`.
2. Exigir que las tres matrices existan en cada capa.
3. Exigir 256 expertos y geometría compatible.
4. Mantener el orden de expertos y el orden de matrices esperado por el índice nativo.
5. Calcular el tamaño combinado por experto antes de escribir; el límite de 256 MiB se aplica a cada bloque combinado por experto, no al tensor GGUF entero.
6. Copiar bytes sin des-cuantizar ni volver a cuantizar.
7. Escribir un índice con 40 × 256 × 3 entradas; rechazar duplicados, huecos y capas fuera del rango.
8. Hacer round-trip de bytes para cada tensor/experto con fixture sintético.
9. No incluir las matrices de la capa 40 en `experts.bin`.

Los bloques de experto de la capa 40 tienen un tamaño estimado de 3,342,336 bytes por experto para el conjunto gate/up/down en Q8_0, muy por debajo del límite de 256 MiB. Aun así, se preservan en el GGUF porque pertenecen al MTP.

## 4. GGUF denso y preservación

El packer existente tiene un camino de bundle asociado a Qwen3.8 que presupone dos shards y PLE. No reutilizar ese flujo como si fuera genérico.

El adaptador Qwen3.5 debe:

- producir un GGUF trunk/dense compatible con el cargador Betelgeuse;
- externalizar solo los datos expertos trunk (0–39);
- preservar los tensores auxiliares `blk.40.nextn.*`;
- preservar tokenizer, configuración, metadata de arquitectura, tensores no expertos y alineación GGUF;
- no crear un segundo archivo PLE;
- generar un manifiesto que relacione nombre, capa, matriz, experto, tipo, offsets/tamaños y hash del segmento cuando el formato lo permita.

No truncar ni reescribir a mano el GGUF. La operación de stripping debe usar las APIs GGUF del mismo árbol de código y tener un test de lectura posterior con el lector GGUF upstream.

## 5. Integración del cargador

Puntos upstream que requieren cambio o verificación:

- `tools/moe_pack.py`: separar el layout de expertos trunk de la lógica de bundle PLE Qwen3.8.
- `src/moe_pager.cpp`: comprobar que el índice tiene exactamente 40 × 256 × 3 entradas y que los nombres se resuelven para las capas trunk.
- `src/models/qwen35moe.cpp`: el camino trunk debe cargar los tensores no expertos; el camino MTP debe respetar el modo `load_mtp=false`.
- `src/llama-context.cpp`: validar que la ruta genérica de paginación MoE se usa para Qwen3.5 y no la ruta de anillo especializada para otras arquitecturas.
- Parámetro de capas del paginador: 40, no el número total de bloques GGUF (41).

No se debe modificar el GGUF original ni cambiar la firma de cuantización de los pesos.

## 6. Criterios de aceptación

### Packer
- Fixture sintético de 40 capas × 256 expertos, con mezclas IQ2_XS/IQ2_XXS/Q8_0.
- Rechazo de capa ausente, matriz ausente, forma incompatible, número de expertos incorrecto, índice duplicado y capa 40 en el bundle.
- Round-trip byte-exact de cada segmento.
- El bundle final no contiene PLE ni referencias `ple_file`.

### GGUF
- El GGUF generado vuelve a abrirse con el lector GGUF.
- Los metadatos originales se preservan, salvo campos explícitamente documentados.
- Los tensores `blk.40.nextn.*` permanecen presentes y sus bytes son idénticos.
- Los expertos trunk están externalizados y no duplicados en el archivo denso.

### Runtime
- El cargador identifica `qwen35moe` sin fallback a otra arquitectura.
- Paginador dimensionado a 40 capas.
- MTP desactivado en el primer smoke test.
- Sin errores de índices, lecturas fuera de rango ni OOM inesperados.
- Una generación corta determinista se completa antes de ejecutar benchmarks.

## 7. Orden de validación

1. Tests unitarios del packer con fixtures.
2. Inspección del GGUF original y verificación del SHA-256.
3. Dry-run del layout real.
4. Generación de bundle en disco local.
5. Reapertura y comparación del GGUF denso y `experts.bin`.
6. Build de Betelgeuse con soporte Qwen3.5.
7. Smoke test con contexto pequeño y MTP apagado.
8. Benchmark con registro de RSS, swap, VRAM, prompt eval y generación t/s.

El paso 4 en adelante se ejecutará en el MSI, no en GitHub. Los artefactos de pesos no se versionarán.
