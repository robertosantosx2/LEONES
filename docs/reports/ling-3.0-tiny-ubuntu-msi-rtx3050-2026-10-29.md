# Ling 3.0 Tiny en Ubuntu — MSI con RTX 3050 Laptop (2026-10-29)

**Estado:** resultados preliminares; benchmark de rendimiento y uso de GPU aún incompleto.  
**Objetivo:** probar ejecución local con llama.cpp CUDA y validar una tarea reproducible de generación de código.

## Hardware y software conocidos

- Equipo: MSI Thin 15 B12UC.
- CPU: Intel Core i7-12650H, 16 CPU lógicas.
- RAM instalada: 14 GiB aproximadamente.
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM.
- Sistema: Ubuntu; kernel observado `7.0.0-38-generic`.
- llama.cpp: `0.7.0-dev`, build `b11740-6fa4f6cd3`.
- Binario: `$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli`.
- Modelo: `bloomer010/Ling-3.0-tiny-GGUF:IQ2_M`, IQ2_M, 2.7 bpw.
- Contexto: 1024; temperatura 0.1; `--gpu-layers 8`; `--flash-attn auto`; razonamiento desactivado.

## Ejecuciones observadas

### Ejecución inicial, 128 tokens máximos

- Prompt: solicitud de una función factorial con breve explicación y ejemplo.
- Prefill: **68,7 tokens/s**.
- Generación: **8,3 tokens/s**.
- Tiempo transcurrido: **83,83 s**.
- RSS máximo del proceso: **3.032.060 KiB** (aprox. 2,89 GiB).
- Código de salida: 0.
- La respuesta quedó truncada en `if n`; no se considera validada funcionalmente.
- Log local: `$HOME/ling3-rtx3050-bench-20261029/ling3-iq2m-ngl8-first-run.log`.
- SHA-256 del log copiado: `ff60e9cec5b014d0388a0ca1975e5132d274a462682609919e8688e3c47f59d60`.

### Reintento funcional, 256 tokens máximos configurados

- Prompt almacenado en `$HOME/ling3-rtx3050-bench-20261029/factorial-prompt.txt`.
- Prefill: **62,5 tokens/s**.
- Generación: **5,4 tokens/s**.
- Tiempo de pared observado entre inicio y fin: aproximadamente **22 s** (21:54:03–21:54:25 +01:00).
- Código de salida de llama-cli: **0**.
- El modelo generó una función completa que verifica `isinstance(n, int)`, lanza `ValueError` para negativos y calcula el factorial con un bucle.
- Log local: `$HOME/ling3-rtx3050-bench-20261029/ling3-iq2m-ngl8-factorial-retry.log`.
- No se capturó RSS máximo en este reintento.

## Validación funcional del código generado

Se ejecutó por separado en Python 3 el código generado por el modelo. Todos los casos pasaron:

- `factorial(0) == 1`
- `factorial(1) == 1`
- `factorial(5) == 120`
- `factorial(10) == 3628800`
- `factorial(-1)` y `factorial(-5)` lanzan `ValueError`.
- `factorial(2.5)` lanza `TypeError`.

**Resultado:** 7 comprobaciones superadas. Matiz: en Python, `bool` es subclase de `int`; por tanto, la comprobación `isinstance(n, int)` acepta `True` y `False`. No se probó ese caso.

## Observaciones sobre GPU y estabilidad

- Se solicitaron 8 capas GPU, pero no se midió la utilización de GPU durante la generación; el parámetro por sí solo no demuestra el uso real de GPU.
- En reposo, `nvidia-smi` mostró 15 MiB de VRAM ocupada.
- Tres lecturas de potencia dieron 749,67 W, 6,23 W y 6,16 W; la primera es anómala y parece una lectura puntual de telemetría. Las dos siguientes son coherentes con reposo.
- Temperatura observada: 44–45 °C.
- `systemctl is-active display-manager` devolvió `active`.
- No se encontraron coincidencias de OOM, NVRM o Xid en el intervalo consultado.
- En el último muestreo, `free -h` mostró 10 GiB disponibles y 2,1 GiB de swap usados; no hay evidencia de presión de memoria en ese momento.
- No había procesos `llama-cli` ni `llama-server` activos después de la prueba.
- No se modificaron servicios existentes ni se utilizó el puerto 8080.

## Conclusión provisional

Ling 3.0 Tiny IQ2_M ejecuta en este MSI con Ubuntu y genera código Python funcional para la tarea de factorial. Las mediciones observadas son 62,5 tokens/s de prefill y 5,4 tokens/s de generación en el reintento funcional. No deben tratarse aún como benchmark exhaustivo ni compararse directamente con otras máquinas sin igualar modelo/cuanti­zación, compilación, prompt, contexto y límites de generación.

## Pendiente para cerrar el benchmark

1. Repetir con `/usr/bin/time -v` para capturar RSS máximo en la ejecución funcional.
2. Registrar `nvidia-smi` durante la generación para comprobar utilización y VRAM en carga.
3. Conservar los logs completos y registrar hash SHA-256 del log funcional.
4. Añadir varias repeticiones bajo los mismos parámetros antes de publicar cifras consolidadas.
5. Opcional: probar explícitamente que `True` y `False` se aceptan por la semántica de `isinstance`, sin confundirlo con un fallo de los requisitos originales.
