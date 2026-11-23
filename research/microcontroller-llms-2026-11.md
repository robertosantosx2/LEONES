# Microcontroller-LLMs — LLMs en ESP32 y microcontroladores

**Fecha de incorporación:** 2026-11-21  
**Estado:** prospección documental; métricas y afirmaciones externas pendientes de reproducción independiente.  
**Categoría:** investigación de modelos, motores y técnicas.

## Objetivo

Investigar arquitecturas de modelos de lenguaje que ejecuten directamente en microcontroladores, especialmente ESP32/ESP32-S3, incluyendo memoria Flash como almacenamiento de pesos, PSRAM, modelos pequeños, MoE, cuantización extrema, distilación, optimización de kernels y clusters distribuidos.

No asumir que las métricas de terceros son benchmarks LEONES. Registrar hardware, firmware, tokenizer, contexto, cuantización, RAM/Flash, método de medición, tokens/s, latencia, energía y calidad de tarea.

## Hallazgos iniciales

| Proyecto / recurso | Arquitectura | Afirmación publicada / interés | Estado |
|---|---|---|---|
| [manjunathshiva/esp32-tinyllm](https://github.com/manjunathshiva/esp32-tinyllm) | 28,9 M parámetros; Per-Layer Embeddings (PLE), tabla de embeddings en Flash, núcleo denso | ~9,5–9,76 tok/s; ESP32-S3, 16 MB Flash / 8 MB PSRAM; TinyStories | Referencia primaria por inspeccionar y reproducir |
| [Bellman281/esp32-tinyLLM](https://github.com/Bellman281/esp32-tinyLLM) | Implementación Rust de la idea PLE | Reporta ~10,50 tok/s, optimización MSPI | Comparación Rust/C pendiente |
| [slvDev/esp32-ai](https://github.com/slvDev/esp32-ai) | Investigación de LLM en ESP32 y PLE | Antecedente relacionado | Revisar arquitectura y relación de derivación |
| [MoE de 5,2 M, Reddit](https://www.reddit.com/r/esp32/comments/1vjgbkk/i_ran_a_full_llm_model_on_an_esp32_dev_kit_v1/) | 16 expertos, INT4, lectura selectiva de pesos desde Flash; sin PSRAM según autor | ~5 tok/s y ~81 KB para motor, cifras del autor | Evidencia comunitaria, no validada |
| [Distributed AI 56 M](https://github.com/wladimiravila/esp32s3-distributed-ai) | Tres ESP32-S3, distribución de componentes y comunicación ESP-NOW | Arquitectura multi-nodo | Explorar particionado, tráfico y sincronización |
| [Cluster 7 ESP32-S3 / BitNet](https://www.reddit.com/r/esp32/comments/1vv7802/i_built_a_7node_esp32s3_cluster_to_run_a_04b_llm/) | Cluster SPI, modelo ~0,4 B y cuantización 1,58-bit declarada | Escalado por particionado de capas | Propuesta comunitaria; no validada |
| [ESP32-Tiny-LLM greenhouse assistant](https://github.com/marcelpetrick/ESP32-Tiny-LLM) | Decoder Transformer, KV cache, RoPE, GQA, INT8 y distilación | Modelo especializado reportado en ~804 KiB | Revisar código, dataset y evaluación |
| [Espressif esp-zerocode-blocks: on-device LLM](https://github.com/espressif/esp-zerocode-blocks/blob/main/docs/on-device-llm.md) | TinyStories y parser de comandos NL→JSON | Reporta 26,7 tok/s en ESP32-S31 y 17,6 tok/s en S3; parser ~270 KB y 88,8% exact match | Claims upstream; protocolo y hardware por verificar |
| [DaveBben/esp32-llm](https://github.com/DaveBben/esp32-llm) | llama2.c / ESP-DSP y uso dual-core | Optimización DSP y control de concurrencia | Inspeccionar y reproducir |
| [andrisgauracs/needle-2-esp32](https://github.com/andrisgauracs/needle-2-esp32) | Modelo ~45 M y tool calling restringido | Salida estructurada / gramática | Inspección de capacidades y licencia pendiente |

## Hipótesis y líneas de trabajo

1. **Flash-resident weights / PLE:** medir ancho de banda, patrón de acceso, latencia de lectura, cachés, coste de embeddings y output head.
2. **Flash-MoE:** cargar/consultar selectivamente expertos, comparar SRAM/PSRAM, latencia y consumo con modelos densos.
3. **Tiny Transformers:** modelos sub-MB para tareas estrechas; comparar distilación, calidad, tokenizer, contexto y recuperación.
4. **Cuantización extrema:** INT4, ternaria/BitNet y formatos de pesos compactos, con evaluación de degradación.
5. **Clusters:** estudiar distribución de capas, activaciones y KV, ESP-NOW frente a SPI y coste de comunicación.
6. **Kernels:** DSP, SIMD, multicore, Rust frente a C/C++, optimización del output head y tokenizer.
7. **Tool calling:** parsers, gramáticas restringidas, NL→JSON y controles de seguridad para acciones de firmware.
8. **Benchmark reproducible:** tokens/s, TTFT, latencia por token, energía, flash, RAM/PSRAM máxima, calidad de tarea, reproducibilidad y límites térmicos.

## Criterios de aceptación de futuras réplicas

- Identificar placa, SoC, revisión, frecuencia, Flash/PSRAM y firmware.
- Fijar repositorio, commit, licencia, modelo, tokenizer, dataset y hashes.
- Diferenciar métricas de autor, estimaciones y medidas físicas LEONES.
- Registrar RAM pico, memoria de pesos, KV cache, contexto, TTFT, throughput y energía cuando sea posible.
- Probar casos reproducibles de la tarea objetivo; la fluidez narrativa no demuestra capacidad general.
- Documentar restricciones de seguridad cuando el modelo pueda activar actuadores o herramientas.
- Aplicar HDAE: alcance, gates, artefactos, checkpoint y aceptación humana.

## Fuentes comunitarias para vigilancia

- [Reddit r/esp32: PLE, 28,9 M](https://www.reddit.com/r/esp32/comments/1v4mq5t/how_i_fit_a_289m_llm_on_an_esp32s3_9_toks_fully/)
- [Reddit r/esp32: MoE de 5,2 M](https://www.reddit.com/r/esp32/comments/1vjgbkk/i_ran_a_full_llm_model_on_an_esp32_dev_kit_v1/)
- [Reddit r/esp32projects: distribución 56 M](https://www.reddit.com/r/esp32projects/comments/1vaxdhi/a_project_that_runs_a_small_56mparameter_language/)
- [Reddit r/esp32: cluster BitNet de siete nodos](https://www.reddit.com/r/esp32/comments/1vv7802/i_built_a_7node_esp32s3_cluster_to_run_a_04b_llm/)
- [Búsqueda X: ESP32 LLM](https://x.com/search?q=ESP32%20LLM&src=typed_query)
- [Búsqueda X: ESP32-S3 TinyLLM](https://x.com/search?q=ESP32-S3%20TinyLLM&src=typed_query)
- [Búsqueda X: BitNet ESP32](https://x.com/search?q=BitNet%20ESP32&src=typed_query)
- [Búsqueda X: Per-Layer Embeddings ESP32](https://x.com/search?q=ESP32%20Per-Layer%20Embeddings&src=typed_query)

La indexación de X es irregular: estas son búsquedas de vigilancia, no publicaciones individuales verificadas.

## Actualización de prospección — 2026-11-23

**Diferencia respecto al corte inicial del 2026-11-21:** se incorporan nuevos repositorios ejecutables y una línea ARM Cortex-M; se amplían las cifras de Rust/C, se localiza una implementación de 4,4 M que funciona sin PSRAM y se documenta un stack de voz completo. Los proyectos que ya estaban en el dossier no se vuelven a catalogar salvo cuando aparece información nueva. Ninguno de estos resultados constituye una validación LEONES.

### 1. Nuevos repositorios y resultados técnicos

| Proyecto | Hardware / arquitectura | Resultados publicados por sus autores | Código, licencia y actividad | Evaluación |
|---|---|---|---|---|
| [dellisankar508/esp32-ple](https://github.com/dellisankar508/esp32-ple) | Modelo PLE de 4,41 M; ESP32-D0WD clásico (520 KB SRAM, 4 MB Flash, sin PSRAM ni SIMD), Raspberry Pi Pico 2 W (Cortex-M33) y Corstone-300 (Cortex-M55/Helium, simulado). Pesos INT4 memory-mapped/streamed desde Flash; KV int8 de 128 posiciones. | ESP32 clásico: 63 ms/token, 15,9 tok/s. Pico 2 W: 40,1 ms/token, 25 tok/s con DSP int8, DMA para el output head y Flash a 75 MHz. El modelo lee 741 KB/token; RAM de activaciones/KV ~222 KB. En Pico, int8 cambia top-1 en 1,12% de las posiciones muestreadas y PPL 5,013→5,019. Helium reduce instrucciones/token 7,7× frente a float en simulación. | MIT; código C compartido, runtime host, pruebas golden, ThreadSanitizer, kernel vectors y documentación de los tres targets. Último commit observado: 2026-10-28. | **Confianza documental alta.** Es el candidato más accionable para validar PLE, streaming Flash y portabilidad ARM. Los 25 tok/s son del Pico 2 W físico; los resultados Helium son recuentos de instrucciones en simulador, no latencias de una placa real. |
| [djObsidian/esp32-ai-idf](https://github.com/djObsidian/esp32-ai-idf) | Port ESP-IDF del PLE TinyLM de 28,9 M a ESP32-S3 N16R8; pesos INT4 en PSRAM, kernel PIE SIMD int4×int8, esp-dsp para productos escalares float y reparto dual-core. | Declara 22–31 tok/s end-to-end frente a 9,88 tok/s del runtime Arduino comparado; kernel SIMD bit-identical al escalar y comprobación de top-5/golden al arrancar. Modelo de demostración con corpus ruso de chistes. | MIT, conserva avisos del runtime upstream; último commit observado: 2026-08-09. Requiere ESP-IDF y 16 MB Flash/8 MB PSRAM. | **Confianza media.** Buen candidato para estudiar PIE SIMD, pero cifra autodeclarada, repositorio con actividad limitada y benchmark no normalizado frente a Rust/C u otros modelos. |
| [BareiroJorge/esp32-llm-commands](https://github.com/BareiroJorge/esp32-llm-commands) | Transformer especializado de ~580 K parámetros; ESP32-S3 N16R8, dos cores, PSRAM. Traduce español/inglés a un DSL fijo para GPIO, PWM, servo, frecuencia y lecturas ADC. | Exact match declarado: 98,9% inglés / 99,1% español en validación generada desde plantillas; banco manual: 30/31 inglés y 31/31 español. El modelo base ocupa ~2,2 MB. La red sólo propone intención: una tabla C independiente valida pines y operaciones antes de actuar. | MIT, con procedencia MIT conservada para el motor derivado de llama2.c/DaveBben. Último commit observado: 2026-08-17. El autor indica que el firmware español sí se probó en placa; inglés sólo en PC/compilación. | **Confianza media-alta para el patrón de seguridad; media para la calidad.** Muy útil para NL→DSL/JSON seguro, pero el 99% no mide paráfrasis abierta: las plantillas y el banco manual tienen distribución limitada. |
| [Carloscodix/qapla](https://github.com/Carloscodix/qapla) | Entrenamiento desde cero en ESP32-S3 N16R8: transformer de ~319 K, carácter a carácter, vocabulario 31, contexto 32, una capa/bloque y atención causal de una cabeza. | Entrena forward, cross-entropy, backprop manual, SGD con momentum y guarda checkpoints en Flash. La ejecución v1 documentada: 5.000 pasos y ~2 días. Gradcheck: error relativo máximo 1,07e-8; QEMU Xtensa verifica el kernel. El autor estima ~11 días para 40.000 pasos. | Apache-2.0; corpus Klingon Apache-2.0 y corpus extendido con Tatoeba CC BY 2.0 FR/atribución. Último commit observado: 2026-08-26; incluye recuperación tras reset y escrituras Flash con yield cada 64 KB. | **Confianza media en la ejecución/ingeniería; baja en capacidad lingüística.** No es un chatbot ni demuestra semántica general: la versión publicada carece de split de validación y advierte riesgo de memorización. Sí es un caso valioso de entrenamiento real en MCU. |
| [imFARSI/NanoMind-S3](https://github.com/imFARSI/NanoMind-S3) | Transformer denso Stories-15M/LLaMA-2, 15,206 M parámetros, 6 capas, vocabulario 32 K, contexto 256; ESP32-S3 N16R8. INT4, Flash MMU y KV/activaciones en PSRAM. | Modelo INT4 de 7,49 MB, KV cache declarado de 3,54 MB y tokenizer ~150 KB; ~2,96 tok/s en el ejemplo publicado. Dos cores LX7 a 240 MHz. | MIT; último commit observado: 2026-08-07. Incluye firmware y exportador, pero la evidencia pública revisada se apoya principalmente en README/demo. | **Confianza media-baja.** Interesante como baseline denso frente a PLE; faltan gates de paridad y evaluación de calidad comparables a esp32-ple. |
| [iamankushpandit/esp_ai](https://github.com/iamankushpandit/esp_ai) | Asistente de voz local completo en ESP32-S3 FNK0104B: WakeNet, Conformer STT, LLM Q4, SVOX Pico TTS, pantalla, micrófono/altavoz y SD. STT y LLM se ejecutan en fases separadas para reutilizar 8 MB de PSRAM. | TinyTalk v8 de 19,7 M: 5,4–5,9 tok/s; GGUF delphi 6,4 M: 7,3 tok/s; stories260K: 30 tok/s. STT: 2,7–4,6 s para 1,4–2,9 s de audio; turno hablado ~6–9 s. Declara 99,2% en formulaciones vistas frente a 63,3% en paráfrasis. | Código GPL-3.0-or-later. El README declara Conformer STT Apache-2.0 y pesos CC-BY-4.0, SVOX Apache-2.0 y componentes MIT/Espressif; algunos pesos/datasets heredan restricciones no comerciales. Último commit observado: 2026-11-09. | **Confianza media-alta como integración demostrable; media en las cifras de calidad.** El resultado más completo de voz local, pero revisar licencias de cada artefacto y la brecha de generalización antes de uso de producto. |
| [Low-Zi-Hong/ESP32s3-LLM-Cluster](https://github.com/Low-Zi-Hong/ESP32s3-LLM-Cluster) | Un maestro + seis nodos ESP32-S3 N16R8; Qwen2-0.5B base, vocabulario podado a ~386 M parámetros, pesos ternarios 1,58-bit; pipeline por capas sobre SPI daisy-chain. | Autor declara ~0,11 tok/s (~9 s/token) y reconoce que el modelo de ejemplo está muy sobreajustado. Es una prueba de particionado, no un asistente práctico. | MIT; último commit observado: 2026-10-08. Incluye scripts de empaquetado/firmware y guía de cableado. | **Confianza baja-media.** Repositorio útil para estudiar particionado SPI, pero rendimiento y calidad limitan su prioridad. No confundir capacidad total distribuida con velocidad útil. |
| [lspr98/conformer-stt-s3](https://github.com/lspr98/conformer-stt-s3) | Conformer CTC de 13,1 M parámetros, destilado y cuantizado desde NVIDIA stt_en_conformer_ctc_small; ESP32-S3, 256 KB SRAM + 4 MB PSRAM + 14 MB Flash. | WER publicado por subconjunto; para 8,28 s de audio declara 13,39 s de inferencia en DevKitC-1 y 13,66 s en XIAO S3 Plus. No es tiempo real. Usa SIMD int8, alineación de 16 bytes, fusión de operadores y dos cores. | Apache-2.0 para el repositorio; último commit observado: 2026-07-19. | **Confianza media.** Referencia sólida de distilación/ASR y pipeline de voz, no un LLM generativo. Hay que revisar la licencia del checkpoint/pesos por separado. |

### 2. Actualizaciones sobre proyectos ya archivados

- **Rust frente a C — [Bellman281/esp32-tinyLLM](https://github.com/Bellman281/esp32-tinyLLM):** el README actual detalla 8,20 tok/s en C y 10,50 tok/s en Rust, un 28,2% más, con salida byte-identical; --fast-mspi declara 10,89 tok/s, pero depende de un ajuste experimental de bus a 120 MHz que el autor no recomienda como configuración normal por sensibilidad térmica. Hay 16 ficheros de test y 38 tests descritos; último commit observado 2026-08-20. Código Apache-2.0, con componentes vendorizados MIT. La comparación es valiosa porque mantiene placa/modelo y exige paridad, aunque sigue siendo evidencia del autor.
- **Distribución ESP-NOW — [wladimiravila/esp32s3-distributed-ai](https://github.com/wladimiravila/esp32s3-distributed-ai):** la descripción técnica comunitaria detalla fragmentación de mensajes en bloques de 246 bytes útiles, secuencia/ACK y reensamblado de embeddings de ~3,6 KB en ~15 fragmentos. El autor reconoce que todavía no implementa retransmisión automática ante pérdida. Esto debe tratarse como riesgo de fiabilidad, no como un detalle menor.
- **Cluster SPI ternario:** ahora hay un repositorio MIT concreto para el caso de siete nodos; el dato útil es la contrapartida: 1,58-bit permite alojar ~386 M parámetros, pero el throughput publicado cae a ~0,11 tok/s.
- **MoE desde Flash:** no se encontró en este corte una implementación nueva con evaluación reproducible que supere el caso comunitario ya archivado de 5,2 M/16 expertos/INT4. Sigue siendo una hipótesis prioritaria, no una capacidad confirmada.
- **Espressif esp-zerocode-blocks:** se mantiene el resultado previamente archivado de esp-tinylm (26,7 tok/s S31 / 17,6 tok/s S3) y parser NL→JSON de 270 KB con 88,8% exact match. No se ha reejecutado en esta campaña.

### 3. Papers y literatura técnica

- [Deeploy — arXiv:2408.04413](https://arxiv.org/abs/2408.04413): compilación de SLMs para MCU heterogéneos RISC-V con extensiones y NPU; reporta 340 tok/s y 490 µJ/token en TinyStories sin memoria externa. No es ESP32 ni comparable directamente: sirve como referencia de co-diseño y techo de hardware especializado.
- [CHIMERA — arXiv:2606.02358](https://arxiv.org/abs/2606.02358): propuesta de AI-MCU en 22 nm con nueve cores RV32, acelerador Transformer y subsistema L2 compartido; declara 3,1 TOPS/W y 563 Gb/s agregados. Es arquitectura de investigación, no una placa de desarrollo disponible para réplica inmediata.
- [TinyVLM — arXiv:2603.00136](https://arxiv.org/abs/2603.00136): detección zero-shot en MCU mediante destilación vision-language, Matryoshka embeddings y almacenamiento cuantizado de prototipos en Flash, con presupuesto inferior a 1 MB. No es un LLM generativo, pero sí una línea relevante para IA multimodal embebida.
- [Systematic review: Language and Transformer Models with ESP32-class Microcontrollers](https://jurnal.unpad.ac.id/ijmt/article/view/72405/0): revisión PRISMA de 2026 que separa despliegue cloud-assisted, edge-assisted y totalmente residente. Su conclusión coincide con la lectura de este dossier: no se demuestra un LLM conversacional generalista ejecutándose íntegramente en ESP32; los resultados son modelos especializados y tareas acotadas. Es una fuente secundaria; la calidad editorial debe evaluarse antes de usarla como referencia fuerte.

### 4. X.com y Reddit: cobertura y límites

Reddit aporta las pistas comunitarias enlazadas arriba: 4,4 M PLE, TinyLM de 28,9 M, 15,2 M denso, 56 M distribuido, cluster ternario, transformer de comandos de ~582 K y entrenamiento desde cero en el propio S3. Se priorizaron los repositorios enlazados por los autores frente a los posts.

La búsqueda indexada de X.com no devolvió publicaciones individuales que pudiera atribuir con seguridad a autor/fecha y enlazar como evidencia primaria. Se mantienen búsquedas reproducibles, no citas de posts:
- [ESP32 + LLM](https://x.com/search?q=%22ESP32%22%20%22LLM%22&src=typed_query)
- [ESP32-S3 + BitNet](https://x.com/search?q=%22ESP32-S3%22%20%22BitNet%22&src=typed_query)
- [Per-Layer Embeddings + ESP32](https://x.com/search?q=%22Per-Layer%20Embeddings%22%20ESP32&src=typed_query)

### 5. Lectura técnica consolidada

1. **La jerarquía de memoria manda más que el número bruto de parámetros.** PLE deja la tabla dispersa en Flash; el output head secuencial puede ser el verdadero cuello de botella. esp32-ple cuantifica 741 KB/token y demuestra que el modelo puede ejecutarse incluso sin PSRAM en un ESP32 clásico.
2. **La vía ARM ya tiene evidencia ejecutable.** Cortex-M33 DSP y DMA alcanzan 25 tok/s en Pico 2 W; M55/Helium está verificado bit a bit en simulación, pero aún falta una placa M55 física con latencias/energía.
3. **INT4 en pesos + activaciones int8** parece el equilibrio más transferible. La calidad del modelo PLE en Pico cambia poco según sus pruebas; el coste real debe medirse por capa y con golden logits.
4. **El tamaño no equivale a capacidad.** 28,9 M PLE y 15,2 M denso siguen siendo modelos TinyStories de continuación narrativa; el 580 K de comandos funciona precisamente por especialización de dominio.
5. **Para actuar sobre hardware, el modelo no debe tener autoridad de seguridad.** El patrón de esp32-llm-commands —modelo → DSL fijo → validador determinista → periférico— es preferible a ejecutar directamente JSON libre o llamadas de herramienta generadas.
6. **MoE/Flash y clusters siguen sin prueba de utilidad práctica suficiente.** Más parámetros repartidos no compensan automáticamente el tráfico de activaciones, la latencia entre nodos, fragmentación, reintentos y sincronización.
7. **La voz completa es posible, pero con latencia y presupuesto de memoria estrictos.** esp_ai alterna STT y LLM para reutilizar arenas; el Conformer separado confirma que transcribir audio sigue siendo más lento que tiempo real en estas placas.

### 6. Recomendaciones de experimentos LEONES

| Prioridad | Experimento | Qué debe medir | Criterio de aceptación |
|---|---|---|---|
| P0 | Replicar esp32-ple en ESP32-D0WD y/o Pico 2 W | Flash bytes/token, ancho de banda, latencia por etapa, KV, RAM pico, energía, tokens/s y hash de salida | Golden match; repetir al menos 3 veces con misma build/modelo; separar tiempo físico de instrucciones simuladas |
| P1 | Comparar kernels scalar C, DSP M33 y Helium M55 con el mismo modelo y vectores | ciclos/instrucciones, throughput, top-1/PPL, efectos de FMA/redondeo y coste de cuantizar activaciones | 42/42 vectores bit-exact; mismo golden; no presentar QEMU/FVP como medición de latencia |
| P1 | Replicar esp32-ai-idf PIE SIMD frente a C/Rust en S3 | ms/token por etapa, throughput end-to-end, tráfico PSRAM, uso de dos cores, tamaño binario | Igual modelo, prompt, contexto y sampling; top-5/logit parity; no aceptar comparaciones con corpus/modelos distintos |
| P1 | Probar esp32-llm-commands en español | Exact match fuera de plantillas, paráfrasis, negaciones, pines inválidos, conflictos de actuadores, secuencias y rechazos | El validador C debe bloquear siempre pines/acciones no permitidos, incluso con salida malformada o adversarial |
| P2 | Comparar NanoMind denso vs PLE con tarea TinyStories común | bytes leídos/token, PSRAM/Flash, KV, TTFT, tokens/s, PPL y repetición | Mismo tokenizer, corpus, contexto y protocolo; registrar diferencias de calidad, no sólo velocidad |
| P2 | Evaluar esp_ai + Conformer como pipeline de voz | RTF de STT, latencia de turno, picos de PSRAM, batería/energía, WER y exactitud de respuestas/paráfrasis | Fases de memoria sin solapamiento accidental; reproducir con audio fijo y registrar licencias de cada modelo |
| P2 | Instrumentar cluster SPI/ESP-NOW | bytes/activación, latencia por salto, pérdida, reintentos, colas, backpressure, tokens/s y energía total | Protocolo tolerante a pérdida y comparación frente a una sola placa; descartar claims de capacidad sin throughput útil |
| P2 | Reproducir Qapla con validación holdout y cortes de alimentación | gradcheck, curva train/val, recuperación, Flash writes, duración y calidad de generación | No aceptar pérdida de entrenamiento como prueba de generalización |

**Estado de evidencia LEONES:** cero reproducciones físicas nuevas en esta actualización. Los números de las tablas son claims externos o tests publicados por sus autores; no se deben introducir en el catálogo de benchmarks LEONES como resultados propios.

## Próximos pasos

- [ ] Priorizar esp32-ple como referencia ARM/Flash y preparar una campaña reproducible con golden files.
- [ ] Fijar commits y hashes de modelo/tokenizer antes de cualquier réplica.
- [ ] Hacer una comparación C/Rust/PIE SIMD sólo con modelo y protocolo idénticos.
- [ ] Añadir un gate de seguridad NL→DSL con casos adversariales en español.
- [ ] Mantener MoE Flash y clusters como líneas exploratorias hasta tener trazas de tráfico, fiabilidad y rendimiento.
- [ ] Mantener separadas las mediciones físicas LEONES, los tests de los autores y las cifras de simuladores.

## Próximos pasos

- [ ] Inspección recursiva y fijado de commits/licencias de cada repositorio.
- [ ] Matriz hardware-modelo-arquitectura y memoria.
- [ ] Protocolo común de benchmark y checklist de evidencia.
- [ ] Seleccionar dos experimentos: PLE single-node y MoE Flash.
- [ ] Evaluar cluster distribuido sólo tras obtener mediciones de tráfico y latencia.
- [ ] Automatizar prospección y actualización del catálogo mediante GitHub Actions/PR.

