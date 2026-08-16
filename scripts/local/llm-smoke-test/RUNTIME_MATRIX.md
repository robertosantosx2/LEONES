# LLM Smoke Test — matriz de runtimes locales

**Estado: v0.1 — adaptadores locales**

La matriz define los runtimes locales que LEONES considera para las pruebas. La presencia en la matriz no implica que todas sus capacidades sean equivalentes.

| Runtime | Prioridad | Objetivo | Núcleo independiente | Estado |
|---|---:|---|---|---|
| llama.cpp | P0 | Inferencia local eficiente, especialmente GGUF/CPU-GPU | Sí | Implementación inicial |
| Ollama | P0 | Entrada sencilla para usuarios de escritorio | Sí | Implementación inicial |
| Transformers | P1 | Pruebas directas sobre ecosistema Python/Hugging Face | Sí | Pendiente |
| vLLM | P1 | Inferencia local orientada a GPU/servidor | Sí | Pendiente |
| MLX | P2 | Apple Silicon | Sí | Pendiente |

## Criterios de inclusión

Un runtime entra en la matriz si:

1. puede ejecutarse localmente;
2. tiene una interfaz suficientemente estable para automatización;
3. permite obtener métricas relevantes;
4. puede ejecutarse sin infraestructura de LEONES;
5. permite documentar claramente requisitos y limitaciones.

## Arquitectura del adaptador

```text
harness
   ↓
configuración explícita
   ↓
adaptador
   ↓
runtime local
   ↓
resultado bruto
   ↓
normalización
   ↓
RESULT_SCHEMA v0.1
```

Los adaptadores no pueden cambiar el significado de una métrica para hacerla parecer comparable. Si una métrica no es equivalente o no puede medirse de forma fiable, se devuelve `null` y se documenta.

## Prioridades

### P0 — primera ola

**llama.cpp** y **Ollama** cubren dos necesidades complementarias: control y simplicidad de uso.

### P1 — segunda ola

**Transformers** y **vLLM** ampliarán la cobertura hacia ejecución Python y escenarios GPU/servidor.

### P2 — plataforma específica

**MLX** queda reservado para Apple Silicon.

## Métricas objetivo

Cuando el runtime lo permita:

- carga/arranque;
- TTFT;
- tiempo de generación;
- tokens de entrada;
- tokens generados;
- tokens/segundo;
- contexto;
- RAM;
- VRAM;
- errores y estado.

Las diferencias de medición entre runtimes deben documentarse antes de comparar resultados.

## Regla de versiones

Cada adaptador debe registrar la versión del runtime cuando pueda obtenerla de forma fiable. La compatibilidad definitiva se fijará después de validar versiones reales.

## No incluidos inicialmente

No se incluyen APIs cloud como adaptadores de ejecución local. Pueden aparecer en otros componentes de LEONES, pero no forman parte del producto `scripts/local`, cuyo objetivo es probar el LLM en el equipo del usuario.
