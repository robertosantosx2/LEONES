# Pithos — trazabilidad de la investigación Intel OpenCL

**Fecha de consolidación:** 2026-11-09  
**Proyecto:** [Pithos](https://github.com/benmaster82/Pithos)  
**Repositorio de trabajo:** [robertosantosx2/Pithos](https://github.com/robertosantosx2/Pithos)  
**Worktree de validación local:** `~/Pithos-opencl-validation-20261109`  
**Rama local:** `validation/intel-opencl-dense-logits`

## 1. Resumen ejecutivo

Se investigó un fallo de lectura de logits en la ruta Intel OpenCL de Pithos, observado al ejecutar el modelo `LFM3-1.7B-Q4_K_M.gguf` en la iGPU Intel UHD del MSI Thin 15 B12UC.

El error reproducible es:

```text
GPU: OpenCL error -5 in read logits
```

El código OpenCL `-5` corresponde a `CL_OUT_OF_RESOURCES`. El trabajo documentado aquí no demuestra que el controlador o la ruta Intel OpenCL hayan quedado reparados. El objetivo del cambio validado es impedir que Pithos continúe una operación con logits no válidos: detectar la pérdida del contexto, abortar la operación y devolver un código de salida no cero en los modos no interactivos y benchmark.

## 2. Entorno de prueba

| Elemento | Valor |
|---|---|
| Sistema | Ubuntu |
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| GPU integrada probada | Intel UHD Graphics, OpenCL |
| GPU dedicada instalada | NVIDIA GeForce RTX 3050 Laptop, 4 GiB |
| Modelo | `LFM3-1.7B-Q4_K_M.gguf` |
| Ruta del modelo | `$HOME/Pithos/models/LFM3-1.7B-Q4_K_M.gguf` |
| Repositorio upstream | `benmaster82/Pithos` |
| Fork | `robertosantosx2/Pithos` |

La prueba de esta campaña seleccionó explícitamente Intel OpenCL, dispositivo 0. No debe interpretarse como una prueba de NVIDIA.

## 3. Historial de investigación

1. Se preparó un clon de trabajo de Pithos para inspeccionar el comportamiento del backend y los mensajes de error.
2. Se identificó la ruta de lectura de logits dense en OpenCL y se revisaron las consultas de capacidades del dispositivo, incluidas las relacionadas con memoria y asignaciones.
3. Se aisló el error de lectura de logits: `OpenCL error -5 in read logits`.
4. Se creó un worktree separado para validar el cambio sin mezclarlo con el clon principal ni con los experimentos previos.
5. Se revisó la propagación del fallo desde la lectura GPU hacia el estado del contexto y el bucle de generación.
6. Se reforzaron los controles de error en generación normal, modo raw y benchmark.
7. Se compiló el worktree y se ejecutaron pruebas reales en Intel OpenCL y CPU-only.

Esta secuencia resume las etapas conservadas en la sesión de trabajo. Los resultados cuantitativos y los comandos reproducibles se registran en las secciones siguientes.

## 4. Cambios locales sometidos a validación

Los cambios pendientes de integrar en el repositorio se encuentran en el worktree indicado; esta documentación no afirma que esos cambios ya formen parte de una rama publicada de Pithos.

### `src/gpu.h` y `src/gpu_opencl.c`

- `gpu_dense_logits()` devuelve un estado de éxito/fallo.
- La espera del evento y el estado de la operación de lectura se comprueban.
- Si falla la lectura, no se considera válido el contenido de logits y se devuelve fallo al llamador.

### `src/model.c`

- El fallo de `gpu_dense_logits()` se propaga al contexto.
- El estado de pérdida GPU se trata como pérdida del contexto.
- La operación actual se aborta en lugar de continuar con logits inválidos.
- El mensaje de diagnóstico queda como:

```text
[GPU context lost: context reset; current operation aborted]
```

### `src/main.c`

- La generación comprueba si `ctx_forward()` devuelve `NULL`.
- Se propaga el estado de fallo a los llamadores.
- Los modos no interactivos devuelven código de salida no cero cuando la operación se aborta.
- El benchmark comprueba warm-up, prefill y generación token a token.
- No se publican métricas TG incompletas cuando se pierde el contexto.
- Las tasas de generación se calculan con los tokens realmente completados.
- En modo interactivo se informa del fallo y se reinician contexto y sampler.

**Caveat de alcance:** `wait_event()` también se utiliza en la ruta MoE de `gpu_dense_wait()`; el caller de esa ruta no se ha validado exhaustivamente en esta campaña. No declarar cobertura completa de MoE.

## 5. Compilación y comprobaciones estáticas

Desde el worktree de validación:

```bash
cd "$HOME/Pithos-opencl-validation-20261109"
bash build.sh --no-install --jobs 2
git diff --check
git status --short
git diff --stat
```

Resultado registrado:

- Build Linux completado: `build/pithos`.
- `git diff --check`: sin errores.
- Archivos modificados en la última inspección: `src/main.c` y `src/model.c`.
- El cambio local de `src/gpu.h` y `src/gpu_opencl.c` forma parte del patch de fail-closed ya preparado en la rama de trabajo anterior; verificar siempre el diff completo de la rama al reproducir la validación.

## 6. Prueba real: Intel OpenCL, generación

Comando:

```bash
cd "$HOME/Pithos-opencl-validation-20261109"
./build/pithos \
  -m "$HOME/Pithos/models/LFM3-1.7B-Q4_K_M.gguf" \
  --gpu opencl --gpu-device 0 \
  -c 1024 -t 8 --reasoning off \
  -p "Explica brevemente qué es una GPU integrada." \
  -n 64 --stats
```

Resultado observado en dos ejecuciones:

```text
GPU: OpenCL error -5 in read logits
[GPU context lost: context reset; current operation aborted]
[turn aborted: context reset or unavailable; resend the prompt]
PITHOS_EXIT_CODE=1
```

Interpretación: el error de Intel OpenCL persiste, pero la operación no continúa con resultados GPU no válidos y el proceso informa del fallo mediante código de salida 1.

## 7. Prueba real: Intel OpenCL, benchmark

Comando:

```bash
cd "$HOME/Pithos-opencl-validation-20261109"
./build/pithos \
  -m "$HOME/Pithos/models/LFM3-1.7B-Q4_K_M.gguf" \
  --gpu opencl --gpu-device 0 \
  -c 128 -t 8 \
  --bench 32,8
```

Resultado:

```text
GPU: OpenCL error -5 in read logits
[GPU context lost: context reset; current operation aborted]
benchmark aborted: context lost during warm-up
PITHOS_BENCH_EXIT_CODE=1
```

No se publicaron métricas TG ni perfil de rendimiento incompletos. El aborto durante warm-up es el comportamiento esperado para esta prueba de fallo.

## 8. Prueba de control: CPU-only

Comando:

```bash
cd "$HOME/Pithos-opencl-validation-20261109"
./build/pithos \
  -m "$HOME/Pithos/models/LFM3-1.7B-Q4_K_M.gguf" \
  --no-gpu -c 512 -t 8 --reasoning off \
  -p "Responde brevemente: ¿qué es una GPU integrada?" \
  -n 32 --stats
```

Resultado:

```text
GPU: off, CPU only
[prompt: 27 tok in 0.21 s = 127.0 tok/s | generation: 32 tok in 0.96 s = 33.43 tok/s]
PITHOS_CPU_EXIT_CODE=0
```

La salida quedó limitada a 32 tokens por el parámetro `-n 32`; no es un fallo de generación.

## 9. Matriz de validación

| Área | Estado | Observación |
|---|---|---|
| Compilación Linux | PASS | Build completado |
| Higiene del diff | PASS | `git diff --check` limpio |
| Intel OpenCL, generación | PASS (fail-closed) | El error se detecta y se aborta la operación |
| Intel OpenCL, benchmark | PASS (fail-closed) | Aborto en warm-up, sin métricas falsas |
| Código de salida ante fallo GPU | PASS | Código 1 |
| CPU-only | PASS | Código 0; 33.43 tok/s en la prueba registrada |
| NVIDIA OpenCL | PENDIENTE | No probado en esta campaña |
| Vulkan | PENDIENTE | No probado en esta campaña |
| Cobertura completa MoE | PENDIENTE | Caller y flujo completo por verificar |

## 10. Limitaciones y conclusiones

- No se ha corregido la causa raíz del `CL_OUT_OF_RESOURCES` en Intel OpenCL.
- No se debe describir el resultado como «Intel OpenCL reparado».
- Lo validado es el manejo seguro del fallo observado: abortar, no reutilizar logits inválidos y devolver un estado de error.
- La generación CPU-only continúa operativa.
- NVIDIA OpenCL, Vulkan y la ruta MoE completa quedan fuera de la evidencia disponible.

**Conclusión:** validación local satisfactoria del comportamiento fail-closed para el fallo Intel OpenCL reproducido. Validación de otros backends y de la ruta MoE completa pendiente.

## 11. Reproducción rápida

```bash
cd "$HOME/Pithos-opencl-validation-20261109"
git status --short
git diff --check
git diff --stat
```

Repetir las pruebas de las secciones 6, 7 y 8 para contrastar el comportamiento.

## 12. Relación con el PR de Pithos

El informe documenta la campaña de validación relacionada con el cambio fail-closed del fork de Pithos. La referencia al PR debe mantenerse como enlace de seguimiento, no como prueba de que el cambio haya sido fusionado:

- [Pithos fork](https://github.com/robertosantosx2/Pithos)
- [PR #1 — Intel OpenCL dense logits fail-closed](https://github.com/robertosantosx2/Pithos/pull/1)

---

*Registro de ingeniería LEONES. Esta entrada conserva resultados observados y distingue explícitamente las pruebas realizadas de las pendientes. No sustituye los logs completos de consola ni el diff Git del worktree local.*
