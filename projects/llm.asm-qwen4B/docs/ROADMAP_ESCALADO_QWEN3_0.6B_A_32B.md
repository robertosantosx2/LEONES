# Hoja de ruta de escalado: Qwen3-0.6B → 32B

**Estado:** diseño de capacidad y arquitectura; no implica compatibilidad implementada.
**Rama:** `research/llm-asm-qwen4b-2026-11-26`
**Upstream auditado:** `alesha-pro/llm.asm` en `48feccbfd57cb669440f31ff64958d95bb8b848e`.

## 1. Objetivo

Preparar llm.asm para que la adaptación no quede limitada a Qwen3-4B. El objetivo de diseño es poder evaluar progresivamente Qwen3-8B, Qwen3-14B y Qwen3-32B sin rehacer el formato, el validador ni el exportador para cada tamaño.

Qwen3-0.6B seguirá siendo la regresión ligera y reproducible. Qwen3-4B será el primer perfil de ampliación. 8B, 14B y 32B son objetivos posteriores, sujetos a compatibilidad arquitectónica, límites del motor, memoria, direccionamiento y validación numérica.

No se declara soporte para ninguno de los tamaños futuros por el mero hecho de documentarlos.

## 2. Principio de diseño: separar arquitectura, formato y capacidad

No codificar el tamaño del modelo como una identidad fija. El sistema debe distinguir:

1. **Perfil de arquitectura:** dimensiones, número de capas/cabezas, tipo de atención, normalizaciones, RoPE, vocabulario, embeddings atados, tokens especiales y variantes de bloque.
2. **Formato de artefacto:** versión ASMBIN, cuantización, tipo de escalas, layout, offsets, alineación y tokenizer.
3. **Capacidades del motor:** límites de K, dimensiones máximas, tipos numéricos, tamaños de buffers, direccionamiento, memoria disponible y operadores implementados.
4. **Presupuesto de ejecución:** pesos residentes o mapeados, KV-cache, activaciones, logits, tokenizer, runtime, memoria temporal y margen de seguridad.
5. **Evidencia:** validación estructural, paridad numérica, pruebas funcionales y mediciones de rendimiento.

El validador no debe inferir la arquitectura a partir del nombre comercial del modelo. Debe validar un manifiesto de arquitectura explícito contra las restricciones del motor.

## 3. Perfiles de modelo

Los valores exactos deben obtenerse de los `config.json` y metadatos de los checkpoints oficiales concretos que se seleccionen. La tabla siguiente es una matriz de objetivos, no una fuente normativa de dimensiones.

| Perfil | Prioridad | Función en el plan | Estado |
|---|---:|---|---|
| Qwen3-0.6B | Regresión | Validación rápida, CI y baseline | Ejecutado en CPU; evidencia archivada |
| Qwen3-4B | 1 | Primer modelo de mayor escala | Auditoría estática; no ejecutado |
| Qwen3-8B | 2 | Validar escalado de capas y pesos | Pendiente |
| Qwen3-14B | 3 | Validar dimensiones mayores y presión de memoria | Pendiente |
| Qwen3-32B | 4 | Objetivo de estrés para memoria, offsets y ejecución por streaming | Pendiente |

Antes de añadir un perfil aceptado, registrar para el checkpoint concreto:
- repositorio y revisión inmutable;
- `architectures`, `model_type`, configuración completa y hashes;
- `hidden_size`, `intermediate_size`, `num_hidden_layers`;
- `num_attention_heads`, `num_key_value_heads`, `head_dim` si existe;
- tipo de atención y cualquier patrón de capas híbridas;
- dimensiones reales de cada tensor safetensors;
- RoPE, RMSNorm, QK-Norm y sesgos;
- vocabulario, tokenizer, merges y tokens especiales;
- tying de embeddings y salida;
- dtype original y cuantización objetivo.

No asumir que todos los modelos con nombre Qwen3-NB comparten exactamente la misma topología o implementación de atención. El checkpoint y sus tensores son la autoridad.

## 4. Generalización del validador ASMBIN

El validador definido en `ASMBIN_VALIDATOR_SPEC.md` debe evolucionar de dos perfiles concretos a un esquema extensible:

- Parser de cabecera y secciones independiente de perfiles.
- Descriptor de arquitectura explícito y versionado.
- Validación de dimensiones por rol de tensor, no por igualdad simplista entre dimensiones.
- Cálculo de tamaños con enteros de ancho suficiente y overflow comprobado.
- Rangos de archivo validados antes de crear vistas o punteros.
- Comprobación de alineación, solapamiento, strides y padding.
- Validación de tokenizer y de su identidad respecto al checkpoint.
- Política de capacidades separada de la validez estructural: un archivo puede estar bien formado y ser demasiado grande o usar una operación no soportada por el motor.
- Rechazo explícito de arquitecturas u operadores desconocidos; nunca aceptación permisiva.

No fijar un máximo universal de dimensiones basado en Qwen3-4B. El límite actual `Q8_MAX_K=16384` es una restricción de implementación del kernel, no una propiedad del formato ni de la familia. Debe exponerse como capacidad declarada del backend y comprobarse para cada dimensión K efectiva. Si 8B/14B/32B exceden el límite, las opciones serán ampliar el kernel/buffers, procesar por bloques o rechazar el perfil; no truncar ni envolver dimensiones.

## 5. Exportador: streaming y memoria acotada

El exportador debe prepararse para modelos cuyos pesos cuantizados ocupen varios GiB y cuyo checkpoint original/pico temporal sea mayor:

- Inspeccionar metadatos Safetensors sin materializar todos los tensores.
- Exportar tensor a tensor o por bloques acotados.
- Cuantizar filas/bloques sin copias completas BF16→FP32 cuando sea posible.
- Mantener temporales acotados y liberarlos determinísticamente.
- Escribir a archivo temporal, validar estructura, tamaños y hashes y publicar mediante rename atómico.
- Reanudar o fallar de forma explícita ante falta de espacio; nunca dejar un artefacto parcial presentado como válido.
- Registrar RSS máximo, memoria disponible, swap, espacio libre, bytes leídos/escritos y duración por tensor.
- Proporcionar estimación previa de espacio y memoria pico con margen conservador.
- Preservar el checkpoint original y los logs de exportación.

No descargar los modelos de mayor tamaño hasta que la ruta de inspección de metadatos, cálculo de presupuesto y exportación acotada esté diseñada y probada con fixtures pequeños.

## 6. Motor de inferencia y memoria

La ampliación debe separar los límites artificiales de los límites físicos:

- Reemplazar buffers globales dimensionados para un único máximo por capacidades explícitas o buffers dimensionados tras validar el modelo.
- Evitar reservar grandes arrays temporales para dimensiones que no se usan.
- Evaluar mmap de pesos y acceso por demanda; medir RSS real, no confundir tamaño virtual con páginas residentes.
- Planificar KV-cache a partir de capas, longitud de contexto, KV heads, head_dim y dtype real de K/V.
- Permitir límites de contexto configurables y rechazar solicitudes que excedan el presupuesto.
- Medir por separado memoria de pesos, KV-cache, activaciones, logits, tokenizer, runtime y temporales.
- Considerar ejecución por capas/bloques y estrategias out-of-core como una línea separada; no confundirlas con soporte directo del motor actual.
- Añadir backpressure y errores de capacidad previsibles antes de OOM cuando sea posible.

La fórmula de KV-cache debe derivarse del perfil y del dtype:
`2 × n_layers × context × n_kv_heads × head_dim × bytes_per_element`.
No reutilizar los números de Qwen3-4B para otros modelos.

## 7. Bare-metal y direccionamiento

La ruta Linux x86-64 se validará primero. La ruta bare-metal es un objetivo independiente.

El diseño bare-metal actual inspeccionado usa Multiboot 1 con campos de módulo de 32 bits, mapa de identidad de 0–4 GiB y allocator bajo 3,75 GiB. Esto no es una base adecuada para prometer carga general de artefactos de varios GiB, aunque el tamaño de un archivo por sí solo no prueba una imposibilidad matemática en cualquier colocación.

Antes de 8B/14B/32B en bare-metal se necesitará un diseño específico para:
- protocolo de arranque y módulos de más de 4 GiB;
- paginación y mapeo de memoria física;
- allocator y regiones reservadas;
- carga segmentada o streaming desde almacenamiento;
- límites de direcciones y tamaños de archivo de 64 bits;
- memoria de trabajo y KV-cache independientes de los pesos;
- recuperación ante memoria insuficiente.

No introducir este rediseño dentro del primer cambio Linux/ASMBIN.

## 8. Estrategia de validación por escalones

1. **0.6B:** conservar todos los tests y resultados existentes como baseline inmutable.
2. **Fixtures:** perfiles sintéticos sin pesos reales para validar dimensiones, strides, overflow, offsets y límites.
3. **4B:** primer checkpoint real; contexto inicial pequeño; comparación tokenizador/logits contra referencia.
4. **8B:** solo después de cerrar 4B; comprobar si el kernel Q8 actual y el presupuesto de memoria son suficientes.
5. **14B:** añadir medición de memoria pico, carga mmap y presión de RAM/swap; no iniciar benchmarks sin umbrales de parada.
6. **32B:** primero análisis de capacidad y estrategia de ejecución; no asumir que la ejecución residente en MSI es viable. Puede servir como perfil de estrés de parser/exportador o como objetivo de una plataforma futura.
7. Cada salto conserva el anterior como regresión. Ningún benchmark sustituye la validación numérica y funcional.

## 9. Criterios de promoción de un perfil

Un perfil solo puede pasar de `planned` a `supported` cuando tenga:
- configuración oficial fijada y hashes;
- descriptor de arquitectura y formas reales de tensores;
- exportación completa y reproducible;
- artefacto ASMBIN validado estructuralmente;
- tokenización idéntica a la referencia en corpus de prueba;
- comparación de logits con tolerancias documentadas;
- generación funcional y repetible;
- pruebas de contexto y límites de memoria;
- mediciones con logs, configuración y manifiesto;
- CI de fixtures y regresiones anteriores.

Estados permitidos: `planned`, `audited`, `exportable`, `validated`, `supported`. No usar “compatible” como sinónimo de “las dimensiones caben”.

## 10. Secuencia de trabajo inmediata

- [ ] Mantener Issue #289 como primer entregable: validador ASMBIN genérico y fixtures.
- [ ] Ampliar fixtures para que no estén acoplados solo a 0.6B/4B.
- [ ] Crear un esquema de perfiles de arquitectura versionado.
- [ ] Añadir estimador de tamaños por tensor, pesos, KV-cache y presupuesto de ejecución.
- [ ] Diseñar exportador incremental con memoria pico acotada.
- [ ] Revisar el límite Q8_MAX_K y decidir entre capacidad configurable, kernel por bloques o límite explícito.
- [ ] Cerrar y validar Qwen3-4B antes de iniciar descarga de Qwen3-8B.
- [ ] Repetir el ciclo de evidencia para 8B, 14B y 32B, sin saltarse escalones.

## 11. Restricciones operativas

- No descargar ni exportar todavía Qwen3-4B/8B/14B/32B.
- No ejecutar pruebas ni benchmarks en el MSI sin solicitar la fase local cuando el código y los fixtures estén listos.
- No modificar el clon upstream fijado.
- No tocar el checkout principal de LEONES ni sus cambios ajenos a este subproyecto.
- Mantener todos los datos y artefactos históricos.
- No afirmar que 32B cabe en el MSI ni que el motor actual soporta ejecución out-of-core.
