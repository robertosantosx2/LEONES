# LLM Smoke Test — matriz de runtimes locales

**Estado: v0.1 — planificación de adaptadores**

La matriz define qué runtimes se consideran candidatos para las pruebas locales. No implica compatibilidad implementada: cada adaptador debe validarse por separado.

| Runtime | Prioridad | Objetivo | Núcleo independiente | Estado |
|---|---:|---|---|---|
| llama.cpp | P0 | Inferencia local eficiente, especialmente GGUF/CPU-GPU | Sí | Especificación creada |
| Ollama | P0 | Entrada sencilla para usuarios de escritorio | Sí | Pendiente |
| Transformers | P1 | Pruebas directas sobre ecosistema Python/Hugging Face | Sí | Pendiente |
| vLLM | P1 | Inferencia local orientada a GPU/servidor | Sí | Pendiente |
| MLX | P2 | Apple Silicon | Sí | Pendiente |

## Criterios de inclusión

Un runtime entra en la matriz si:

1. puede ejecutarse localmente;
2. tiene una interfaz suficientemente estable para automatización;
3. permite obtener o estimar métricas relevantes;
4. puede ejecutarse sin infraestructura de LEONES;
5. permite documentar claramente requisitos y limitaciones.

## Criterios de adaptación

Cada adaptador debe separar:

```text
harness LEONES
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

No se permite que un adaptador cambie el significado de una métrica para hacerla comparable. Si una métrica no es equivalente o no puede medirse de forma fiable, se devuelve `null` y se documenta.

## Prioridades

### P0 — primera ola

**llama.cpp** y **Ollama** cubren dos necesidades complementarias: control local y simplicidad de uso.

### P1 — segunda ola

**Transformers** y **vLLM** amplían la cobertura hacia ejecución Python y escenarios GPU/servidor.

### P2 — plataformas específicas

**MLX** se reserva para una fase posterior centrada en Apple Silicon.

## Regla de compatibilidad

No se fijan versiones de runtime en esta matriz. La implementación de cada adaptador debe fijar una versión o rango soportado después de verificar la interfaz real y registrar la fecha de validación.

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

## No incluidos inicialmente

No se incluyen runtimes remotos o APIs de proveedores cloud como adaptadores de ejecución local. Pueden aparecer como fuentes de comparación en otros componentes de LEONES, pero no pertenecen al producto `scripts/local` cuyo objetivo es probar el LLM en el equipo del usuario.
