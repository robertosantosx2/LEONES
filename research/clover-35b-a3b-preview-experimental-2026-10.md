# Clover-35B-A3B-Preview

> **Clasificación LEONES:** experimental · investigación documental · no validado en hardware local  
> **Fecha de registro:** 28 de octubre de 2026

## Resumen ejecutivo

Clover-35B-A3B-Preview es un modelo de lenguaje que combina una arquitectura *Mixture of Experts* (MoE) con generación de texto por difusión en bloques. Es relevante para LEONES como caso de estudio de inferencia MoE, generación paralela y decodificación especulativa. Las características que siguen proceden de los materiales publicados por el proyecto; no constituyen una verificación independiente.

## Ficha técnica anunciada

| Campo | Valor anunciado |
|---|---|
| Parámetros totales | 35B |
| Parámetros activos | Aproximadamente 3B por token |
| Capas | 40 |
| Expertos enrutados | 256 |
| Enrutamiento | Top-8 y un experto compartido |
| Bloque de difusión | 32 posiciones |
| Contexto máximo anunciado | Hasta 128K tokens |
| Componentes de arquitectura | Gated DeltaNet y atención bidireccional dentro del bloque |
| Modalidad | Texto; no atribuir capacidades nativas de imagen, audio o vídeo sin evidencia específica |
| Licencia | El proyecto anuncia Apache; comprobar el archivo de licencia del código y las condiciones del artefacto de pesos antes de redistribuir |

**Importante:** 3B parámetros activos no significa que el modelo solo necesite memoria para 3B parámetros. Los expertos que no participan en un token también deben estar almacenados en memoria o cargarse mediante una estrategia de *offloading/streaming* compatible.

## Fuentes primarias

- [Artículo de lanzamiento de DiffuSpace](https://diffuspace.ai/blog/clover-35b/)
- [Repositorio oficial](https://github.com/DiffuSpace/Clover-35B-A3B-Preview)
- [Ficha del modelo en Hugging Face](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview)

Los resultados y cifras de rendimiento publicados por los autores deben identificarse como resultados del desarrollador, no como mediciones independientes de LEONES.

## Viabilidad en el equipo de referencia LEONES

**Equipo de referencia:** Ubuntu, Intel Core i7-12650H, 16 GB de RAM, NVIDIA RTX 3050 Laptop con 4 GB de VRAM.

| Escenario | Evaluación preliminar |
|---|---|
| Pesos BF16 completos en GPU | No viable: el mínimo teórico de los pesos ronda 70 GB. |
| Pesos INT4 completos en GPU | No viable: el mínimo teórico ronda 17,5 GB, sin contar escalas, metadatos ni memoria de inferencia. |
| INT4 con descarga a RAM | Muy improbable con 16 GB de RAM; el archivo y la memoria adicional pueden superar el presupuesto disponible. |
| Descarga de expertos a RAM o SSD | Experimental; requiere soporte explícito en el backend, más memoria suficiente y pruebas reproducibles. |
| Evaluación mediante servicio remoto | Alternativa para estudiar la calidad sin cargar el modelo en el equipo local. |

Las cifras anteriores son cálculos teóricos de almacenamiento de pesos (parámetros × bits por parámetro), no tamaños medidos del artefacto publicado ni requisitos completos de ejecución. El formato cuantizado real puede ocupar más. También se necesita memoria para buffers, activaciones, estado recurrente, contexto, runtime y el sistema operativo.

El *swap* no sustituye a la RAM: puede evitar algunos fallos por falta de memoria, pero la paginación intensiva puede volver la inferencia impracticablemente lenta.

### Dictamen para la RTX 3050 de 4 GB

**No clasificar como ejecutable en el equipo actual.** No se ha descargado ni ejecutado Clover en esta máquina. La ejecución INT4 anunciada en una GPU con más VRAM no demuestra viabilidad en 4 GB.

## Plan de validación

1. Revisar el repositorio oficial y confirmar formatos de pesos, requisitos, licencia de cada artefacto y soporte actual de cada backend.
2. Verificar si existe un formato utilizable en Linux y si el backend soporta de forma real la arquitectura de difusión de Clover; no asumir que todas las rutas de inferencia son equivalentes.
3. Determinar si hay *offloading* de expertos compatible y calcular el presupuesto de RAM, VRAM y disco antes de descargar pesos grandes.
4. Si supera los pasos anteriores, ejecutar una prueba aislada y registrar versiones, cuantización, contexto, tiempo de carga, picos de RAM/VRAM, prefill, tokens/s, estabilidad y calidad.
5. Comparar con una carga de referencia en el mismo equipo y con el mismo protocolo. Etiquetar los resultados como **MEASURED** solo si proceden de una ejecución física documentada.

## Criterio de promoción

Mantener en **Experimental** hasta verificar formato, backend y requisitos. Solo promoverlo a candidato ejecutable tras una prueba reproducible. No reutilizar cifras de terceros como mediciones LEONES.

---

*Ficha de investigación; no acredita compatibilidad, rendimiento ni ejecución local.* 
