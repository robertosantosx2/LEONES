# Manada — Informe automático

La Manada permite aportar de forma voluntaria resultados técnicos de máquinas reales para mejorar futuras recomendaciones de LEONES.

## Uso rápido

Desde la raíz del proyecto:

```bash
python3 scripts/leones-manada-report.py
```

Genera un informe Markdown en `results/manada/`.

También se puede indicar el modelo, llama.cpp y Buddy:

```bash
python3 scripts/leones-manada-report.py \
  --model ~/models/Qwen3-8B-Q4_K_M.gguf \
  --llama-cpp ./llama.cpp \
  --buddy ./buddy \
  --output results/manada/mi-prueba.md
```

## Qué obtiene automáticamente

- sistema operativo y versión;
- kernel y arquitectura;
- CPU, RAM, GPU y VRAM cuando están disponibles;
- versiones de Python y Git;
- commits de llama.cpp y Buddy;
- modelo y SHA-256;
- rendimiento de inferencia cuando se proporciona una salida de benchmark;
- resultados B01–B05 de Evaluación cuando se proporciona el resultado correspondiente.

## Privacidad

El informe está diseñado para no recopilar deliberadamente nombres de usuario, hostname, MAC/IP, números de serie, UUID, rutas personales, credenciales, tokens ni ubicación personal.

La publicación es voluntaria y siempre debe existir una revisión humana antes de compartir el resultado.

## Flujo

```text
medir → generar informe → revisar privacidad → compartir voluntariamente → agregar → mejorar recomendaciones
```

La Manada identifica el experimento técnico, no a la persona.
