# AirLLM — fuente de conocimiento para LEONES

- **Proyecto:** AirLLM
- **Repositorio:** https://github.com/lyogavin/airllm
- **Licencia del código:** Apache-2.0 (según el repositorio)
- **Tipo:** runtime/biblioteca de inferencia orientada a reducir el uso de memoria durante la inferencia de LLM grandes.
- **Revisión:** 2026-08-20
- **Estado LEONES:** 🟢 fuente activa; 🟡 candidato de integración funcional, pendiente de benchmark propio.

## 1. Qué aporta

AirLLM aborda el principal cuello de botella de ejecutar modelos grandes en hardware con poca VRAM: evita mantener el modelo completo en memoria aceleradora. Su estrategia divide el modelo por capas y mantiene en GPU la capa necesaria durante el cálculo, trasladando el resto al almacenamiento/CPU según el flujo de ejecución.

El README actual del proyecto afirma que esta estrategia permite ejecutar modelos que exceden ampliamente la VRAM disponible. Los valores anunciados por el proyecto deben tratarse como **claims externos**, no como mediciones LEONES.

## 2. Arquitectura relevante

### Layer-wise loading

El modelo se transforma en fragmentos por capa y durante la inferencia se carga el material necesario para la capa activa. Esto cambia el requisito dominante desde **VRAM ≈ tamaño total del modelo** hacia **VRAM ≈ tamaño de la capa activa + estados auxiliares**.

Consecuencia: AirLLM es especialmente interesante cuando existe suficiente almacenamiento y el objetivo prioritario es **hacer ejecutable** un modelo que no cabe convencionalmente en GPU.

### Prefetching

El proyecto incorpora prefetching para solapar carga y cálculo. Esto es importante para LEONES porque el rendimiento real puede quedar limitado por la latencia y ancho de banda del almacenamiento, no por la capacidad de cómputo de la GPU.

### Compresión

AirLLM incluye compresión opcional de pesos de 4 u 8 bits basada en cuantización por bloques. El proyecto la presenta principalmente como una forma de reducir el volumen de datos que debe moverse durante la inferencia. Los claims de aceleración deben validarse en el hardware objetivo.

### CPU inference

El proyecto documenta soporte para inferencia CPU desde versiones anteriores. Esto convierte AirLLM en candidato para perfiles sin GPU, pero no debe confundirse **posibilidad de ejecución** con **rendimiento útil**.

## 3. Modelos y alcance

El proyecto declara compatibilidad con numerosas familias populares, entre ellas Llama, Qwen, DeepSeek, Mistral/Mixtral, Phi, Gemma, ChatGLM, Baichuan, InternLM, Yi y Kimi K3, además de modelos recientes.

La compatibilidad efectiva debe verificarse por versión de `airllm`, `transformers`, arquitectura del modelo, formato de pesos, dependencias de atención y hardware.

Especial atención a modelos MoE: la estrategia de streaming puede ser particularmente atractiva porque permite cargar sólo los expertos necesarios para cada token, pero el coste de transferencia, routing y sincronización debe medirse.

## 4. Relación con LEONES

AirLLM no debe sustituir a LLMFit ni al benchmark LEONES.

**Papel propuesto:** runtime candidato dentro de la capa de ejecución y como mecanismo de recuperación para modelos que no caben en la ruta convencional.

Pipeline recomendado:

```text
Perfil hardware
    ↓
LLMFit — preselección de modelos
    ↓
Router LEONES — tarea + restricciones + evidencia
    ↓
Runtime selector
    ├── llama.cpp / otros runtimes convencionales
    └── AirLLM — cuando la memoria sea el cuello de botella
    ↓
Benchmark LEONES
    ↓
Medición real: latencia, tok/s, RAM, VRAM, I/O, estabilidad
```

## 5. Encaje con el recomendador

AirLLM debe aparecer como **runtime**, no como una propiedad del modelo.

El recomendador debe conservar separados:

- `model_id`
- `runtime_id = airllm`
- `hardware_profile`
- `precision/compression`
- `context_length`
- `storage_profile`
- `measured_prefill_tps`
- `measured_decode_tps`
- `time_to_first_token`
- `peak_ram`
- `peak_vram`
- `disk_read_bytes`
- `disk_read_latency`
- `result_quality`

Esto permite comparar AirLLM contra otros runtimes sin atribuir al modelo el comportamiento específico del motor.

## 6. Criterios de benchmark LEONES

Antes de recomendar AirLLM para un equipo concreto, medir como mínimo:

1. instalación reproducible en Debian;
2. descarga y transformación inicial del modelo;
3. espacio de almacenamiento utilizado;
4. tiempo de carga inicial;
5. TTFT;
6. tok/s de generación;
7. RAM pico;
8. VRAM pico, si existe GPU;
9. lectura sostenida y latencia del almacenamiento;
10. comportamiento con contextos crecientes;
11. estabilidad durante sesiones largas;
12. calidad frente al mismo modelo en otro runtime.

Para perfiles de bajo consumo, el almacenamiento debe considerarse una variable de primer orden. Una solución puede ser técnicamente ejecutable y, aun así, quedar fuera del objetivo LEONES de respuesta práctica.

## 7. Compatibilidad y mantenimiento

AirLLM depende de un ecosistema que cambia rápidamente (`torch`, `transformers`, `bitsandbytes`, `flash-attn`, arquitecturas de modelos y formatos). Algunas arquitecturas pueden requerir versiones concretas.

Por tanto, LEONES debe registrar la combinación completa:

`airllm + torch + transformers + modelo + precisión + hardware + SO`

y no sólo la versión de AirLLM.

## 8. Valor estratégico

AirLLM amplía el espacio de modelos **ejecutables** en hardware de consumo. Su mayor valor para LEONES no es prometer que un equipo modesto pueda ejecutar cualquier modelo a velocidad interactiva, sino permitir separar tres preguntas:

- **¿Cabe?** — capacidad/memoria.
- **¿Funciona?** — compatibilidad y estabilidad.
- **¿Sirve?** — rendimiento y calidad medidos para la tarea.

Esta separación encaja directamente con la filosofía de LEONES de no convertir una estimación externa en una medición propia.

## 9. Fuente primaria

Repositorio oficial: https://github.com/lyogavin/airllm

La información de esta ficha se basa en la documentación/README del repositorio consultado el 2026-08-20. Las cifras de memoria y rendimiento publicadas por AirLLM quedan clasificadas como **evidencia externa del proveedor/proyecto** hasta su reproducción mediante benchmarks LEONES.
