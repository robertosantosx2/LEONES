# Clover-35B-A3B-Preview — ficha experimental LEONES

- **Estado:** experimental; investigación documental, no validado en hardware local.
- **Fecha de registro:** 2026-10-28.
- **Familia:** modelo de lenguaje MoE con generación de texto por difusión en bloques.
- **Tamaño anunciado:** 35B parámetros totales y aproximadamente 3B activos por token.
- **Contexto anunciado:** hasta 128K tokens.
- **Bloque de difusión anunciado:** 32 posiciones.
- **Arquitectura anunciada:** 40 capas, 256 expertos enrutados, top-8 y un experto compartido; componentes recurrentes Gated DeltaNet y atención bidireccional dentro del bloque.
- **Modalidad:** texto; no asumir capacidades nativas de imagen, audio o vídeo.
- **Fuentes primarias:**
  - Artículo de lanzamiento: https://diffuspace.ai/blog/clover-35b/
  - Repositorio: https://github.com/DiffuSpace/Clover-35B-A3B-Preview
  - Modelo: https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview

## Interés para LEONES

Candidato de investigación para estudiar modelos MoE de difusión, generación paralela por bloques, cuantización y decodificación autoespeculativa. Puede ser relevante para cargas de programación, agentes y razonamiento, pero los resultados publicados por el desarrollador no equivalen a una evaluación independiente ni garantizan el mismo rendimiento en otros equipos.

## Viabilidad en el equipo de referencia

**Equipo:** Ubuntu, Intel Core i7-12650H, 16 GB de RAM y NVIDIA RTX 3050 Laptop con 4 GB de VRAM.

| Escenario | Evaluación preliminar |
|---|---|
| Carga completa BF16 en GPU | No viable; el mínimo teórico de pesos ronda 70 GB. |
| Pesos INT4 íntegramente en GPU | No viable; el mínimo teórico ronda 17,5 GB, antes de escalas, metadatos y memoria de inferencia. |
| INT4 con descarga a RAM | Muy improbable con 16 GB de RAM; requiere medir el formato y la memoria real del backend. |
| Descarga de expertos a RAM/SSD | Experimental; no se considera disponible hasta verificar soporte explícito en el backend y reproducir una prueba. |
| Servicio remoto para evaluar calidad | Opción práctica para estudiar el modelo sin cargarlo en el equipo local. |

Las cifras de memoria son cálculos teóricos (parámetros × bits por parámetro), no mediciones del artefacto real. El tamaño de los archivos cuantizados puede ser mayor y el proceso necesita memoria adicional para estados, activaciones, contexto, buffers y el sistema operativo. El *swap* no sustituye a la RAM rápida y puede hacer que la inferencia sea impracticablemente lenta.

## Plan de validación

1. Verificar en el repositorio oficial los formatos publicados, requisitos, licencia exacta de cada artefacto y estado del soporte de llama.cpp/SGLang.
2. Determinar si existe un formato compatible con descarga de expertos y qué parte de los pesos debe permanecer residente.
3. Antes de descargar pesos grandes, estimar espacio en disco y presupuesto máximo de RAM/VRAM.
4. Solo si supera las comprobaciones anteriores, ejecutar una prueba aislada y registrar versión del backend, cuantización, contexto, tiempo de carga, pico de RAM/VRAM, prefill, tokens/s, estabilidad y calidad.
5. Comparar con una carga de referencia en el mismo equipo y con idéntico protocolo.

## Criterio de clasificación

Mantener como **experimental / pendiente de reproducibilidad**. No marcar como ejecutable en la RTX 3050 de 4 GB ni incorporar cifras de rendimiento del fabricante como resultados LEONES. No se ha realizado una ejecución local de Clover durante la elaboración de esta ficha.

## Nota de licencia

El artículo/repo anuncian licencia Apache; antes de redistribuir pesos o derivados, verificar el archivo de licencia y las condiciones aplicables al artefacto concreto publicado en el repositorio oficial.
