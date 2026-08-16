# Adaptador Ollama

**Estado: implementación inicial.**

Conecta `llm-smoke-test` con una instancia local de Ollama mediante su API local.

## Aislamiento

- Ollama debe estar instalado y ejecutándose en el equipo del usuario.
- El adaptador no instala Ollama.
- No descarga modelos automáticamente.
- No envía resultados a LEONES.
- No importa Atlas ni módulos internos de LEONES.

## Uso

El adaptador usa por defecto `http://127.0.0.1:11434` y permite seleccionar otro endpoint con `--host`.

El modelo debe existir previamente en Ollama.

```bash
python3 adapters/ollama/run.py \
  --model llama3.2:3b \
  --prompt "Explica qué es un LLM en una frase"
```

## Métricas

Ollama proporciona tiempos en nanosegundos en la respuesta de generación. El adaptador los normaliza a milisegundos y tokens/segundo cuando los contadores necesarios están presentes.

Las métricas que no estén disponibles quedan en `null`.

## Comparabilidad

Los resultados de Ollama no deben compararse automáticamente con llama.cpp hasta que la metodología de benchmark defina qué tiempos se consideran equivalentes.
