# Cosmic Lightning — informe de descarga, procedencia y preparación experimental

**Fecha:** 2026-10-31  
**Estado:** artefactos descargados y auditados localmente; benchmark propio de Cosmic Lightning pendiente. Se incorpora como referencia de rendimiento el ensayo previo LFM3-1.7B Uncensored, sin atribuirlo como medición directa de Cosmic Lightning.  
**Equipo de referencia:** Ubuntu en MSI Thin 15 B12UC, Intel Core i7-12650H, 16 CPU lógicas, 14.8 GiB RAM, NVIDIA RTX 3050 Laptop GPU con 4 GiB VRAM.

## 1. Resumen ejecutivo

Se descargaron dos repositorios de Hugging Face:

1. **Modelo original:** [cosmicstack/cosmic-lightning](https://huggingface.co/cosmicstack/cosmic-lightning)
2. **Conversión GGUF:** [bartowski/cosmicstack_cosmic-lightning-GGUF](https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF)

El original ocupa aproximadamente **3.48 GB** y el conjunto de GGUF aproximadamente **25 GB**. Se recopilaron metadatos del repositorio, archivos, hashes y datos de licencia/procedencia. La revisión del original quedó fijada para reproducibilidad.

**Importante:** esta fase no demuestra todavía que el modelo funcione en llama.cpp, TensorFold u otro motor. No se deben atribuir velocidades, prefill, TTFT ni calidad hasta ejecutar pruebas controladas.

## 2. Repositorio original: identificación y revisión

| Campo | Valor |
|---|---|
| Repositorio | `cosmicstack/cosmic-lightning` |
| URL | https://huggingface.co/cosmicstack/cosmic-lightning |
| Revisión descargada | `b5c2c76e95397a0b73cb618a2ec506a755f2832d` |
| Creación indicada por Hub | 2026-10-29 19:33:48 UTC |
| Última modificación indicada por Hub | 2026-10-29 19:59:08 UTC |
| Visibilidad | Público |
| Acceso | No gated; descarga sin autenticación |
| Tarea declarada | `text-generation` |
| Licencia declarada en metadatos | Apache-2.0 |
| Etiquetas relevantes | `lfm3`, `transformers`, `safetensors`, `custom_code` |

### Archivos descargados del original

- `README.md`
- `chat_template.jinja`
- `config.json`
- `configuration_lfm3.py`
- `generation_config.json`
- `lfm3_conv.py`
- `model.safetensors` — aproximadamente 3.3 GB (3,457,635,448 bytes)
- `modeling_lfm3.py`
- `tokenizer.json` — aproximadamente 18 MB
- `tokenizer_config.json`

La presencia de `configuration_lfm3.py` y `modeling_lfm3.py`, junto con las etiquetas del repositorio, apunta a una implementación basada en la familia LFM3 con código de Transformers personalizado. La compatibilidad real con cada runtime debe comprobarse, no suponerse.

## 3. Repositorio GGUF y cuantizaciones descargadas

Repositorio: [bartowski/cosmicstack_cosmic-lightning-GGUF](https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF)

Directorio local utilizado:

`~/modelos/cosmic-lightning/GGUF`

Tamaño aproximado de todo el directorio: **25 GB**.

### Archivos GGUF

| Cuantización | Tamaño (bytes) | Tamaño decimal aproximado |
|---|---:|---:|
| IQ2_M | 651,650,112 | 651.7 MB |
| IQ3_M | 925,533,248 | 925.5 MB |
| IQ3_XS | 812,467,264 | 812.5 MB |
| IQ3_XXS | 780,870,720 | 780.9 MB |
| IQ4_NL | 1,115,636,800 | 1,115.6 MB |
| IQ4_XS | 997,303,360 | 997.3 MB |
| Q2_K | 701,310,016 | 701.3 MB |
| Q3_K_L | 887,579,712 | 887.6 MB |
| Q3_K_M | 847,299,648 | 847.3 MB |
| Q3_K_S | 811,500,608 | 811.5 MB |
| Q4_0 | 1,057,971,264 | 1,058.0 MB |
| Q4_1 | 1,145,353,280 | 1,145.4 MB |
| Q4_K_L | 1,190,388,800 | 1,190.4 MB |
| Q4_K_M | 1,115,636,800 | 1,115.6 MB |
| Q4_K_S | 1,053,787,200 | 1,053.8 MB |
| Q5_K_M | 1,352,451,136 | 1,352.5 MB |
| Q5_K_S | 1,268,171,840 | 1,268.2 MB |
| Q6_K | 1,516,143,680 | 1,516.1 MB |
| Q6_K_L | 1,582,933,056 | 1,582.9 MB |
| Q6_K_S | 1,456,718,912 | 1,456.7 MB |
| Q8_0 | 1,846,238,272 | 1,846.2 MB |
| BF16 | 3,466,625,792 | 3,466.6 MB |

> Los tamaños corresponden a los archivos registrados en la auditoría local. MB se expresa aquí en unidades decimales (1 MB = 1,000,000 bytes).

### Archivos auxiliares del repositorio GGUF

- `cosmicstack_cosmic-lightning-calibration-v6.txt` — aproximadamente 1 MB
- `imatrix.gguf` — aproximadamente 3.6 MB
- Archivos JSON de layouts
- Archivos auxiliares de tipos de tensor

No todos los archivos auxiliares tenían hash remoto publicado en el árbol de Hugging Face; esa diferencia quedó anotada en el expediente local.

## 4. Integridad y hashes

Se ejecutó una comprobación local de SHA-256 para los archivos descargados y se compararon los hashes disponibles con los publicados por Hugging Face.

Resultado documentado en la sesión:
- Los archivos GGUF contrastados coinciden con los SHA-256 publicados en Hub.
- `model.safetensors` y `tokenizer.json` del repositorio original coinciden con los hashes de Hub.
- Algunos sidecars/layouts no tienen hash remoto para realizar comparación directa.

Registro local completo:
`~/modelos/cosmic-lightning/expediente-licencia/SHA256SUMS-COMPLETO.txt`

Este resultado acredita integridad respecto de los hashes publicados por el repositorio en el momento de la comprobación; no constituye una auditoría criptográfica independiente del autor ni una validación del comportamiento del modelo.

## 5. Entorno de descarga

Se creó un entorno virtual Python aislado:

`~/venvs/huggingface`

Comandos ejecutados:

```bash
mkdir -p ~/venvs
python3 -m venv ~/venvs/huggingface
source ~/venvs/huggingface/bin/activate
pip install --upgrade pip
pip install --upgrade huggingface_hub
hf --version
```

Versiones registradas:
- Python: 3.14
- pip: 26.2.2
- huggingface_hub / CLI `hf`: 2.4.0

### Comandos de descarga reproducibles

Modelo original:

```bash
mkdir -p ~/modelos/cosmic-lightning/original
hf download cosmicstack/cosmic-lightning \
  --local-dir ~/modelos/cosmic-lightning/original
```

Repositorio GGUF:

```bash
mkdir -p ~/modelos/cosmic-lightning/GGUF
hf download bartowski/cosmicstack_cosmic-lightning-GGUF \
  --local-dir ~/modelos/cosmic-lightning/GGUF
```

Para reproducir exactamente el original, usar la revisión fijada:

```bash
hf download cosmicstack/cosmic-lightning \
  --revision b5c2c76e95397a0b73cb618a2ec506a755f2832d \
  --local-dir ~/modelos/cosmic-lightning/original
```

## 6. Expediente de licencia y procedencia

Directorio local del expediente:

`~/modelos/cosmic-lightning/expediente-licencia`

En la sesión se generó/consultó el resumen de metadatos y repositorio:

`resumen-repositorio.txt`

### Distinción obligatoria entre licencias

No deben tratarse como una única licencia ni propagarse automáticamente entre repositorios:

| Artefacto / repositorio | Licencia declarada | Qué significa para este expediente |
|---|---|---|
| `cosmicstack/cosmic-lightning` | **Apache License 2.0** (metadatos de Hugging Face) | Es la licencia que declara la ficha del repositorio Cosmic Lightning. Debe conservarse su LICENSE/avisos y revisión exacta. |
| Modelo base `LiquidAI/LFM3-1.7B` | **LFM Open License v1.0** | No es Apache 2.0 estándar: aunque está basada en Apache 2.0, incluye una restricción de uso comercial para entidades con ingresos anuales superiores a 10 millones USD, además de obligaciones de atribución y conservación de avisos. |
| `AtomicChat/LFM3-1.7B-Uncensored-GGUF` | **LFM Open License v1.0** | La ficha identifica explícitamente el modelo base LiquidAI y dice que la ablación de seguridad y cuantización se distribuyen bajo la licencia base. No es el mismo artefacto que el GGUF de bartowski. |
| `bartowski/cosmicstack_cosmic-lightning-GGUF` | **No verificada independientemente en esta auditoría** | No se debe asumir que la conversión tiene Apache 2.0 por el mero hecho de que la ficha del modelo original lo indique, ni atribuirle LFM Open sin inspeccionar su LICENSE y procedencia. |

**Alerta de procedencia/licencia:** si la coincidencia uno-a-uno de pesos/hash que se está observando implica que Cosmic Lightning incorpora exactamente los pesos de LiquidAI/LFM3-1.7B, la etiqueta Apache-2.0 de la ficha Cosmic no resuelve por sí sola el posible conflicto con la licencia LFM Open v1.0 del modelo base. Hace falta determinar quién publicó los pesos, qué derechos tenía para relicenciarlos y qué LICENSE/NOTICE acompañan a la revisión concreta. La similitud arquitectónica o el nombre LFM3 no bastan para establecer identidad; la identidad binaria de los pesos sí es un indicio material y debe documentarse con hashes comparativos y sus rutas de origen. Hasta aclararlo, marcar la situación como **licencia declarada Apache-2.0 / procedencia upstream por aclarar**, no como una conclusión jurídica de que Apache prevalece.

La LFM Open License v1.0 está basada en Apache 2.0, pero añade una condición comercial significativa: la licencia gratuita para uso comercial deja de aplicar si los ingresos anuales de la empresa superan USD 10 millones; para continuar se requiere licencia comercial de Liquid AI. También exige conservar avisos y atribución. No es copyleft y no impone publicar modificaciones.

Antes de redistribuir pesos o publicar derivados, se recomienda conservar junto al artefacto:
- copia de la licencia aplicable y avisos de copyright;
- README y ficha de origen;
- identificador de revisión exacto;
- nombres de los repositorios de origen y conversión;
- hashes de los archivos redistribuidos;
- atribución de la conversión GGUF a su repositorio correspondiente;
- nota de que el GGUF es una conversión, no el artefacto original publicado por `cosmicstack`.

La licencia de la conversión GGUF y las obligaciones de redistribución deben revisarse por separado en el repositorio de bartowski, sin inferir que la ficha del modelo original resuelve automáticamente todos los términos de la conversión.

## 7. Referencia de rendimiento heredada: LFM3-1.7B

Se recuperó el informe previo de LEONES [LFM3-1.7B Uncensored — pruebas en Ubuntu](../subprojects/LFM3/README.md). Este dato permite contextualizar el rendimiento esperado de la familia/los pesos relacionados, pero **no se registra como benchmark ejecutado de Cosmic Lightning**.

### Resultado experimental previo

| Campo | Valor |
|---|---|
| Modelo probado | LFM3-1.7B Uncensored |
| Repositorio | `AtomicChat/LFM3-1.7B-Uncensored-GGUF` |
| Artefacto | `LFM3-1.7B-Uncensored-AD-Q4_K_M.gguf` |
| Motor | llama.cpp CUDA, llama-bench |
| Build | llama.cpp 0.8.0-dev, build 1; commit `c3df4b7` |
| Equipo | MSI Thin 15 B12UC, i7-12650H, 14.8 GiB RAM, RTX 3050 Laptop 4 GiB |
| Parámetros | `-ngl 99 -t 6 -p 512 -n 128 -r 3` |
| Prefill | **4.326,68 ± 254,02 tok/s** (PP512) |
| Generación | **117,29 ± 0,27 tok/s** (TG128) |
| Estado | 3 repeticiones; ejecución confirmada |

En prueba interactiva separada con `llama-cli`, se observaron 99,8–104,4 tok/s de generación. El prefill interactivo varió entre 163,5 y 1.797,1 tok/s según la interacción, por lo que no debe mezclarse con PP512.

### Qué se puede y qué no se puede inferir

- El usuario ha indicado que la comparación de hashes/pesos muestra coincidencia uno-a-uno con LFM3-1.7B. Se incorpora esa observación como premisa de procedencia comunicada, pendiente de adjuntar al expediente la tabla comparativa de SHA-256 y los comandos que la generaron.
- El ensayo de 117,29 tok/s corresponde específicamente a **AtomicChat Uncensored AD-Q4_K_M**, que su propia ficha describe como pesos LFM3 modificados mediante ablación de seguridad (LoRA de rango 1 horneada, W*=2.0) y después cuantizados con el esquema AD.
- Por tanto, no es idéntico al GGUF de bartowski por el mero hecho de compartir el modelo base o pesos upstream. Cambian el proceso de modificación, cuantización, imatrix y posiblemente el formato/metadata del artefacto.
- Se conserva **117,29 tok/s PP512 4.326,68 tok/s** como referencia histórica de LFM3 en este equipo y runtime, no como resultado medido de Cosmic Lightning ni como promesa de que cualquier cuantización de Cosmic obtendrá esa velocidad.
- Para trasladar formalmente la cifra a Cosmic Lightning habría que verificar igualdad SHA-256 del archivo GGUF exacto, o comparar tensor por tensor después de normalizar metadatos, y ejecutar al menos una repetición cruzada con el mismo binario y protocolo. Si el hash del GGUF completo es idéntico, la expectativa de rendimiento del artefacto es muy alta; si solo coincide el checkpoint base, no.

## 8. Consideraciones de ejecución en el equipo de referencia

Hardware de referencia: RTX 3050 Laptop con 4 GiB de VRAM y 14.8 GiB de RAM del sistema.

La cuantización IQ3_XXS (780.9 MB de archivo) es una candidata razonable para la primera prueba de carga por su reducido tamaño, pero el tamaño del archivo **no equivale** al consumo total de memoria en ejecución. También intervienen:
- buffers del runtime y del backend;
- contexto y caché KV;
- memoria temporal de evaluación;
- capas que se descarguen a GPU;
- arquitectura y kernels compatibles;
- reserva de VRAM del escritorio y otros procesos.

La primera ejecución debería usar contexto modesto y generación corta; posteriormente se puede aumentar contexto y offload de GPU en pasos, registrando consumo y errores.

## 9. Plan de validación pendiente

| Fase | Estado | Qué debe registrarse |
|---|---|---|
| Identificar arquitectura y configuración | Parcial: inspección de metadatos iniciada | `config.json`, arquitectura, parámetros y contexto declarado |
| Confirmar runtime y versión | Pendiente | llama.cpp / TensorFold / otros; commit o versión exacta |
| Carga inicial de GGUF | Pendiente | cuantización, comando, éxito/error, RAM y VRAM |
| Prueba de generación | Pendiente | prompt, tokens de entrada/salida, temperatura, seed |
| Medición de velocidad | Pendiente | prefill (tokens/s), generación (tokens/s), TTFT y tiempo total |
| Comparación entre cuantizaciones | Pendiente | mismo prompt, contexto, backend y parámetros |
| Evaluación cualitativa | Pendiente | tareas reproducibles, rúbrica y respuestas completas |
| Registro en LEONES | Este informe | actualizar cuando existan resultados reales |

## 10. Plantilla mínima para el futuro benchmark

Para cada ejecución, registrar:
- fecha y hora;
- equipo, sistema operativo, driver CUDA y memoria libre;
- runtime, versión/commit y parámetros de compilación;
- ruta y cuantización del GGUF, tamaño y SHA-256;
- contexto, batch, número de capas en GPU, threads;
- prompt exacto y número de tokens de entrada;
- máximo de tokens nuevos, temperatura, top-p, seed;
- tiempo de carga, TTFT, prefill en tokens/s;
- generación en tokens/s y duración total;
- RAM máxima y VRAM máxima;
- resultado: éxito, OOM, error de arquitectura o salida incorrecta;
- texto generado y evaluación.

## 11. Conclusión de esta fase

La descarga del modelo original y de la colección GGUF se completó. La revisión del repositorio original está fijada, los tamaños de las cuantizaciones están inventariados y los hashes disponibles fueron contrastados con Hugging Face.

**No hay aún resultados de inferencia medidos directamente sobre Cosmic Lightning.** Sí existe una referencia LFM3 previa en el mismo equipo: 4.326,68 ± 254,02 tok/s de PP512 y 117,29 ± 0,27 tok/s de TG128, medida sobre AtomicChat Uncensored AD-Q4_K_M con llama.cpp CUDA. No debe presentarse como resultado propio de Cosmic hasta confirmar identidad del artefacto GGUF exacto. La distinción Apache-2.0 / LFM Open v1.0 / licencia GGUF de conversión no verificada queda incorporada como asunto de procedencia prioritario.

## Referencias

- Modelo original: https://huggingface.co/cosmicstack/cosmic-lightning
- Revisión original: `b5c2c76e95397a0b73cb618a2ec506a755f2832d`
- Conversión GGUF: https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF
- LFM3-1.7B Uncensored benchmark LEONES: https://github.com/robertosantosx2/LEONES/blob/main/docs/subprojects/LFM3/README.md
- LFM3-1.7B upstream y licencia: https://huggingface.co/LiquidAI/LFM3-1.7B
- Explicación oficial LFM Open License v1.0: https://www.liquid.ai/lfm-license
- AtomicChat Uncensored GGUF y licencia declarada: https://huggingface.co/AtomicChat/LFM3-1.7B-Uncensored-GGUF
- Expediente local de hashes: `~/modelos/cosmic-lightning/expediente-licencia/SHA256SUMS-COMPLETO.txt`



## 12. Auditoría de origen y relicenciamiento — 2026-10-31

### Dictamen ejecutivo

**No se ha encontrado evidencia pública de una autorización de Liquid AI para relicenciar los pesos de LFM3-1.7B bajo Apache-2.0.** La evidencia disponible apunta a que Cosmic Lightning reutiliza sin cambios los pesos oficiales de LiquidAI/LFM3-1.7B, mientras que la ficha de Cosmic declara Apache-2.0. Esta discrepancia debe tratarse como una **incompatibilidad de procedencia/licencia no resuelta**, no como una relicencia válida.

No es posible concluir solo con fuentes públicas que haya infracción: podría existir una autorización privada, un acuerdo de licencia separado o un error de metadatos. No se ha localizado públicamente ninguno de esos documentos ni una declaración de Liquid AI que confirme una excepción.

### 12.1 Cadena de procedencia reconstruida

| Eslabón | Evidencia pública observada | Conclusión |
|---|---|---|
| Liquid AI → LFM3-1.7B | La ficha oficial identifica el modelo como LFM3-1.7B y declara expresamente LFM Open License v1.0. Su arquitectura y tamaño coinciden con Cosmic Lightning. | Fuente upstream oficial y titular/licenciante identificado: Liquid AI. |
| LFM3-1.7B → cosmicstack/cosmic-lightning | Un análisis público de David Hendrickson (@TeksEdge) informa que el SHA-256 del archivo de pesos de 3.46 GB coincide exactamente en ambos repositorios (prefijo/sufijo publicado: `135922ca...fb4330`) y que la configuración también es LFM3. | Evidencia externa fuerte de copia binaria idéntica del checkpoint; no de un fine-tune ni de pesos nuevos. El hash completo no está reproducido en esa publicación. |
| Cosmic Lightning → bartowski GGUF | La ficha del repositorio GGUF declara `base_model:cosmicstack/cosmic-lightning`, `base_model:quantized:cosmicstack/cosmic-lightning` y licencia `apache-2.0`. | La cadena declarada de conversión pasa por Cosmic Lightning; no constituye prueba de autorización de Liquid AI. |
| Liquid AI → AtomicChat Uncensored GGUF | La ficha de AtomicChat identifica LiquidAI/LFM3-1.7B como modelo base y declara licencia `other`; el informe previo de LEONES registra su modificación/ablación y cuantización. | Ejemplo distinto de derivado LFM3: no confundir con Cosmic Lightning ni usar su hash/benchmark como prueba de identidad del GGUF de bartowski. |

**Límite de verificación:** el hash completo de Cosmic/LiquidAI no se ha descargado de forma independiente en esta auditoría web; se cita el cotejo externo publicado y se conserva como verificación pendiente repetir localmente contra ambos repositorios fijados por commit. El expediente local anterior verificó hashes de los archivos descargados frente a los hashes publicados por sus propios repositorios, pero eso por sí solo no compara Cosmic contra LiquidAI.

### 12.2 Licencias: texto aplicable y efecto

**LiquidAI/LFM3-1.7B — LFM Open License v1.0.** La ficha oficial de Liquid AI identifica esta licencia. No es Apache-2.0 sin cambios: deriva de su texto, pero condiciona las concesiones de copyright y patentes a la limitación comercial de la sección 5. El umbral definido es USD 10 millones de ingresos anuales de la entidad legal (incluye entidades vinculadas según la definición contractual). Para entidades que alcanzan/superan el umbral, el uso comercial no queda autorizado por esa licencia gratuita; Liquid AI indica que deben obtener licencia comercial. Investigación/no comercial y las organizaciones sin ánimo de lucro cualificadas tienen tratamiento específico.

**Redistribución y derivados (sección 4).** La licencia permite redistribuir el Work o derivados en cualquier medio y en forma Source u Object, con o sin modificaciones, siempre que se entregue copia de la licencia, se indiquen los archivos modificados y se conserven avisos de copyright, patentes, marcas y atribución, además de los avisos NOTICE si existen. La definición de Object form incluye transformaciones mecánicas o traducciones a otros medios. Por tanto, una conversión de pesos a GGUF no borra automáticamente las condiciones upstream.

La sección 4 permite añadir términos propios o diferentes para las modificaciones o para un derivado como conjunto, **pero condiciona expresamente esa posibilidad a que el uso, reproducción y distribución del Work upstream sigan cumpliendo la LFM Open License**. No equivale a poder sustituir la licencia upstream del checkpoint original por Apache-2.0 ni a eliminar sus condiciones para los receptores.

**Cosmic Lightning — declaración Apache-2.0.** La ficha de Hugging Face etiqueta el repositorio como `license:apache-2.0`. Hugging Face explica que ese campo es metadato de la model card introducido por quien mantiene el repositorio; permite declarar licencias estándar o personalizadas. El campo no es una revisión de titularidad, no autentica la cadena de derechos y no constituye consentimiento del titular upstream. En la descarga local inventariada para Cosmic no apareció un archivo LICENSE/NOTICE entre los ficheros registrados; hay que volver a comprobar el árbol completo de la revisión fijada antes de afirmar de forma absoluta que no existe ningún aviso.

**bartowski GGUF — declaración Apache-2.0.** La ficha del repositorio de conversión también declara Apache-2.0, pero su propia metadata lo vincula como cuantización de Cosmic Lightning. La etiqueta del repositorio no puede otorgar más derechos sobre los pesos de los que tenía el proveedor de origen. Para el contenido de los pesos cuantizados, la licencia upstream sigue siendo una cuestión material. El código, scripts, calibration corpus, imatrix, layouts y otros materiales auxiliares podrían tener derechos/licencias distintos; deben analizarse por separado y no confundirse con los pesos.

### 12.3 ¿Se ha demostrado el relicenciamiento?

| Pregunta de auditoría | Resultado |
|---|---|
| ¿Cosmic declara Apache-2.0? | Sí, como metadata del Hub. |
| ¿LFM3 oficial declara LFM Open v1.0? | Sí, en la ficha oficial de Liquid AI. |
| ¿Hay evidencia pública de que los pesos sean byte a byte idénticos? | Sí: un análisis independiente publica el mismo SHA-256 abreviado para ambos archivos. Falta reproducir aquí el hash completo. |
| ¿Se ha identificado una modificación de los pesos Cosmic respecto a LFM3? | No. La evidencia disponible apunta a identidad binaria, no a fine-tuning. |
| ¿Se ha encontrado autorización expresa de Liquid AI para Apache-2.0? | No. |
| ¿Se ha encontrado contrato, excepción o aclaración pública del titular? | No localizado. |
| ¿La metadata Apache del GGUF de bartowski resuelve la cuestión? | No. Es una declaración del repositorio derivado, no una autorización del titular upstream. |
| ¿Puede declararse probado un incumplimiento jurídico? | No con la evidencia actual; faltaría descartar autorización privada y analizar jurisdicción/hechos. |

**Resultado:** relicenciamiento **no acreditado**. La declaración Apache-2.0 de Cosmic Lightning no debe aceptarse como prueba suficiente de que el checkpoint de Liquid AI pasó válidamente a Apache-2.0. La posición prudente es mantener para los pesos la LFM Open License v1.0 como licencia upstream aplicable, salvo que Cosmic Stack aporte una autorización válida de Liquid AI o demuestre otra procedencia independiente.

### 12.4 Qué evidencia resolvería la cuestión

1. **Respuesta escrita de Liquid AI** que confirme que autorizó a Cosmic Stack a redistribuir exactamente ese checkpoint bajo Apache-2.0, con alcance sobre pesos y derivados/quantizaciones, fecha efectiva y titular/entidad autorizada.
2. **Contrato o licencia separada** entre Liquid AI y Cosmic Stack, o prueba de que Cosmic Stack es titular/cesionario con facultad de relicenciar esos pesos.
3. **Expediente de Cosmic Stack**: origen de los pesos, proceso de entrenamiento/fine-tuning (si lo hubo), hashes previos/posteriores, autoría, avisos y motivo documentado de la declaración Apache.
4. **Revisión completa del árbol Git/Hugging Face** de ambos repositorios, incluidos commits históricos, LICENSE, NOTICE, README y metadatos por revisión.
5. **Confirmación del mantenedor de bartowski** sobre la fuente exacta de los pesos, versión de llama.cpp/convertidor, tratamiento de la licencia upstream y si recibió autorización adicional. La declaración de bartowski por sí sola no sustituye el permiso del titular.
6. **Reproducir los SHA-256 completos** de `model.safetensors` en los commits concretos de LiquidAI y Cosmic. Si son idénticos, se confirma copia binaria; si difieren, comparar tensor por tensor y establecer si existe fine-tuning real.

### 12.5 Recomendación operativa para LEONES

- Mantener los artefactos descargados para investigación y pruebas internas, conservando sus revisiones y hashes.
- No redistribuir ni publicar mirrors de los pesos/quantizaciones con una etiqueta Apache-2.0 como si el relicenciamiento estuviera verificado.
- Para redistribución, tratar provisionalmente los pesos como sujetos a LFM Open v1.0 y conservar licencia, atribución y NOTICE upstream, hasta aclaración.
- No describir Cosmic Lightning como un nuevo modelo entrenado por Cosmic Stack: con la evidencia actual es más exacto denominarlo **republicación de LFM3-1.7B con metadata Apache-2.0 no acreditada**, pendiente de respuesta del autor.
- Mantener la licencia del código de conversión y de los sidecars separada de la licencia de los pesos.
- Si se usa en un producto comercial, comprobar la definición de entidad legal y el umbral de ingresos de LFM Open v1.0; solicitar asesoramiento jurídico para una decisión de distribución/comercialización.

### 12.6 Fuentes consultadas

- Liquid AI, ficha oficial LFM3-1.7B (identifica LFM Open License v1.0): https://huggingface.co/LiquidAI/LFM3-1.7B
- Liquid AI, texto completo y FAQ LFM Open License v1.0: https://www.liquid.ai/lfm-license
- Cosmic Lightning, ficha y metadata declarada: https://huggingface.co/cosmicstack/cosmic-lightning
- Bartowski, conversión GGUF y metadata de base_model/licencia: https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF
- David Hendrickson (@TeksEdge), observación pública del SHA-256 coincidente y discrepancia de licencias: https://teapawt.org/TeksEdge
- Hugging Face, documentación de model cards y metadatos de licencia: https://huggingface.co/docs/hub/model-cards
- Hugging Face, documentación de licencias de repositorios: https://huggingface.co/docs/hub/main/repositories-licenses
- Local AI Release Board, registro de lanzamiento 2026-10-29 y clasificación como modelo recién publicado/no verificado: https://recentmodel.com/models/cosmicstack/cosmic-lightning/

*Nota: este apartado es una auditoría técnica/documental de procedencia y licencias, no asesoramiento jurídico. No se ha recibido respuesta de Liquid AI, Cosmic Stack ni bartowski durante esta investigación.*
