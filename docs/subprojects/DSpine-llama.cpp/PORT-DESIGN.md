# Diseño de port DSpine a llama.cpp

**Tipo:** diseño de ingeniería previo a implementación.  
**Estado:** bloqueado hasta disponer de un runtime llama.cpp que incorpore DSpine de verdad.

## Referencia de comportamiento

Implementación de referencia oficial:

- `Tencent/DSpine/sglang_dspine/models/dspine.py`
- `Tencent/DSpine/sglang_dspine/spec.py`
- `Tencent/DSpine/sglang_dspine/kernels/dspine.py`
- `Tencent/DSpine/dspine_mlx/dspine_mlx/model.py`
- `Tencent/DSpine/dspine_mlx/dspine_mlx/config.py`

Blobs consultados durante esta auditoría:

| Archivo | Blob SHA |
|---|---|
| `sglang_dspine/models/dspine.py` | `d0f65f0911c3eee3de7e664200be3af0e2e77a38` |
| `sglang_dspine/spec.py` | `0db1ed234e0486ae8f64d6c2af731bdc5fdd057d` |
| `sglang_dspine/layers/layout.py` | `8255b86fcb056e686055409e50d366d495724c7c` |
| `sglang_dspine/kernels/dspine.py` | `1de4ea9cb3ba4683ca9ef27b07c3c1376a813f80` |
| `dspine_mlx/dspine_mlx/model.py` | `099209a1491c400ca0e5079d1ad1f26dd64dfecf` |
| `dspine_mlx/dspine_mlx/config.py` | `28292eb8feacaa9bd4d04f547b78f266216cbaf7` |

Los hashes son blob SHAs de GitHub, no SHA del commit completo de Tencent/DSpine.

## Contrato que debe respetar el port

El checkpoint contiene un drafter con arquitectura Qwen3 y un puente de código DSpine. La implementación de referencia reutiliza componentes DFlash para el bloque de draft, pero añade semántica propia:

- Proyecciones de características del modelo objetivo.
- Capas de draft Qwen3 con atención causal sobre el bloque y acceso al contexto objetivo.
- Escrituras de código adyacente a través de capas, con pesos aprendidos en `selected_prefix_bridge.*`.
- Refinamiento de la última escritura/selección mediante un head top-k descrito en la configuración.
- Reglas estrictas de configuración; los modos desconocidos o terminal-corrected se rechazan.
- Kernels de preparación/normalización de códigos, mensajes de características, finalización de escrituras y selección.

No se debe implementar el port suponiendo que basta con reutilizar sin cambios el decodificador DFlash. La propia referencia valida el contrato del checkpoint y rehúsa configuraciones no soportadas.

## Diseño sugerido en llama.cpp

### A. Identificación y validación

Añadir un tipo de speculative decoding independiente:

- Enum: `COMMON_SPECULATIVE_TYPE_DSPINE`.
- Nombre CLI: `draft-dspine`.
- Detección de GGUF basada en metadatos inequívocos.
- Validación de la pareja target/drafter y de los IDs de capas.
- Rechazo explícito cuando la configuración no corresponda a DSpine.

No mapear el tipo a `draft-dflash` ni `draft-dspark`.

### B. Carga de tensores

Primero documentar el inventario exacto de tensores y formas a partir del checkpoint oficial. La conversión GGUF debe conservar:

- Nombres del puente `selected_prefix_bridge.*`.
- Tensores de atención, MLP y normalización del drafter.
- Capas objetivo requeridas para las características compartidas.
- Metadatos de bloque, máscara y refinamiento.

El conversor debe tener pruebas de ida/vuelta de nombres, dimensiones y tipos de datos. BF16 debe conservarse para los tensores de puente cuando el checkpoint lo requiera.

### C. Grafo GGML

Separar el trabajo en subgrafos testeables:

1. Extracción de hidden states del target.
2. Proyección/normalización de características de contexto.
3. Construcción de códigos y anclas.
4. Una escritura adyacente aprendida por capa.
5. Atención causal del bloque con contexto visible.
6. Refinamiento final/top-k.
7. Proyección a logits y tokens propuestos.

Evitar primero la optimización CUDA: la referencia numérica debe funcionar en CPU/GGML antes de añadir kernels específicos.

### D. Integración especulativa

Reutilizar la infraestructura común de propuesta/verificación solo donde su contrato coincida. DSpine debe implementar su propio estado de draft, preparación del bloque, consumo de hidden states y reconstrucción del prefijo aceptado.

Casos mínimos:
- greedy determinista;
- sampling con rejection sampling;
- aceptación de prefijo parcial;
- bloque sin tokens aceptados;
- EOS dentro del prefijo;
- múltiples secuencias, si el backend lo soporta;
- reset y rollback del estado KV tras rechazo.

### E. Backends

Orden recomendado:

1. GGML CPU de referencia.
2. CUDA SM86.
3. CPU/GPU híbrido, solo después de verificar coherencia numérica y asignación de memoria.

No escribir kernels CUDA hasta que las pruebas CPU validen las fórmulas y el orden de operaciones.

## Checkpoints y coste aproximado de memoria

Metadatos públicos de Hugging Face:

| Drafter | Parámetros publicados | Target obligatorio |
|---|---:|---|
| Qwen3-8B-DSpine-b16 | 1.2378B | Qwen3-8B |
| Qwen3.8-27B-DSpine-b16 | 2.0259B | Qwen3.8-27B |

Los parámetros no equivalen al tamaño final de pesos: el formato/precisión determina el tamaño en memoria. A estos pesos se añaden KV, buffers de contexto, workspace, embeddings/hidden states y memoria del runtime.

El checkpoint oficial de Qwen3-8B se publica en Safetensors, no debe asumirse que es directamente cargable por llama.cpp. La conversión y el soporte GGUF son trabajo adicional. Una conversión comunitaria del drafter Qwen3.8-27B no es soporte upstream ni demuestra compatibilidad del runtime.

## Pruebas numéricas necesarias

- Comparar outputs de cada capa del drafter frente a SGLang de referencia en inputs fijos.
- Tolerancias por dtype (BF16/FP16/F32) declaradas, no elegidas después de ver los resultados.
- Comparar códigos/índices top-k antes de comparar tokens.
- Verificar que el prefijo greedy aceptado coincide exactamente.
- Repetir en CPU y CUDA.
- Ejecutar con diferentes longitudes de contexto y tamaños de bloque.
- Guardar prompt, tokens, seed, hashes de modelo, commit, flags y logs.

## Criterios de salida antes de MSI

- [ ] Un commit de llama.cpp con el tipo `draft-dspine` real.
- [ ] Conversor y documentación de GGUF para al menos Qwen3-8B.
- [ ] Tests de metadatos, tensores y formas.
- [ ] Tests de equivalencia contra referencia.
- [ ] Build CPU y CUDA en CI.
- [ ] Smoke test de CLI que rechace modelos incompatibles.
- [ ] Estimación de memoria calculada a partir de los ficheros exactos.
- [ ] Paquete MSI reversible y sin tocar la instalación llama.cpp activa.

Hasta completar esos puntos, no hay razón técnica para pedir una ejecución en el MSI.
