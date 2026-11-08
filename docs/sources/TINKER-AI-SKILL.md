# Tinker AI Skill — especialización de modelos mediante LoRA

- **Fuente primaria:** [drost-ai/tinker-ai-skill](https://github.com/drost-ai/tinker-ai-skill)
- **Autor indicado por el proyecto:** Migel Tissera.
- **Licencia del skill:** MIT (según su README y metadatos).
- **Servicio de entrenamiento:** [Tinker — Thinking Machines Lab](https://thinkingmachines.ai/tinker/)
- **Documentación:** [Tinker Docs](https://tinker-docs.thinkingmachines.ai/) · [Modelos y precios](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/)
- **Versión revisada:** rama `main`, contenido consultado el 2026-11-08; el repositorio no fija aquí un tag de release.
- **Clasificación LEONES:** `research-candidate` (metodología y herramienta documental; no es un runtime local ni una medición).
- **Próximo gate:** reproducir el pipeline con un dataset de prueba no sensible, verificar disponibilidad/precio del modelo elegido y evaluar un primer adaptador exportado.

## 1. Qué es

Tinker AI Skill es una habilidad para agentes de programación (Agent Skills) que guía un flujo reproducible para convertir sesiones reales de trabajo con un agente en un dataset de *supervised fine-tuning* (SFT), entrenar un adaptador **LoRA** sobre un modelo de pesos abiertos mediante el servicio remoto Tinker, evaluar checkpoints y exportar un modelo utilizable fuera del servicio.

No es un modelo nuevo ni un motor de inferencia. Es una receta operativa: instrucciones `SKILL.md`, scripts Python/shell y notas técnicas para recopilar, normalizar, anonimizar, segmentar, entrenar, evaluar, fusionar y cuantizar.

El autor presenta la metodología como la utilizada para producir los modelos Tess-4 y Tess-4.5. Esa procedencia es una afirmación del proyecto; LEONES no ha reproducido todavía esos entrenamientos.

## 2. Qué aporta

La contribución útil no es simplemente «entrenar un LoRA», sino resolver problemas prácticos que suelen degradar los modelos especializados:

- **Datos reales de trabajo:** aprovecha trazas de conversaciones, decisiones, llamadas a herramientas y resultados, en vez de depender solo de ejemplos genéricos.
- **Normalización:** transforma transcripciones de Claude Code JSONL a mensajes estructurados compatibles con el pipeline de entrenamiento.
- **Privacidad:** sustituye credenciales y datos identificativos; genera identidades ficticias distintas por sesión y falla si detecta valores sensibles conocidos que sobreviven.
- **Segmentación consciente del modelo:** cuenta tokens con el tokenizer/renderer real del modelo; no corta una llamada a herramienta de su resultado.
- **Continuidad:** añade contexto de trabajo y un puente de continuación cuando una sesión larga se divide en ventanas.
- **Reproducibilidad:** separa sesiones completas para validación con una semilla estable y registra hashes/procedencia del dataset.
- **Entrenamiento controlado:** hace primero una prueba local sin coste, muestra tokens/configuración y requiere `--train` para lanzar el trabajo remoto.
- **Evaluación de comportamiento:** compara modelo base y checkpoints con los mismos prompts; no selecciona solo por una curva de loss.
- **Salida local:** permite descargar el checkpoint LoRA, fusionarlo con el modelo base, convertirlo a GGUF y servirlo con llama.cpp.

## 3. Arquitectura: qué ocurre dónde

```text
MSI / estación de trabajo
  ├─ recopilar y preparar ejemplos
  ├─ anonimizar y revisar datos
  ├─ construir dataset + split train/validation
  ├─ smoke test offline y estimación de tokens
  └─ cliente Python / API
            │
            ▼
     Tinker (GPU remota)
       ├─ LoRA SFT
       ├─ checkpoints
       └─ sampling / evaluación
            │
            ▼
     descargar adaptador elegido
            │
            ▼
     fusionar con modelo base
            │
            ▼
     Hugging Face → GGUF → cuantización
            │
            ▼
     llama.cpp / runtime local
            │
            ▼
     benchmark funcional LEONES
```

Tinker es un servicio de entrenamiento distribuido: el cliente y la preparación de datos pueden ejecutarse en una máquina CPU-only; Tinker ejecuta el trabajo de gradientes/optimización en sus GPU remotas. La API expone operaciones como `forward_backward`, `optim_step`, `sample` y guardado de estado. El método documentado aquí utiliza LoRA, no *full fine-tuning*.

**Consecuencia para LEONES:** los 4 GiB de VRAM de la RTX 3050 no son el límite del entrenamiento remoto. Sí importan al ejecutar y medir el GGUF final. La fusión/exportación y conversión también consumen disco, RAM y tiempo local; deben tratarse como fases separadas del entrenamiento.

## 4. Cómo crear modelos pequeños especializados

La regla de diseño es especializar primero el **comportamiento**, no intentar memorizar toda una enciclopedia:

- enseñar formato de salida, criterios, estilo técnico, secuencias de diagnóstico y uso de herramientas;
- mantener datos cambiantes (versiones, precios, catálogo de modelos, compatibilidad recién publicada) en documentación/RAG o fuentes consultables;
- entrenar con ejemplos representativos, correctos y autorizados;
- incluir contraejemplos y casos límite;
- reservar sesiones/documentos completos para validación, evitando que fragmentos casi duplicados aparezcan en train y validation.

### Receta práctica

1. **Definir una tarea estrecha.** Una entrada y una salida observables: por ejemplo, «clasificar un fallo CUDA y proponer los siguientes comandos de diagnóstico», no «saber toda la informática».
2. **Crear el contrato de respuesta.** Prompt de sistema, esquema JSON si procede, límites de seguridad, herramientas disponibles y ejemplos de salida correcta.
3. **Construir ejemplos supervisados.** Cada ejemplo debe contener contexto suficiente, petición, respuesta ideal y, si aplica, llamada a herramienta más resultado. Para conocimiento documental, incluir fuente/fecha y evitar entrenar hechos efímeros como si fueran permanentes.
4. **Limpiar y anonimizar.** Eliminar API keys, tokens, rutas privadas, nombres, datos de clientes y fragmentos que no se tenga permiso para usar. La anonimización automática no sustituye la revisión humana.
5. **Normalizar y renderizar para el modelo elegido.** Rehacer el dataset si cambia el tokenizer, renderer, modelo, prompt o definición de herramientas.
6. **Separar train/validation por sesión, proyecto o documento de origen.** No dividir aleatoriamente mensajes casi idénticos.
7. **Ejecutar el smoke test offline.** Inspeccionar ejemplos decodificados, conteo real de tokens, solapamiento, configuración y coste previsto.
8. **Entrenar LoRA en Tinker solo tras aprobar el presupuesto.** Los scripts de entrenamiento, sampling y exportación pueden generar costes; confirmar precios y estimación actual antes de lanzar.
9. **Comparar base y checkpoints.** Mismo conjunto de pruebas, mismas plantillas y parámetros. Medir exactitud de tarea, cumplimiento de formato, errores peligrosos, llamadas a herramientas y regresiones.
10. **Exportar el checkpoint elegido.** Fusionar con el modelo base o conservar un adaptador PEFT cuando el runtime lo soporte; convertir a GGUF y cuantizar si se usará llama.cpp.
11. **Validar en el hardware objetivo.** Ejecutar un benchmark LEONES con identidad exacta del modelo, hash, cuantización, runtime, contexto, configuración, RAM/VRAM, latencia, tokens/s y score funcional.

## 5. Modelos de partida: qué elegir y por qué

La disponibilidad de modelos en Tinker cambia. La tabla de Tinker consultada el 2026-11-08 incluye Qwen3.5-4B, Qwen3.5-9B, Qwen3-8B y modelos mayores. El catálogo/API debe comprobarse justo antes de entrenar; no asumir que un modelo de Hugging Face está soportado por Tinker.

| Candidato | Uso recomendado | Consideración para LEONES |
|---|---|---|
| **Qwen3.5-4B** | Primer especialista generalista: asistente técnico en español, clasificación, extracción estructurada, soporte de repositorio o diagnóstico guiado. | **Punto de partida recomendado.** Es el candidato más pequeño de la lista Tinker revisada y el más razonable para exportar y probar en el MSI con cuantización y offload si hace falta. |
| **Qwen3-8B** | Especialista que necesita más capacidad de razonamiento/código o instrucciones más complejas. | Segunda etapa; mayor coste y presión de memoria local. No empezar aquí sin demostrar que 4B se queda corto. |
| **Qwen3.5-9B** | Especialista con tareas más variadas, contexto multimodal o mayor margen de capacidad. | Escalar solo si el benchmark demuestra una limitación concreta de 4B/8B; su despliegue local será más exigente. |
| **Qwen3.6-35B-A3B** | Experimento MoE de mayor capacidad, cuando se necesite comparar un modelo grande con solo 3B parámetros activos por token. | No es un modelo pequeño: tiene 35B parámetros totales. No confundir parámetros activos con tamaño de pesos que hay que almacenar. |

**Recomendación inicial:** empezar con **Qwen3.5-4B**, un único dominio y un conjunto de evaluación pequeño pero representativo. El catálogo Tinker consultado no incluye un Qwen de 0.6B o 2B para este flujo; no se debe prometer que el skill pueda entrenar cualquier modelo arbitrario. Si el objetivo obligatorio es un modelo de 0.6B–2B, habrá que elegir una herramienta de fine-tuning local/alternativa cuyo catálogo admita ese modelo, o esperar a que Tinker lo soporte.

Para inferencia local en el MSI (RTX 3050 Laptop 4 GiB VRAM, 14 GiB RAM), priorizar GGUF Q4, contexto moderado y offload CPU/GPU medido. Qwen3.5-4B es una **hipótesis de candidato**, no una garantía de que cualquier configuración quepa íntegramente en VRAM ni de que alcance una velocidad concreta. La medición debe hacerse con el runtime y el contexto previstos.

## 6. Especialistas concretos que LEONES podría construir

### A. Especialista de diagnóstico Ubuntu + CUDA + llama.cpp

- **Base inicial:** Qwen3.5-4B.
- **Datos:** incidencias reales anonimizadas, logs, causa raíz confirmada, comandos de diagnóstico y resolución verificada.
- **Aprendizaje deseado:** pedir la evidencia que falta, proponer comandos seguros, interpretar resultados y separar hipótesis de hechos.
- **Pruebas:** fallos CUDA, OOM, compilación, bibliotecas, offload, memoria y regresiones.
- **Criterio de éxito:** diagnóstico correcto y reproducible; no inventar que un comando se ejecutó.

### B. Especialista LEONES de selección y evaluación de modelos

- **Base inicial:** Qwen3.5-4B.
- **Datos:** casos hardware/modelo/runtime con RAM, VRAM, cuantización, contexto, licencia, compatibilidad y resultados.
- **Aprendizaje deseado:** producir recomendaciones estructuradas y respetar los estados `ESTIMATED`, `VERIFIED` y `MEASURED`.
- **Pruebas:** casos con memoria insuficiente, datos incompletos y diferencias entre parámetros totales y activos.
- **Criterio de éxito:** no convertir estimaciones externas en mediciones LEONES y abstenerse cuando falten datos.

### C. Especialista de mantenimiento del código LEONES

- **Base inicial:** Qwen3.5-4B; comparar con Qwen3-8B si la evaluación revela fallos de razonamiento/código.
- **Datos:** sesiones de desarrollo autorizadas, issues, diffs, tests, revisiones y resolución final.
- **Aprendizaje deseado:** seguir convenciones del repositorio, localizar archivos, proponer cambios acotados y acompañarlos de pruebas.
- **Pruebas:** tareas retenidas por issue/PR, tests de regresión y revisión humana del diff.
- **Criterio de éxito:** cambios correctos, pequeños, probados y sin inventar resultados de ejecución.

### D. Especialista de documentación técnica en español

- **Base inicial:** Qwen3.5-4B.
- **Datos:** documentación aprobada, ejemplos de fichas LEONES, informes y pares borrador→documento aceptado.
- **Aprendizaje deseado:** mantener estructura, terminología, trazabilidad y separación fuente/evidencia/estimación/medición.
- **Pruebas:** documentos no vistos, citas, enlaces, consistencia y detección de afirmaciones sin soporte.

Estos son diseños propuestos; no existen todavía modelos entrenados ni resultados medidos por LEONES para estos especialistas.

## 7. El flujo del repositorio de referencia

El skill contiene nueve etapas y scripts dedicados:

| Etapa | Scripts / resultado |
|---|---|
| Recopilar | `collect_sessions.py`: copia sesiones principales y manifiesto con SHA-256. |
| Normalizar | `normalize_sessions.py`: convierte JSONL de Claude Code a mensajes estructurados. |
| Anonimizar | `anonymize_sessions.py`: sustituye secretos e identidad; exige revisión humana. |
| Construir dataset | `build_dataset.py`: segmentación por tokenizer/renderer, contexto de continuación y split estable. |
| Entrenar | `train_tinker.py`: smoke test offline por defecto; `--train` lanza el entrenamiento. |
| Evaluar | `sample_checkpoint.py`: compara base y checkpoints. |
| Exportar | `export_checkpoint.py`: descarga el checkpoint de entrenamiento y fusiona LoRA. |
| Convertir | `make_gguf.sh`: conversión GGUF y cuantización con llama.cpp. |
| Servir | `serve_gguf.sh`: levanta llama.cpp con plantilla y parámetros alineados con el entrenamiento. |

El repositorio genera datos sintéticos para probar la canalización sin usar transcripciones reales ni gastar en entrenamiento. Es el primer paso recomendado antes de conectar datos de trabajo.

## 8. Instalación y adaptación a Codex

El skill declara compatibilidad con Claude Code, Codex y OpenCode. Para Codex, el README propone instalarlo en:

```bash
git clone https://github.com/drost-ai/tinker-ai-skill.git \
  ~/.agents/skills/tinker-ai-skill
```

Dependencias indicadas por el proyecto: Python 3.11+, `uv` o pip, `tinker-cookbook>=0.6.0`; clave `TINKER_API_KEY` y, opcionalmente, `WANDB_API_KEY`.

**Límite importante:** los scripts de recopilación incluidos leen transcripciones JSONL de Claude Code. Para usar historiales de Codex u otro agente hay que implementar un normalizador que produzca el esquema común descrito en las referencias del proyecto. La compatibilidad del formato Agent Skills no significa que todos los formatos de transcripción se importen automáticamente.

## 9. Costes, privacidad y riesgos

- El preprocesamiento y el smoke test por defecto son locales y no lanzan entrenamiento.
- El entrenamiento, sampling y ciertas operaciones de exportación consultan el servicio Tinker y pueden tener coste. Calcularlo con los tokens reales y los precios/modelos vigentes; no reutilizar presupuestos antiguos.
- Las claves deben vivir en variables de entorno/archivo local ignorado por Git, nunca en commits, logs ni datasets.
- No enviar transcripciones de clientes, repositorios privados o sesiones sensibles sin autorización explícita.
- Revisar manualmente los datos anonimizados: la detección automática solo cubre patrones y valores conocidos.
- Excluir proyectos completos cuando no exista permiso para entrenar con sus datos.
- Los checkpoints periódicos pueden tener caducidad; exportar a tiempo el checkpoint elegido.
- LoRA no garantiza mejora: puede sobreajustar, olvidar capacidades o aprender errores de los ejemplos. Comparar siempre con el modelo base.
- La plantilla de chat, renderer, thinking y parámetros de sampling deben coincidir con el entrenamiento; una exportación/serving mal configurada puede degradar un checkpoint correcto.

## 10. Valor e integración en LEONES

Tinker AI Skill aporta una posible **línea de creación de especialistas**, no un sustituto de Atlas, LLMFit, los runtimes ni el benchmark.

Integración conceptual:

```text
casos / trazas / documentación aprobada
                ↓
       dataset versionado
                ↓
      anonimización + revisión
                ↓
       train / validation
                ↓
        Tinker LoRA (remoto)
                ↓
        checkpoint evaluado
                ↓
      export + GGUF cuantizado
                ↓
       runtime-selection.v1
                ↓
          executor local
                ↓
       grader + benchmark LEONES
                ↓
       evidencia reproducible
                ↓
       Atlas / catálogo de especialistas
```

Cada especialista debería registrarse como artefacto independiente con: modelo base y revisión, hash del dataset privado (sin publicar el dataset), configuración LoRA, identificador del run/checkpoint, coste, hash del modelo exportado, cuantización, plantilla, runtime, hardware objetivo, benchmark y límites conocidos.

La selección de especialista debe seguir subordinada al propósito y al hardware. El benchmark LEONES debe medir tanto calidad de la tarea como latencia, tokens/s y memoria. Un modelo que responde bien pero no cabe o no es suficientemente rápido en el dispositivo objetivo no debe recomendarse para ese perfil.

## 11. Evidencia y estado LEONES

### Fuente primaria revisada

- README del skill: arquitectura de nueve pasos, scripts, notas de referencia, dataset sintético y exportación GGUF.
- `SKILL.md`: reglas de operación, anonimización, split por sesión, renderizado, smoke test, entrenamiento y evaluación.
- `references/tinker-training.md`: LoRA, learning rate, rank, batch, coste y evaluación.
- `references/export-and-serve.md`: descarga del checkpoint, merge, plantilla de chat, cuantización y serving.

### Evidencia externa

- Tinker documenta una API de entrenamiento distribuido y soporte de LoRA para un catálogo de modelos de pesos abiertos.
- Tinker documenta operaciones de entrenamiento/sampling y descarga de checkpoints.
- El proyecto `tinker-ai-skill` publica el pipeline y declara haberlo usado para Tess-4 y Tess-4.5. LEONES no ha auditado esos entrenamientos ni sus datasets.

### Estimación LEONES

- Qwen3.5-4B es el punto de partida propuesto por tamaño y disponibilidad observada en el catálogo Tinker revisado.
- Su viabilidad local en el MSI depende de cuantización, contexto, runtime y offload; está pendiente de benchmark del modelo especializado exportado.
- Los ejemplos de especialistas son hipótesis de producto/experimento, no modelos ya disponibles.

### Medición LEONES

**Ninguna todavía.** No se ha ejecutado entrenamiento Tinker, exportado un especialista ni medido un GGUF derivado de esta fuente como parte de esta ficha.

## 12. Próximos pasos propuestos

1. Ejecutar el generador sintético del repositorio y recorrer el pipeline hasta el smoke test, sin `--train`.
2. Diseñar un primer dataset no sensible para el especialista de diagnóstico Ubuntu/CUDA o para documentación LEONES.
3. Verificar el catálogo y precio de Qwen3.5-4B justo antes del entrenamiento.
4. Aprobar explícitamente el presupuesto y lanzar un LoRA pequeño.
5. Comparar base/checkpoints con un test retenido.
6. Exportar, cuantizar Q4 y ejecutar en el MSI con llama.cpp.
7. Registrar el benchmark completo en LEONES; solo entonces valorar promoverlo a `measured`.

---

**Conclusión:** Tinker AI Skill puede ayudar a LEONES a pasar de utilizar modelos generalistas a mantener una familia de especialistas pequeños, entrenados para tareas concretas y desplegables localmente. La primera prueba razonable es Qwen3.5-4B, con un único dominio, datos revisados, entrenamiento remoto controlado y validación física posterior en el MSI.
