# Ling 3.0 Tiny en Ubuntu — MSI con RTX 3050 Laptop (2026-10-29)

**Estado:** prueba funcional preliminar superada; benchmark de memoria y utilización GPU durante inferencia pendiente.  
**Fecha de pruebas:** 29 de octubre de 2026, zona horaria local `+01:00`.  
**Objetivo:** comprobar que Ling 3.0 Tiny puede ejecutarse localmente en el MSI con llama.cpp CUDA, medir el rendimiento observado y validar con Python una tarea reproducible de generación de código.  
**Alcance:** texto únicamente; no se ha probado generación de imágenes, herramientas ni razonamiento habilitado.

## 1. Hardware y sistema

- Equipo: MSI Thin 15 B12UC.
- CPU: Intel Core i7-12650H; 16 CPU lógicas.
- RAM: aproximadamente 14 GiB.
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB de VRAM.
- Sistema operativo: Ubuntu.
- Kernel observado: `7.0.0-38-generic`.
- Controlador NVIDIA observado: `580.178.04`.
- CUDA indicada por `nvidia-smi`: `13.0`.
- El equipo llevaba encendido aproximadamente 10 días y 12 horas en las comprobaciones.
- Estado del servidor gráfico: `systemctl is-active display-manager` devolvió `active`.

## 2. Software y modelo

- Motor: llama.cpp.
- Versión declarada por el binario: `0.7.0-dev`.
- Build: `b11740-6fa4f6cd3`.
- Binario usado: `$HOME/llama.cpp-cuda/build-cuda/bin/llama-cli`.
- Repositorio Hugging Face: [bloomer010/Ling-3.0-tiny-GGUF](https://huggingface.co/bloomer010/Ling-3.0-tiny-GGUF).
- Identificador cargado: `bloomer010/Ling-3.0-tiny-GGUF:IQ2_M`.
- Cuantización: `IQ2_M`, 2,7 bits por peso (bpw), tamaño informado por el motor aproximadamente 2,7 GB.
- Modalidad declarada por el motor: texto.
- Contexto: 1024 tokens.
- Temperatura: 0.1.
- Hilos: 8 (`--threads 8 --threads-batch 8`).
- Offload solicitado: `--gpu-layers 8`.
- Atención: `--flash-attn auto`.
- Razonamiento desactivado explícitamente mediante `--reasoning off --reasoning-format none --reasoning-budget 0`.
- Plantilla y modo de ejecución: `--jinja --single-turn --simple-io`.
- Nota de compatibilidad CLI: este build **no admite** `--prompt-file`; la ejecución que lo usó terminó inmediatamente con `error: invalid argument: --prompt-file` y código de salida 1. Esa ejecución no llegó a cargar el modelo y no es un benchmark.

## 3. Prompts empleados

### Primera ejecución

```text
Escribe una función Python factorial(n) que devuelva el factorial de n y rechace los enteros negativos con ValueError. Incluye una breve explicación y un ejemplo de uso.
```

### Reintento funcional

El prompt se guardó en `$HOME/ling3-rtx3050-bench-20261029/factorial-prompt.txt`:

```text
Escribe solo una función Python llamada factorial(n), sin explicación ni ejemplo.
Debe rechazar n negativo con ValueError, devolver 1 para n=0 y calcular correctamente n! para enteros no negativos.
Incluye comprobación de que n sea entero.
```

## 4. Resultados de inferencia

### 4.1 Primera ejecución — máximo de 128 tokens

- Log original: `$HOME/ling3-rtx3050-bench-20261029/ling3-iq2m-ngl8.log`.
- Copia conservada: `$HOME/ling3-rtx3050-bench-20261029/ling3-iq2m-ngl8-first-run.log`.
- SHA-256 de la copia del log: `ff60e9cec5b014d0388a0ca1975e5132d274a462682609919e8688e3c47f59d60`.
- Prefill: **68,7 tokens/s**.
- Generación: **8,3 tokens/s**.
- Tiempo transcurrido medido por `/usr/bin/time -v`: **83,83 s**.
- Tiempo de usuario: **71,39 s**.
- Tiempo de sistema: **23,95 s**.
- CPU media: **113 %**.
- RSS máximo: **3.032.060 KiB**, aproximadamente **2,89 GiB**.
- Fallos de página mayores: **969**.
- Swap contabilizado por el proceso: **0**.
- Código de salida: **0**.
- Resultado: el modelo empezó a escribir una respuesta, pero quedó truncada en `if n`; por ello no se consideró validada funcionalmente.
- La cifra de RSS corresponde a esta primera ejecución, no al reintento funcional.

### 4.2 Reintento funcional — máximo configurado de 256 tokens

- Inicio observado: `2026-10-29T21:54:03+01:00`.
- Fin observado: `2026-10-29T21:54:25+01:00`.
- Duración de pared aproximada: **22 s**.
- Prefill: **62,5 tokens/s**.
- Generación: **5,4 tokens/s**.
- Código de salida de `llama-cli`: **0**.
- Log: `$HOME/ling3-rtx3050-bench-20261029/ling3-iq2m-ngl8-factorial-retry.log`.
- No se capturó `/usr/bin/time -v` en esta ejecución, por lo que no se conoce su RSS máximo.
- La salida del motor informó:
  - `build: b11740-6fa4f6cd3`
  - `model: bloomer010/Ling-3.0-tiny-GGUF:IQ2_M`
  - `ftype: IQ2_M - 2.7 bpw`
  - `modalities: text`
- El prompt apareció completo en la salida y el modelo terminó normalmente con `Exiting...`.
- El límite de 256 tokens era el máximo solicitado; no implica que el modelo generase exactamente 256 tokens.

### 4.3 Código producido por el modelo

La respuesta generada fue:

```python
def factorial(n):
    if not isinstance(n, int):
        raise TypeError("El valor debe ser un entero")
    if n < 0:
        raise ValueError("No se puede calcular el factorial de un número negativo")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
```

## 5. Validación funcional independiente

El código se copió a una prueba independiente con Python 3; no se dio por válida solo porque el proceso de inferencia terminara con código 0.

Resultados observados:

| Caso | Resultado |
|---|---|
| `factorial(0)` | PASS — `1` |
| `factorial(1)` | PASS — `1` |
| `factorial(5)` | PASS — `120` |
| `factorial(10)` | PASS — `3628800` |
| `factorial(-1)` | PASS — lanza `ValueError` |
| `factorial(-5)` | PASS — lanza `ValueError` |
| `factorial(2.5)` | PASS — lanza `TypeError` |

**Resultado de validación: 7 comprobaciones superadas.** El script imprimió literalmente `RESULTADO: TODAS LAS PRUEBAS SUPERADAS`.

Matiz de Python: `bool` es una subclase de `int`, así que `isinstance(True, int)` y `isinstance(False, int)` devuelven verdadero. El código generado acepta por ello `True` y `False`; ese comportamiento no se probó y no incumple literalmente el prompt original, pero sería mejor excluir booleanos en una validación de enteros estricta (por ejemplo, `type(n) is not int`).

## 6. Diagnóstico de memoria, procesos y GPU

Comprobaciones efectuadas después de las pruebas:

- `pgrep -af 'llama-cli|llama-server'` no mostró procesos de llama.cpp activos.
- `free -h` informó:
  - RAM total: 14 GiB.
  - RAM usada: 3,9 GiB.
  - RAM libre: 6,5 GiB.
  - Búfer/caché: 5,0 GiB.
  - RAM disponible: 10 GiB.
  - Swap total: 31 GiB.
  - Swap usada: 2,1 GiB.
- Estas cifras describen el estado posterior de la máquina; no deben confundirse con el pico de consumo durante inferencia.
- La consulta de registros del usuario no encontró coincidencias con `gnome-terminal`, `ptyxis`, `konsole`, `terminal`, `segfault` o `crash` durante los últimos 30 minutos.
- La búsqueda en el registro del kernel de los últimos 15 minutos no encontró coincidencias con `oom`, `out of memory`, `killed process`, `NVRM`, `Xid` o `GPU fault`.
- La búsqueda vacía no demuestra que no haya errores fuera de ese intervalo ni en registros que no coincidan con esos términos.
- Se informó que el terminal había «muerto», pero en el reintento funcional se volvió al indicador de shell normalmente; la naturaleza exacta del incidente inicial (cierre de ventana, congelación o retorno al prompt) no quedó determinada.

### Lecturas de GPU en reposo

Tres lecturas de `nvidia-smi` realizadas aproximadamente entre 21:53:00 y 21:53:06:

| Hora local | Potencia informada | VRAM | Utilización | Temperatura |
|---|---:|---:|---:|---:|
| 21:53:00 | 749,67 W | 15 MiB | 9 % | 44 °C |
| 21:53:04 | 6,23 W | 15 MiB | 0 % | 44 °C |
| 21:53:06 | 6,16 W | 15 MiB | 0 % | 45 °C |

La primera lectura de potencia es anómala para esta GPU portátil y no concuerda con las dos siguientes. Se trata como posible anomalía puntual de telemetría, no como consumo real demostrado. En esa comprobación el límite de potencia aparecía como `[N/A]`. La memoria de 15 MiB y la baja utilización se midieron **en reposo, después de finalizar llama.cpp**, no durante la generación. Por tanto, no prueban ni descartan el uso efectivo de GPU durante el benchmark.

## 7. Problemas encontrados y resolución

1. **Respuesta truncada en la primera ejecución.** La prueba inicial terminó con código 0, pero el código estaba incompleto. Se repitió con un prompt más específico y un máximo de 256 tokens.
2. **Opción `--prompt-file` no admitida.** La segunda tentativa fallida terminó con `invalid argument: --prompt-file`. Se resolvió leyendo el archivo con Bash (`PROMPT="$(cat "$PROMPT_FILE")"`) y pasando el contenido mediante `--prompt "$PROMPT"`.
3. **Lectura de potencia de GPU anómala.** Se hicieron tres muestras adicionales; dos informaron aproximadamente 6,2 W y una sola mostró 749,67 W. No hay evidencia suficiente para atribuirle un fallo físico.
4. **Terminal.** La ejecución funcional se completó y devolvió el prompt. No se determinó la causa del incidente inicial.
5. **Hermes y servicios preexistentes.** No se detuvieron procesos ni se modificaron servicios. No se lanzó ningún servicio en el puerto 8080.

## 8. Conclusiones

- **Ejecución local confirmada:** Ling 3.0 Tiny `IQ2_M` carga y genera texto con el build CUDA de llama.cpp indicado en el MSI Ubuntu.
- **Tarea de código superada:** la función factorial generada superó siete comprobaciones funcionales independientes.
- **Rendimiento observado en el reintento funcional:** **62,5 tokens/s de prefill** y **5,4 tokens/s de generación**.
- **Primera ejecución:** **68,7 tokens/s de prefill**, **8,3 tokens/s de generación**, **83,83 s** y **2,89 GiB de RSS máximo**, pero respuesta incompleta.
- Estas mediciones son observaciones de ejecuciones individuales, no una media estadística ni un resultado exhaustivo.
- No se ha medido el RSS máximo de la ejecución funcional ni se ha muestreado la GPU durante la generación.
- No comparar directamente con resultados del GB-BXi7-5500 como si fueran condiciones idénticas: cambian la máquina, la cuantización, el build de llama.cpp, el prompt y los límites de generación.
- La velocidad de generación del reintento funcional fue menor que la de la primera ejecución; la diferencia puede depender del prompt y del contenido generado, por lo que hacen falta repeticiones controladas antes de atribuirla a una causa concreta.

## 9. Artefactos locales

Directorio de trabajo: `$HOME/ling3-rtx3050-bench-20261029`.

- `factorial-prompt.txt`: prompt de la prueba funcional.
- `ling3-iq2m-ngl8.log`: log de la primera ejecución.
- `ling3-iq2m-ngl8-first-run.log`: copia conservada de ese log; SHA-256 documentado en la sección 4.1.
- `ling3-iq2m-ngl8-second-run.log`: tentativa fallida con `--prompt-file`; no es un benchmark válido.
- `ling3-iq2m-ngl8-factorial-retry.log`: log del reintento funcional.
- `ling3-iq2m-ngl8-gpu.csv`: registro de monitorización que solo contiene cabecera y una muestra del proceso fallido; no sirve para demostrar uso de GPU durante la ejecución funcional.

Los logs y el prompt permanecen en el equipo local. Su existencia local se documenta aquí; no se afirma que se hayan subido como archivos separados al repositorio.

## 10. Trabajo pendiente para cerrar el benchmark

1. Repetir la tarea funcional con `/usr/bin/time -v` y guardar el resultado completo, incluyendo RSS máximo, fallos de página, CPU y tiempo total.
2. Monitorizar `nvidia-smi` durante la generación real para registrar VRAM y utilización GPU; verificar que el muestreo coincide temporalmente con el proceso.
3. Calcular y registrar el SHA-256 del log del reintento funcional.
4. Ejecutar al menos tres repeticiones con exactamente los mismos parámetros y prompt; registrar cada resultado por separado antes de calcular una media.
5. Mantener por separado pruebas de calidad funcional y mediciones de rendimiento.
6. Si se necesita una comparación entre equipos, armonizar en lo posible el modelo y la cuantización, versión/build del motor, prompt, contexto, temperatura, número máximo de tokens y protocolo de medida.
7. Opcional: añadir casos explícitos para `True`, `False`, cadenas, números muy grandes y entradas no enteras; anotar que los booleanos se aceptan con la implementación actual.

---
**Registro de estado:** a 29-10-2026, prueba funcional preliminar aprobada; pendiente cerrar las mediciones de memoria y GPU bajo carga.
