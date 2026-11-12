# Resultados resumidos · Tandem.cpp Qwen3.5-35B-A3B IQ2_XXS · 2026-11-12

## Identidad de la ejecución

- Modelo: Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf, tamaño local comunicado 9.94 GiB.
- Tandem.cpp: commit d684d4de171d8c6413e34c95fb5703492dcd2561.
- llama.cpp submodule: f5222f25c18da062ab2b8a2dbbfbf4feae398566.
- Build: 0.8.0-dev build 11962, fingerprint b11962-f5222f25c.
- Endpoint: 127.0.0.1:18086.
- Parámetros: contexto 2048, batch 128, ubatch 64, threads 8/8, ngl 99, CPU-MoE, caché expertos 512 MiB, un slot.
- Hardware: MSI Thin 15 B12UC; i7-12650H; RTX 3050 Laptop 4 GiB (sm_86); RAM 14 GiB; swap 32 GiB; driver 580.178.04; CUDA runtime 13.0; nvcc 13.4.92; Ubuntu kernel 7.0.0-43-generic.

## Resumen de mediciones

| Caso | Budget | max_tokens | completion | tok/s | finish |
|---|---:|---:|---:|---:|---|
| 17 × 23 | 64 | 256 | 70 | 35.62 | stop |
| 17 × 23 | 128 | 384 | 134 | no registrado aquí | stop |
| 17 × 23 | 256 | 512 | 262–263 | 34.58 / 33.11 | stop |
| two_sum | 128 | 512 | 512 | 33.07 | length |
| two_sum | 128 | 768 | 768 | 32.51 | length |
| two_sum | 256 | 1024 | 1024 | 33.27 | length |
| two_sum | 128 | 1536 | 1165 | 32.58 | stop |
| two_sum | 256 | 1536 | 1201 | 32.32 | stop |
| binary_search | 128 | 1536 | 1435 | 34.79 | stop |
| binary_search | 256 | 1536 | 1536 | 33.20 | length |

### Interpretación

- En aritmética, los tres presupuestos produjeron 391. Budget 64 ya bastó para esa tarea elemental.
- En two_sum, las salidas con 512/768/1024 tokens se truncaron. Con max_tokens 1536, ambos presupuestos completaron; 128 fue aproximadamente 0.8% más rápido y no se demostró mejora cualitativa con 256.
- En binary_search, ambas identificaron correctamente left = mid + 1. Budget 128 terminó; 256 llegó al límite max_tokens y truncó la respuesta.
- Recomendación empírica para estas tareas: budget 128 como punto de partida; 256 no aportó una mejora consistente. No generalizar fuera de esta combinación de modelo, cuantización, motor, build y host.

## Diagnóstico thinking

Con thinking activado y sin presupuesto explícito, se observaron salidas de razonamiento que consumieron max_tokens enteros sin producir contenido final (finish_reason length). La prueba sin thinking sí produjo una respuesta final. El parser Qwen3-Coder separa el contenido anterior a </think> como reasoning_content; al no aparecer el cierre antes de acabar la generación, content queda vacío. El control reasoning_budget_tokens fuerza el marcador de cierre al agotar el presupuesto.

## Artefactos locales pendientes de adjuntar

Los ficheros originales están en $HOME/Descargas/tandem-research/logs/. El recolector incluido en repro/ copia los ficheros que existan, incluyendo los JSON de peticiones, startup/build logs, metadata GGUF y JSONL de benchmark. No se afirma que esos ficheros estén ya subidos: el archivo comprimido con los originales y las capturas de sistema se incorporará después de ejecutar el recolector.
