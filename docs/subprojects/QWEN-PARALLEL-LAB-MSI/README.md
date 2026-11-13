# Qwen Parallel Lab — adaptación MSI / Qwen3.5-4B

Estado: auditoría inicial; no ejecutar el motor RTX 5090 en el MSI.

## Objetivo

Investigar y adaptar las ideas de planificación y generación paralela del proyecto [Maharajahu/qwen-parallel-lab-rtx5090-tensorfold](https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold) para un MSI Thin 15 B12UC con Ubuntu, Intel Core i7-12650H, NVIDIA RTX 3050 Laptop de 4 GiB y 14 GiB de RAM.

Modelo de partida acordado: `mlx-community/Qwen3.5-4B-MLX-4bit`, servido por TensorFold CUDA (el nombre MLX identifica el formato/checkpoint; no implica usar el backend MLX de Apple).

La validación de concurrencia queda bloqueada hasta que TensorFold integre el PR [#1879](https://github.com/ashhart/TensorFold/pull/1879) y exista una revisión upstream/release verificable que podamos fijar.

## Fuente auditada

- Repositorio: https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold
- Rama: `main`
- Commit observado: `73c5533` — `Add synchronized twelve-branch experimental engine and verified results`.
- TensorFold base fijado por el proyecto: `6e9af930261a88bb28ac0bfb157ce8e57e9eea07` (versión 1.2.6).
- Plataforma de build declarada en `engine-manifest.json`: Windows x86-64, Zig 0.17.0, CUDA 13.3, SM120.
- Las tres variantes aplican parches nativos independientes al mismo commit fijado de TensorFold.

## Hallazgos de compatibilidad

1. El README declara como objetivo cualificado Windows x64 + RTX 5090 de 32 GiB. No declara soporte validado para Linux, SM86 ni RTX 3050.
2. La variante `experimental12` reserva doce lanes por defecto, permite hasta dieciséis por API y delega la admisión al presupuesto real de VRAM. Su README declara explícitamente que no tiene CPU offload ni fallback serial.
3. El modelo de demostración es Qwen3.8-27B NVFP4 con drafter DFlash2 de 4 bits; no es el modelo de 4B elegido para este proyecto.
4. El instalador `scripts/setup.py` rechaza plataformas distintas de Windows en la fase de build y exige Zig 0.17.0, CUDA 13.3 y MSVC. Descarga/verifica checkpoints grandes y el ejecutable OMP de Windows.
5. Los parches nativos contienen cambios específicos de Qwen3.5/CUDA, NVFP4 y SM120. No deben aplicarse directamente a TensorFold 1.2.3 ni compilarse como si fueran compatibles con SM86.
6. La variante fanout modifica tres archivos nativos; shared-context modifica 86 y experimental12 106. El tamaño reducido del parche fanout no demuestra compatibilidad con SM86.
7. Las cifras publicadas (incluidos 791 tokens/s agregados y el pico muestreado de 1.081 tokens/s de experimental12) corresponden a ejecuciones agregadas en una RTX 5090 de 32 GiB. No son predicciones ni resultados transferibles al MSI.

## Estrategia de adaptación

### Separar dos capas

- **Orquestación/harness:** coordinación de tareas, entrega de propuestas, límites por tarea, integración de archivos y validación. Auditar y, si es posible, portar independientemente del motor nativo.
- **Motor TensorFold:** mantenerlo como dependencia upstream separada. No portar kernels SM120 ni parches NVFP4 por suposición; usar la ruta CUDA SM86 que TensorFold soporte realmente.

### Fases

1. Auditoría estática y matriz de dependencias de cada variante; identificar qué partes son portables y qué partes dependen de Windows/MSVC/SM120.
2. Esperar la integración verificable de TensorFold PR #1879. Fijar commit/release y mantener una copia de trabajo aislada.
3. Baseline single-stream de Qwen3.5-4B con contexto conservador. Confirmar carga, TTFT, prefill/decode, VRAM pico, RSS y swap.
4. Con baseline estable, probar dos solicitudes concurrentes. Aumentar a tres/cuatro solo si la admisión de memoria y la estabilidad lo permiten. No empezar por doce.
5. Comparar throughput agregado, latencia por rama, tokens completados, errores, VRAM/RAM/swap y coste de coordinación. Separar métricas del motor nativo de las del harness.
6. Guardar manifests, configuración, logs y resultados reproducibles en LEONES. Las mediciones del MSI solo se etiquetarán MEASURED cuando se ejecuten físicamente en ese equipo.

## Guardas

- No ejecutar los scripts PowerShell/CMD del proyecto original en Ubuntu.
- No descargar los checkpoints Qwen3.8-27B NVFP4 ni DFlash2 de este experimento para el MSI.
- No aplicar ninguno de los tres parches nativos a TensorFold activo.
- No alterar el TensorFold 1.2.3 instalado.
- No afirmar que la RTX 3050 puede ejecutar doce ramas: la concurrencia será incremental y condicionada por memoria.
- Mantener intactos los cambios locales preexistentes de LEONES y no incluirlos en commits de este subproyecto.

## Referencias

- Proyecto original: https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold
- README: https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/README.md
- Manifiesto nativo: https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/engine-manifest.json
- Resultados experimental12: https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/docs/experimental12.md
- Validación y limitaciones: https://github.com/Maharajahu/qwen-parallel-lab-rtx5090-tensorfold/blob/main/docs/validation.md
- TensorFold PR #1879: https://github.com/ashhart/TensorFold/pull/1879
