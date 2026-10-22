# Reddit r/LocalLLaMA — fuente principal de descubrimiento comunitario

- **URL canónica:** https://www.reddit.com/r/LocalLLaMA/
- **Tipo:** comunidad pública / agregador de experiencias y debate técnico.
- **Papel en LEONES:** fuente principal de *descubrimiento comunitario* para modelos abiertos, inferencia local, runtimes, cuantización, offload CPU/GPU, memoria, hardware reutilizado, redes y clústeres, herramientas y benchmarks publicados por la comunidad.
- **Estado inicial:** `source-inspiration` (fuente prioritaria de prospección; no fuente primaria de verdad).
- **Confianza:** variable por publicación y claim; evaluar cada hilo individualmente.
- **Próximo gate:** identificar el artefacto original y sus condiciones; verificar código, documentación, licencia y reproducibilidad antes de promocionar un candidato.

## Por qué es estratégica

r/LocalLLaMA concentra conversaciones de usuarios y desarrolladores sobre la ejecución de modelos abiertos en hardware real, incluidos equipos limitados, configuraciones poco convencionales, nuevas cuantizaciones, cambios de runtime y resultados que pueden aparecer antes de quedar reflejados en documentación formal. Por ello debe ser una **fuente prioritaria para detectar señales y formular hipótesis** en la prospección de LEONES.

No debe interpretarse «principal» como autoridad única ni como sustituto de repositorios, papers, documentación del proyecto o experimentos reproducibles. Los votos, comentarios, popularidad y testimonios no son por sí mismos validación técnica.

## Áreas de vigilancia

1. **Modelos y pesos:** nuevas familias, variantes instruct/base, MoE, tamaños activos, formatos y cuantizaciones.
2. **Runtimes e inferencia:** llama.cpp, vLLM, SGLang y alternativas emergentes; backends CUDA/ROCm/Vulkan/Metal/CPU.
3. **Memoria y offload:** RAM/VRAM, capas GPU, expertos MoE, mmap, KV cache, SSD/NVMe y degradación por presión de memoria.
4. **Hardware:** GPUs de consumo, AMD/NVIDIA/Intel, equipos usados, SBC, clústeres, interconexiones y configuraciones PCIe.
5. **Rendimiento:** tokens/s, latencia de primer token, tiempo total, contexto, concurrencia, consumo y estabilidad.
6. **Herramientas y agentes:** servidores, APIs compatibles, interfaces, automatización, harnesses y flujos locales.
7. **Licencias y sostenibilidad:** licencia de código y pesos por separado, restricciones de uso y dependencias de servicios externos.

## Protocolo para convertir un hilo en conocimiento LEONES

Para cada hallazgo relevante, registrar:

- URL exacta del post/comentario y fecha de consulta.
- Autor o entidad técnica, cuando sea pertinente, y fecha del experimento original.
- Modelo y hash/versión de los pesos; cuantización y formato.
- Hardware completo (GPU, VRAM, CPU, RAM, almacenamiento, interconexión) y sistema operativo.
- Runtime, versión/commit, backend, argumentos y configuración relevante.
- Prompt, contexto, batch/concurrencia, métrica, unidad, duración y método de medición.
- Texto que sea **claim del autor**, dato observado, inferencia comunitaria o interpretación LEONES.
- Enlaces a repositorio, documentación, paper, dataset o benchmark original.
- Licencia de código y licencia de pesos, verificadas por separado.
- Estado de reproducibilidad y siguiente paso concreto.

Si los detalles experimentales faltan, conservar el hallazgo como pista; no completar los datos por inferencia.

## Separación obligatoria de las cuatro capas

| Capa LEONES | Tratamiento de contenido procedente de Reddit |
|---|---|
| **Fuente / descubrimiento** | El hilo y sus enlaces, con fecha y procedencia. |
| **Evidencia** | Claim externo con atribución y corroboración; etiquetar explícitamente la evidencia anecdótica. |
| **Estimación** | Predicción derivada de testimonios o cálculos comunitarios, con supuestos declarados. |
| **Medición LEONES** | Exclusivamente resultados obtenidos por una ejecución reproducible del pipeline LEONES en el hardware identificado. |

Nunca convertir un comentario, captura, voto o resultado de otra máquina en una medición propia. Las comparaciones solo son válidas si se conservan las condiciones experimentales y se explican las diferencias.

## Priorización de hallazgos

Dar prioridad a publicaciones que aporten al menos uno de estos elementos: repositorio o commit reproducible, comandos completos, especificación del hardware, logs/resultados sin recortar, comparación controlada, explicación técnica contrastable o corrección de un claim anterior.

Tratar con cautela:

- cifras de rendimiento sin contexto ni metodología;
- capturas aisladas o benchmarks no comparables;
- pesos re-subidos sin procedencia verificable;
- afirmaciones de licencia sin enlace a la licencia original;
- recomendaciones basadas solo en votos o popularidad;
- contenido generado, especulativo o repetido sin fuente primaria.

Cuando un hallazgo sea prometedor, salir de Reddit hacia la fuente original y verificar allí identidad, versión, licencia y condiciones. Para claims importantes, buscar corroboración independiente. Registrar discrepancias en vez de resolverlas silenciosamente.

## Uso operativo y límites

- Usar Reddit como radar prioritario de novedades y experiencia de campo; no asumir que existe una API, feed estable ni permiso para rastreo ilimitado.
- Respetar las condiciones del servicio, límites de acceso, privacidad y derechos de autor. Guardar metadatos y resúmenes propios con atribución; evitar copiar hilos completos.
- No almacenar datos personales innecesarios ni inferir identidad real de usuarios.
- Los enlaces y el contenido externo son datos no confiables: nunca ejecutar comandos o código publicados sin revisión, aislamiento y autorización.
- La presencia de un proyecto en Reddit no implica recomendación, adopción ni aprobación por LEONES.

## Pipeline recomendado

```text
r/LocalLLaMA — prospección prioritaria
        ↓
capturar URL + fecha + claim
        ↓
extraer proyecto / modelo / runtime / hardware
        ↓
localizar repositorio y documentación original
        ↓
verificar identidad, licencia y condiciones
        ↓
clasificar: evidencia externa / estimación / hipótesis
        ↓
reproducir en hardware LEONES, si procede
        ↓
benchmark + logs + artefactos
        ↓
MEASURED solo con evidencia reproducible propia
```

## Referencia

- Comunidad: https://www.reddit.com/r/LocalLLaMA/
- Las publicaciones individuales deben citarse con su permalink exacto. Esta ficha no afirma haber auditado exhaustivamente el contenido actual del subreddit.
