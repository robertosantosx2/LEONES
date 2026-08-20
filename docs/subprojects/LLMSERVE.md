# LLMServe — integración LEONES

## Upstream

- Repositorio: https://github.com/AlexsJones/llmserve
- Rama de referencia: `main`
- SHA fijado en esta integración: `85c63fce8a7c386e5fa1db8f3093502a1d077d39`
- Licencia: MIT
- Implementación: Rust/TUI

## Función en LEONES

LLMServe es la capa de **serving local**: descubre modelos locales y backends de inferencia y permite lanzar el modelo seleccionado mediante una TUI. El proyecto upstream se presenta explícitamente como compañero de LLMFit: LLMFit responde qué modelos encajan en el hardware y LLMServe ejecuta el elegido.

LEONES debe mantener estas responsabilidades separadas:

```text
Hardware
   ↓
LLMFit — estimación de encaje
   ↓
Atlas + evidencia — identidad y procedencia
   ↓
selección de modelo/configuración
   ↓
LLMServe — descubrimiento de backend + lanzamiento
   ↓
benchmark LEONES — medición real
```

## Capacidades relevantes

- autodetección de backends locales;
- descubrimiento de modelos GGUF y MLX;
- múltiples directorios de modelos;
- presets por backend;
- configuración de contexto, batch, GPU layers, threads y argumentos adicionales;
- múltiples modelos/servidores simultáneos;
- logs y diagnóstico de procesos;
- soporte de modelos de visión mediante `mmproj`;
- configuración persistente en `~/.config/llmserve/config.toml`.

El upstream documenta detección de llama-server, KoboldCpp, LocalAI, MLX, Ollama, vLLM y LM Studio. Los backends no equivalentes a archivos locales propios se detectan para mostrar su disponibilidad/limitaciones.

## Regla de integración

**LLMServe se conserva idéntico al upstream.** LEONES no modifica su código para adaptarlo. Las necesidades detectadas durante la integración se convierten en documentación, tests de contrato o propuestas al autor upstream.

## Primeras líneas de trabajo

1. Verificar que el submódulo permanece en el SHA fijado.
2. Crear un smoke test de presencia del upstream y de su `Cargo.toml`/entrypoint.
3. Comprobar instalación/ejecución en Debian cuando sea necesario, sin contaminar el árbol del submódulo.
4. Integrar la salida de LLMFit con la selección de modelo de LLMServe sin duplicar lógica.
5. Registrar en LEONES la combinación `modelo + backend + configuración + hardware` antes de medir.
6. Comparar después la predicción de LLMFit con el rendimiento observado por los benchmarks de LEONES.

## Principio de procedencia

LLMServe no es una fuente de verdad sobre calidad de modelos. Es un ejecutor/serving layer. Los datos de rendimiento obtenidos al usarlo deben clasificarse como `measured` únicamente cuando LEONES los haya ejecutado y registrado bajo condiciones reproducibles.
