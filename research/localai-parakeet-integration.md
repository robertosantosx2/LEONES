# LocalAI y Parakeet.cpp: evaluación de integración en LEONES

**Estado:** investigación preliminar — 2026-11-05  
**Tipo:** arquitectura / motores de inferencia / audio  
**Decisión propuesta:** evaluar LocalAI como proveedor experimental de servicios de audio y Parakeet.cpp como motor ASR prioritario. No incorporar aún LocalAI como dependencia obligatoria de ODS.

## 1. Resumen ejecutivo

LocalAI es una plataforma de inferencia local que ofrece APIs compatibles con OpenAI y abstrae distintos motores y modelos. Puede ayudar a LEONES a incorporar capacidades de audio sin implementar de inmediato cada backend y servicio de gestión.

La oportunidad más concreta identificada es **Parakeet.cpp**, implementación C++ basada en ggml de modelos NVIDIA NeMo Parakeet. Es un candidato para reconocimiento de voz local (ASR), con opciones de CPU/GPU y una ruta de ejecución sin Python durante la inferencia.

La recomendación es realizar una prueba reproducible en el MSI Thin 15 B12UC del proyecto y comparar:
1. Parakeet.cpp directamente.
2. Parakeet mediante LocalAI.
3. Alternativas como Whisper.cpp y Moonshine.

La investigación no equivale a una validación ejecutada en el hardware: las cifras de rendimiento, consumo y precisión deberán medirse.

## 2. LocalAI

### Qué aporta
- Servidor de inferencia local y API HTTP.
- Compatibilidad con endpoints de estilo OpenAI, incluidos endpoints de audio según backend.
- Gestión de modelos y configuración.
- Integración de distintos motores y modalidades: LLM, audio, imagen y otras capacidades, dependiendo de backend/modelo.
- Despliegue como servicio, incluido Docker.
- Posibilidad de experimentar con backends especializados sin integrarlos directamente en ODS.

### Papel propuesto en LEONES
LocalAI se considera **capa opcional de experimentación/proveedor**, no reemplazo de ODS, Hermes, TensorFold ni del router de LEONES.

ODS debe mantener el control de routing, selección de proveedor, políticas, telemetría y exposición a clientes. El servicio LocalAI, si se adopta, quedaría detrás de una interfaz de proveedor intercambiable.

## 3. Parakeet.cpp

Repositorio: https://github.com/mudler/parakeet.cpp

Parakeet.cpp es una implementación C++ de modelos NVIDIA NeMo Parakeet utilizando ggml. El proyecto declara soporte de inferencia CPU y GPU, modelos en formatos preparados para su runtime y herramientas de procesamiento de audio. La disponibilidad exacta de cada función depende de la arquitectura, modelo y versión.

### Capacidades a investigar
- **ASR / transcripción:** convertir audio en texto.
- **Timestamps:** marcas temporales, incluida granularidad por palabra cuando el modelo/runtime lo admite.
- **Streaming:** transcripción incremental; medir latencia real de extremo a extremo.
- **VAD:** detección de actividad de voz.
- **Diarización:** segmentación/diferenciación de hablantes, según pipeline.
- **Speaker embeddings:** representaciones de voz; requieren cautela y consentimiento si se usan para identificación.
- **Sound-event detection:** detección/clasificación de eventos acústicos no verbales, si está soportada por el modelo/pipeline.
- **Multilingüismo:** comprobar idiomas y variantes concretas del modelo seleccionado.

No se debe asumir que todas las capacidades están presentes simultáneamente en una única variante de Parakeet o que la diarización implica identificación de personas.

## 4. Modelos candidatos

| Candidato | Uso previsto | Nota |
|---|---|---|
| Parakeet TDT/CTC compacto (~110M) | ASR auxiliar de bajo coste | Prioridad para primera prueba |
| Parakeet TDT v3 (~0.6B) | Mayor calidad / evaluación multilingüe | Medir memoria, latencia y precisión |
| Variantes Parakeet Nemotron | Streaming / idiomas y capacidades específicas | Verificar disponibilidad y soporte en parakeet.cpp |
| Variantes compactas/Redux | Investigar footprint reducido | Validar compatibilidad antes de elegir |

Los tamaños de archivo dependen del checkpoint, formato y cuantización. El tamaño de los pesos no representa por sí solo RAM o VRAM pico.

## 5. Hardware objetivo y restricciones

Hardware de referencia registrado en LEONES:
- MSI Thin 15 B12UC
- Intel Core i7-12650H
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM
- Ubuntu
- Stack local con ODS, llama.cpp y TensorFold

### Hipótesis
- Un modelo ASR compacto podría funcionar como servicio auxiliar persistente.
- Parakeet podría ejecutarse en CPU cuando la GPU esté ocupada por TensorFold.
- La inferencia de audio podría coexistir con el LLM, pero debe medirse la presión combinada de RAM/VRAM, latencia y swap.
- No reservar VRAM ni modificar el servicio llama-server/ODS por defecto durante la prueba.
- Probar primero procesos aislados; luego concurrencia controlada.

## 6. Integración propuesta

### Arquitectura lógica

```text
LEONES UI / Voice / Applications
              |
           ODS Router
              |
       Audio Provider API
              |
     +--------+---------+
     |                  |
 Parakeet.cpp       LocalAI
 (direct/native)   (experimental)
     |                  |
     +---- ASR / VAD / Audio pipelines
```

### Estrategias

| Estrategia | Ventajas | Costes / riesgos |
|---|---|---|
| A. LocalAI como servicio Docker | Prototipado rápido, gestión y API existente | Servicio adicional, configuración y recursos |
| B. Parakeet.cpp como servicio independiente | Menor superficie, control directo | Implementar API, lifecycle y observabilidad |
| C. Integrar biblioteca/runtime en servicio LEONES | Integración y control potencialmente mejores | Mayor esfuerzo, mantenimiento y acoplamiento |

**Secuencia recomendada:** empezar por A para validar la API y el pipeline; comparar con B; decidir si C tiene justificación basada en resultados. Mantener la API de proveedor desacoplada para poder sustituir backend.

## 7. API y posible configuración ODS

LocalAI documenta una API de transcripción de audio de estilo OpenAI, por ejemplo:

```bash
curl http://localhost:8080/v1/audio/transcriptions \
  -F file="@audio.wav" \
  -F model="parakeet-110m"
```

Ejemplo de solicitud de granularidad temporal por palabra (la sintaxis y soporte deben verificarse con la versión desplegada):

```bash
curl http://localhost:8080/v1/audio/transcriptions \
  -F file="@audio.wav" \
  -F model="parakeet-110m" \
  -F "timestamp_granularities[]=word"
```

Propuesta conceptual (no es configuración existente ni validada de ODS):

```yaml
audio:
  transcription:
    provider: localai
    base_url: http://local-ai:8080/v1
    model: parakeet-110m
  capabilities:
    timestamps: true
    streaming: experimental
    vad: optional
    diarization: optional
```

ODS debería exponer una operación de transcripción independiente del backend. La selección de motor puede considerar latencia, idioma, calidad, disponibilidad, hardware y coste de recursos.

## 8. Posibles aplicaciones LEONES

### LEONES Voice
1. Captura de micrófono.
2. VAD para detectar inicio/fin de voz.
3. Transcripción con Parakeet.
4. Envío de texto a ODS/Hermes/TensorFold.
5. Generación de respuesta.
6. TTS local.
7. Reproducción y continuación de conversación.

### Otras aplicaciones
- Dictado local y accesibilidad.
- Transcripción de reuniones y grabaciones.
- Subtítulos SRT/VTT.
- Timestamps y búsqueda en grabaciones.
- Segmentación de hablantes.
- Indexación de audio para RAG.
- Clasificación de eventos acústicos y alarmas.

## 9. Ecosistema LocalAI que merece una revisión adicional

| Proyecto/backend | Área | Evaluación propuesta |
|---|---|---|
| parakeet.cpp | ASR / audio | Prioridad alta |
| moss-transcribe.cpp | Transcripción y diarización | Comparar calidad y footprint |
| moss-tts.cpp | Síntesis de voz | Revisar licencias, calidad y requisitos |
| magpie-tts.cpp | TTS / voces multilingües | Evaluar idiomas y latencia |
| ced.cpp | Clasificación de eventos acústicos | Potencial para audio ambiental |
| vllm.cpp | Inferencia de LLM | Investigar; no asumir que sustituye motores ya integrados |

Cada componente y cada peso de modelo requiere revisión independiente de compatibilidad, mantenimiento, licencia y requisitos de hardware. No asumir que todos forman parte de una versión estable de LocalAI.

## 10. Plan de benchmark

### Fase 1 — Smoke tests
- Compilar/instalar Parakeet.cpp y registrar versión, commit, flags y dependencias.
- Descargar modelos candidatos desde fuentes oficiales.
- Ejecutar transcripción de muestras cortas en CPU.
- Confirmar salida, idioma, timestamps y manejo de errores.

### Fase 2 — Hardware
Para cada modelo/formato:
- CPU vs CUDA.
- Tiempo de carga y primera inferencia.
- Tiempo total y real-time factor (RTF).
- Latencia inicial y streaming (si disponible).
- RAM pico, VRAM pico, temperatura y potencia.
- Duración del audio y throughput.
- Efecto de concurrencia y estabilidad.

### Fase 3 — Calidad
- Corpus de español e inglés con licencia adecuada.
- Audio limpio, ruido, varios hablantes y grabaciones largas.
- WER/CER, normalización, puntuación y manejo de nombres propios.
- Documentar idioma/modelo y condiciones; no comparar métricas incompatibles.

### Fase 4 — Comparación
- Parakeet.cpp vs Whisper.cpp vs Moonshine.
- Parakeet.cpp directo vs LocalAI como wrapper.
- GPU dedicada vs CPU cuando TensorFold ocupa VRAM.
- Evaluar diarización/VAD por separado del WER de ASR.

### Fase 5 — Integración ODS
- Crear proveedor audio.transcription.
- Añadir health check, timeout, cancelación y límites de tamaño/duración.
- Definir respuesta normalizada (texto, idioma, segmentos, timestamps, metadatos).
- Añadir observabilidad sin registrar audio ni contenido sensible por defecto.
- Probar integración con Hermes/Open WebUI y futura LEONES Voice.

## 11. Riesgos, privacidad y licencias

- **VRAM compartida:** ASR y TensorFold pueden competir por 4 GiB; definir modo CPU y límites.
- **RAM y swap:** evitar procesos concurrentes que provoquen swapping; monitorizar PSI y memoria.
- **Streaming:** verificar latencia real y cancelación, no inferirla de la existencia de una API.
- **Diarización:** separar “speaker 1/2” de identificación biométrica de una persona.
- **Datos de voz:** el audio y embeddings pueden ser sensibles; consentimiento, retención mínima y controles explícitos.
- **Licencias:** revisar licencia de código, pesos y datasets por separado antes de distribuir.
- **Compatibilidad:** fijar versiones/commits y no depender de capacidades de documentación “latest” sin pruebas.
- **Seguridad:** endpoint local autenticado o aislado; validar formatos, tamaño y duración del audio.

## 12. Decisión preliminar

**GO para benchmark e integración experimental.**  
**NO-GO todavía para dependencia de producción o cambio de arquitectura por defecto.**

Criterios para avanzar:
1. Calidad suficiente en español e inglés.
2. RTF/latencia apropiados para el caso de uso.
3. Footprint compatible con el MSI y con el stack activo.
4. API estable y fácil de integrar en ODS.
5. Licencias compatibles con los objetivos de LEONES.
6. Resultados reproducibles y artefactos archivados.

## 13. Fuentes

- LocalAI — sitio: https://localai.io/
- LocalAI — documentación: https://localai.io/docs/
- LocalAI — Audio to Text: https://localai.io/docs/features/audio-to-text/
- LocalAI — repositorio: https://github.com/mudler/LocalAI
- Parakeet.cpp: https://github.com/mudler/parakeet.cpp
- NVIDIA NeMo: https://github.com/NVIDIA/NeMo
- Whisper.cpp (comparador): https://github.com/ggml-org/whisper.cpp
- Moonshine (comparador): https://github.com/usefulsensors/moonshine

---
*Documento de investigación. Las recomendaciones son hipótesis de arquitectura hasta que se complete el benchmark local.*
