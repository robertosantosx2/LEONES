# Picchio — subproyecto de LEONES

**Estado:** integración documental inicial; fork de desarrollo pendiente.

## Repositorios

- Upstream: https://github.com/benmaster82/picchio
- Fork de trabajo previsto: https://github.com/robertosantosx2/picchio
- Rama local de investigación existente: `~/picchio-lab`

> El fork bajo `robertosantosx2` todavía no se ha creado. La conexión GitHub disponible en esta sesión permite leer repositorios y escribir archivos, ramas y commits, pero no expone la operación GitHub de crear un fork ni crear un repositorio. No se presenta el upstream como si fuera un fork propio. Cuando el fork exista, se actualizarán aquí la URL, el pin y `.gitmodules`.

## Objetivo

Desarrollar y validar un backend MoE híbrido CPU/CUDA para equipos de recursos limitados, manteniendo una ruta CPU de referencia independiente y verificable.

## Plataforma de referencia

- MSI Thin 15 B12UC
- Intel Core i7-12650H
- NVIDIA RTX 3050 Laptop, 4 GiB VRAM, compute capability `sm_86`
- Ubuntu; CUDA Toolkit 13.4

## Estado técnico inicial (2026-11-08)

- Picchio v0.8.0; modelo de referencia Qwen3-30B-A3B Instruct 2507 convertido a INT4.
- Ejecutable CPU baseline funcional; debe permanecer intacto.
- Backend CUDA compilado como biblioteca compartida y cargado dinámicamente.
- La ruta CUDA de expertos ya ejecuta inferencia real, pero en las pruebas iniciales no supera el baseline CPU: aproximadamente 1.6–1.9 tok/s frente a 1.8–2.2 tok/s en las pruebas CPU comparables.
- El análisis identificó copias H2D síncronas, asignaciones frecuentes y evicciones LRU como posibles costes. Aún no se ha demostrado cuál domina el tiempo.
- La primera optimización autorizada es registrar slabs host con CUDA pinned memory, conservando copias síncronas. No introducir streams ni `cudaMemcpyAsync` en esta fase.

## Reglas de desarrollo

1. Mantener intactos el ejecutable CPU baseline y los artefactos CUDA funcionales existentes.
2. Desarrollar en una rama aislada del fork cuando esté disponible.
3. Compilar bibliotecas experimentales con nombre/ruta separados; no sobrescribir `/tmp/libpicchio_cuda.so`.
4. Cada cambio debe tener diff revisable, compilación, prueba funcional y medición reproducible.
5. Separar claramente resultados **MEASURED** de hipótesis y estimaciones.
6. No afirmar aceleración sin comparación controlada de tokens/s, latencia, uso de VRAM/RAM y estabilidad.
7. Mantener upstream intacto; las integraciones y resultados LEONES viven en este subproyecto.

## Primera línea de trabajo

**CUDA pinned host slabs (sin asincronía):**
- API opcional `pgpu_host_register(ptr, size)` / `pgpu_host_unregister(ptr)`.
- Registro limitado y contabilizado; fallo de registro debe degradar a memoria pageable.
- Desregistro antes de liberar o sustituir un slab; protección frente a llamadas concurrentes del loader/prefetch.
- Limpieza de registros pendientes al apagar el backend.
- Prueba A/B frente a la biblioteca CUDA actual, sin modificar el ejecutable CPU baseline.

## Evidencia y seguimiento

Los cambios de código deben quedar en el fork de Picchio. LEONES conservará metodología, commits de referencia, resultados, logs, métricas y conclusiones en este directorio.
