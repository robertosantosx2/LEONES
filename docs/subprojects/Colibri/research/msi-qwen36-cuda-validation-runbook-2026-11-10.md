# Runbook de validación Qwen3.6 CUDA en MSI Thin 15

Fecha: 2026-11-10  
Equipo objetivo: MSI Thin 15 B12UC, Ubuntu, RTX 3050 Laptop 4 GiB (sm_86), driver NVIDIA 580.178.04, CUDA Toolkit 13.4, 14 GiB RAM y 31 GiB swap.

Este documento prepara la validación local del trabajo de la rama `research/qwen36-cuda-chain-planner`. No presupone que los tests o la compilación hayan pasado: deben ejecutarse en el MSI y archivarse sus salidas.

## 0. Reglas de seguridad

- No ejecutar todavía con un modelo grande ni con contexto largo.
- No arrancar dos servidores Colibri simultáneamente.
- Registrar el commit exacto probado.
- Mantener el modelo y su configuración actuales; no descargar otro modelo para esta primera validación.
- Si falla la compilación, detenerse y guardar el primer error completo; no continuar con el runtime.

## 1. Obtener exactamente la rama del PR

Desde un terminal Ubuntu:

```bash
cd ~/colibri
git status --short --branch
git fetch origin research/qwen36-cuda-chain-planner
git switch --detach FETCH_HEAD
git rev-parse HEAD
git status --short
```

El commit esperado para esta revisión es el HEAD actual del PR. Comprobarlo en GitHub antes de ejecutar; si la rama ha avanzado, registrar el nuevo SHA.

## 2. Registrar el entorno

```bash
mkdir -p ~/colibri-validation-qwen36-$(date +%Y%m%d-%H%M%S)
OUT=$(ls -dt ~/colibri-validation-qwen36-* | head -1)
{
  date -Is
  git -C ~/colibri rev-parse HEAD
  uname -a
  gcc --version | head -1
  /usr/local/cuda-13.4/bin/nvcc --version
  nvidia-smi
  free -h
  df -h .
} 2>&1 | tee "$OUT/environment.txt"
echo "OUT=$OUT"
```

## 3. Tests C y regresiones fake-CUDA

```bash
cd ~/colibri/c
make test-c 2>&1 | tee "$OUT/test-c.log"
echo "${PIPESTATUS[0]}" > "$OUT/test-c.exit"
```

Este target construye y ejecuta la suite C del repositorio, incluidos los tests de tier Qwen3.6 registrados en el Makefile. Confirmar expresamente en el log que aparece y pasa `test_qwen36_tier_autoplace`. Si no aparece, no dar el test por cubierto.

## 4. Compilación del engine CUDA para sm_86

```bash
cd ~/colibri/c
make clean
make qwen36 CUDA=1 CUDA_HOME=/usr/local/cuda-13.4 CUDA_ARCH=sm_86 2>&1 | tee "$OUT/qwen36-cuda-build.log"
echo "${PIPESTATUS[0]}" > "$OUT/qwen36-cuda-build.exit"
```

Si la compilación falla, conservar el log y no seguir con el runtime. Si el Makefile de la revisión exige otro nombre de variable, registrar el error y ajustar el comando de forma explícita, sin sustituir silenciosamente el target.

## 5. Runtime corto: cadena activada y control CPU/per-matrix

Usar la ruta real del GGUF/modelo ya instalado. No adivinar el nombre ni la ruta:

```bash
find ~/colibri ~/models ~/.cache -type f \( -iname '*qwen*3.6*.gguf' -o -iname '*qwen36*' \) 2>/dev/null | head -30
```

Cuando se conozca la ruta, ejecutar primero una única petición corta con `COLI_CUDA_CHAIN=1`, contexto pequeño y salida limitada. Registrar stdout/stderr, PID, consumo VRAM/RAM y código de salida. Repetir el mismo prompt y parámetros con `COLI_CUDA_CHAIN=0` como control. No comparar velocidad con una única repetición.

Antes de cada ejecución:

```bash
nvidia-smi
free -h
```

Después:

```bash
nvidia-smi
free -h
```

## 6. Pruebas de rechazo/recuperación

La primera ronda no debe provocar OOM deliberadamente. Una vez que los dos arranques básicos sean estables:

1. Ejecutar una configuración que haga que la cadena decline por falta de colocación, verificando que la ruta por-matriz continúa.
2. Probar el fallo de setup con el mecanismo de fault injection disponible, sólo después de revisar el punto exacto donde se consume la variable y el impacto esperado.
3. Confirmar que el proceso no se cierra, que no hay corrupción y que el log indica la ruta de fallback.
4. Comparar VRAM antes/después y repetir el arranque para comprobar que no queda el contexto en un estado inutilizable.

No activar `COLI_CUDA_CHAIN_FAULT` hasta que se haya confirmado en el código de la revisión qué fase y qué número de fallo activa; no asumir que simula un error de inicialización.

## 7. Evidencias que deben archivarse

- `environment.txt`
- `test-c.log` y `test-c.exit`
- `qwen36-cuda-build.log` y `qwen36-cuda-build.exit`
- logs completos de ambos runtimes
- prompt exacto, contexto, tokens generados y configuración
- `nvidia-smi` y `free -h` antes/después
- SHA probado y resultado de cada fase

## Estado conocido al redactar

- El parche de presupuesto y admisión automática tiene tests fake-CUDA añadidos, todavía pendientes de ejecución.
- La limpieza común de setup fallido y el registro de `cc_shutdown()` están implementados en el fork, pero todavía no tienen una prueba de integración específica ni una compilación confirmatoria.
- No se han medido tiempos de prefill/decode para este parche.
- No se declara validación CUDA ni rendimiento hasta completar las fases anteriores.
