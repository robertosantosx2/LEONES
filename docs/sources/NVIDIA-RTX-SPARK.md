# NVIDIA RTX Spark

## Fuente aportada

Publicación de NVIDIA RTX Spark en X:
https://x.com/NVIDIARTXSpark/status/2095580592704217349

## Estado de procedencia

**Fuente primaria aportada por el proyecto.** La publicación de X se conserva como referencia externa. En la revisión del 4 de septiembre de 2026, X no permitió recuperar automáticamente el contenido de la publicación (HTTP 403), por lo que no se atribuye a este post ningún dato concreto que no haya podido verificarse.

## Contexto técnico verificable

La documentación y comunicación oficial de NVIDIA sobre RTX Spark describen una plataforma para PC Windows centrada en IA local y agentes, basada en un superchip con CPU NVIDIA Grace y GPU Blackwell, memoria unificada de hasta 128 GB y ecosistema CUDA/RTX. NVIDIA afirma soporte para cargas locales de hasta 120B de parámetros y hasta 1 millón de tokens de contexto en determinados escenarios.

Fuente oficial:
https://www.nvidia.com/en-us/products/rtx-spark/

Comunicación oficial NVIDIA/Microsoft, 31 de mayo de 2026:
https://nvidianews.nvidia.com/news/nvidia-microsoft-windows-pcs-agents-rtx-spark

## Relevancia para LEONES

RTX Spark debe incorporarse al conocimiento de LEONES como **plataforma de hardware IA local de memoria unificada**, no como benchmark propio.

Aspectos relevantes para el selector y el conocimiento de hardware:

- memoria unificada de gran capacidad;
- CPU Grace + GPU Blackwell en una plataforma integrada;
- ecosistema CUDA/RTX;
- orientación a inferencia local y agentes;
- posibilidad de ejecutar modelos cuyo tamaño excede la VRAM típica de una GPU de consumo;
- importancia conjunta de capacidad de memoria, ancho de banda, runtime y software stack.

## Tratamiento de evidencia

Los datos declarados por NVIDIA deben mantenerse como **evidencia externa del fabricante** hasta disponer de mediciones reproducibles en hardware real mediante el protocolo de benchmark de LEONES.

No deben convertirse automáticamente en tok/s, latencias o puntuaciones de selección. Cuando existan mediciones independientes o ejecuciones físicas LEONES, deberán registrarse separadamente con modelo, cuantización, runtime, versión, contexto, workload y hardware exactos.

## Relación con el modelo de conocimiento de LEONES

RTX Spark refuerza una distinción ya utilizada por LEONES:

`capacidad de memoria ≠ ancho de banda ≠ rendimiento de inferencia`

Para la recomendación de modelos/runtimes deberán considerarse conjuntamente:

`modelo + cuantización + memoria disponible + ancho de banda + runtime + workload + evidencia real`

---

**Fecha de incorporación:** 2026-09-04
