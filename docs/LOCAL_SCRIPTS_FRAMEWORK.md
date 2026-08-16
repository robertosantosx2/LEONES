# Marco de scripts locales de LEONES

**Estado:** definido · **Fecha:** 2026-08-16

## 1. Objetivo

Los scripts locales son herramientas que el usuario puede descargar y ejecutar en su propio equipo para comprobar cómo funciona un LLM en condiciones reales.

La web documenta y orienta. La infraestructura de LEONES descubre, almacena, evalúa y recomienda. El script local ejecuta la prueba en el equipo del usuario.

```text
WEB LEONES
   │ documentación / orientación
   ▼
SCRIPT LOCAL
   │
   ├── hardware real
   ├── runtime real
   ├── modelo real
   └── prueba reproducible
   │
   ▼
RESULTADO ESTRUCTURADO
```

## 2. Principio de independencia

Un script local no debe requerir la infraestructura de LEONES para realizar su prueba básica. No debe depender de Atlas, del recomendador, de servicios privados ni de credenciales de LEONES.

El usuario controla el modelo y su ubicación. El script no descarga modelos silenciosamente.

## 3. Contrato mínimo de ejecución

Cada adaptador debe identificar, cuando sea posible:

- sistema operativo;
- CPU y GPU;
- memoria RAM y VRAM;
- runtime y versión;
- modelo y formato;
- cuantización;
- contexto utilizado;
- parámetros relevantes de generación;
- resultado de la ejecución;
- errores y causa si falla.

Una medición que no pueda obtenerse de forma fiable debe representarse como `null`, nunca como `0`.

## 4. Métricas

El contrato debe distinguir como mínimo:

- TTFT (time to first token);
- tiempo total;
- tokens de entrada;
- tokens de salida;
- tokens por segundo de salida;
- memoria cuando pueda medirse;
- estado de ejecución.

Para comparaciones serias deben conservarse también modelo, cuantización, runtime, versión, hardware y configuración. La fuente de referencia insiste en que comparar únicamente tokens/segundo con una sola carga es insuficiente. fileciteturn74file13L1-L13

## 5. Arquitectura de adaptadores

El contrato común debe permitir sustituir el runtime sin cambiar la herramienta de medición.

Prioridad conceptual:

1. `llama.cpp`: portabilidad, CPU, hardware heterogéneo y GGUF.
2. `Ollama`: entrada sencilla para usuarios de escritorio cuando resulte útil.
3. `Transformers`: referencia general para modelos soportados por Python.
4. `vLLM`: servicio y cargas con mayores necesidades de concurrencia.
5. Otros runtimes: se incorporan solo cuando aporten una capacidad diferenciada.

La documentación de referencia describe llama.cpp como especialmente útil para hardware atípico, limitado, offline y configuraciones híbridas CPU/GPU. fileciteturn74file10L1-L8

## 6. Memoria y selección

El script no debe decidir que un modelo cabe únicamente por el tamaño de sus pesos. La memoria real incluye pesos, caché KV, activaciones, batching/concurrencia y sobrecarga del runtime. fileciteturn74file17L1-L11

Como regla operativa, se debe reservar margen de memoria y evitar configuraciones que apenas caben y terminan haciendo offload perjudicial a CPU. La documentación de referencia propone trabajar aproximadamente al 80–90 % de la memoria disponible como límite práctico. fileciteturn74file4L1-L9

## 7. Chat template

La plantilla de chat forma parte del contrato del modelo. El adaptador debe utilizar la plantilla proporcionada por el tokenizador/runtime cuando exista; una plantilla incorrecta puede producir resultados aparentemente defectuosos o romper tool calls. fileciteturn74file12L1-L8

## 8. Seguridad

Los scripts deben minimizar permisos y no ejecutar código descargado de fuentes no confiables. Para modelos se debe priorizar `safetensors` cuando corresponda y tratar con especial precaución formatos que puedan implicar carga ejecutable. Para llama.cpp, GGUF es el formato de referencia de su ecosistema. fileciteturn74file12L9-L16

## 9. Primera herramienta: LLM Smoke Test

El Smoke Test debe responder una pregunta sencilla:

> **¿Puedo ejecutar este modelo, con este runtime, en este hardware, y obtener una respuesta válida?**

No pretende ser un benchmark completo. Es una prueba de salud de la pila.

Fases:

```text
DISCOVERY
   ↓
VALIDATE CONFIG
   ↓
LOAD MODEL
   ↓
RUN PROMPT DETERMINISTA
   ↓
COLLECT METRICS
   ↓
VALIDATE RESULT
   ↓
JSON
```

## 10. Evolución

Después del Smoke Test se podrán añadir pruebas específicas de calidad, coding, herramientas, contexto largo y agenticidad. Estas deben mantenerse separadas del test básico para que un fallo de una capacidad avanzada no se confunda con un fallo de inferencia elemental.

La referencia de LLM local recomienda ejecutar entre 20 y 50 prompts reales sobre candidatos y medir calidad, latencia, memoria, fiabilidad de la plantilla y modos de fallo. fileciteturn74file4L1-L9

## 11. Qué debe volver a LEONES

El resultado local debe poder conservarse como artefacto JSON y, si el usuario lo desea, incorporarse posteriormente a procesos de evidencia. La herramienta local no debe necesitar conectarse a LEONES para funcionar.

Así se mantiene la frontera:

```text
LOCAL → mide
LEONES → estructura, compara, aprende y recomienda
WEB → explica
```
