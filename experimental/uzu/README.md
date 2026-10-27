# Uzu — motor experimental en evaluación

**Estado LEONES:** `EXPERIMENTAL / NOT VERIFIED`
**Fecha de evaluación documental:** 2026-10-27
**Objetivo:** determinar si Uzu puede convertirse en un runtime adicional para inferencia local en Ubuntu, sin sustituir ni degradar los motores ya verificados por LEONES.

> Este documento registra una evaluación de fuentes públicas. No afirma que Uzu se haya compilado, instalado o ejecutado en el equipo del usuario. No contiene mediciones LEONES.

## Resumen ejecutivo

[Uzu](https://github.com/trymirai/uzu) es un motor de inferencia escrito en Rust, con API de alto nivel para sesiones/chat y bindings para varios lenguajes. Su ecosistema incluye [Lalamo](https://github.com/trymirai/lalamo), infraestructura para adaptar/convertir modelos al formato y las operaciones que espera Uzu.

La ruta documentada de Uzu se centra actualmente en Apple Silicon y backend Metal. Aunque el repositorio enumera destinos Linux x86-64 y AArch64 como trabajo en curso, eso **no demuestra soporte Linux listo para uso**. No se ha identificado un backend CUDA documentado ni una ruta de carga directa de GGUF confirmada en las fuentes consultadas.

**Decisión provisional:** mantener Uzu en el catálogo de investigación de LEONES, sin presentarlo como instalable/compatible en Ubuntu hasta completar las pruebas de compilación, carga e inferencia.

## Fuentes primarias

- Uzu: https://github.com/trymirai/uzu
- Lalamo: https://github.com/trymirai/lalamo
- Checkpoint Qwen3.5-4B preparado por Mirai: https://huggingface.co/trymirai/Qwen3.5-4B-M
- Página del runtime: https://trymirai.com/inference-runtime
- Documentación de arquitectura Qwen3.5 MoE en Transformers: https://github.com/huggingface/transformers/blob/main/docs/source/en/model_doc/qwen3_5_moe.md

Las capacidades y la compatibilidad deben reevaluarse contra los README, commits, ModelSpecs y kernels vigentes al ejecutar las pruebas.

## Arquitectura de integración

```text
Catálogo LEONES
  └─ Uzu [EXPERIMENTAL]
       ├─ Revisión de plataforma y backend
       ├─ Lalamo: soporte de arquitectura + conversión de pesos
       ├─ Uzu: kernels/operaciones necesarios
       └─ Pruebas locales aisladas
            ├─ compilación
            ├─ carga del checkpoint convertido
            ├─ prompt mínimo y respuesta no vacía
            └─ benchmark reproducible
```

Lalamo y Uzu son componentes relacionados, pero no equivalentes: una conversión disponible o una especificación de modelo no demuestra por sí sola que el runtime ejecute correctamente todas las operaciones del modelo. El formato de salida de Lalamo tampoco debe confundirse con GGUF.

## Compatibilidad preliminar

| Elemento | Estado documental | Qué falta para promoverlo |
|---|---|---|
| Ubuntu x86-64 / CPU | No confirmado como ruta estable; destino Linux señalado como trabajo en curso | Compilar en Ubuntu y ejecutar una inferencia real |
| Ubuntu + NVIDIA RTX 3050 | No se encontró backend CUDA documentado | Confirmar backend compatible; no asumir que la GPU se usa |
| Metal / Apple Silicon | Ruta principal descrita por el proyecto | No aplica a la máquina Ubuntu/NVIDIA objetivo |
| GGUF existente | Carga directa no confirmada | Documentar conversión soportada o un loader real |
| Lalamo | Herramienta de conversión/adaptación asociada | Verificar ModelSpec, tokenizer, pesos y operaciones requeridas |
| API HTTP compatible con OpenAI | El proyecto describe un servidor y endpoints compatibles | Comprobar en Linux únicamente después de superar la prueba local mínima |

## Modelos objetivo

### Qwen3.5-4B

El repositorio de Hugging Face [trymirai/Qwen3.5-4B-M](https://huggingface.co/trymirai/Qwen3.5-4B-M) ofrece un checkpoint cuantizado de aproximadamente 2,46 GB destinado a Uzu. La ficha del modelo indica que actualmente solo está soportada la inferencia en Apple Silicon.

- **Ubuntu x86-64:** no verificado.
- **RTX 3050 de 4 GB:** no asumir compatibilidad ni ajuste de memoria a partir del tamaño del fichero; hacen falta backend, memoria de runtime, KV cache y prueba real.
- **GGUF Q4_K_M ya disponible:** no se considera directamente reutilizable en Uzu sin una ruta documentada y probada de conversión/carga.

### Qwen MoE

Objetivos de investigación:
- Qwen3-30B-A3B-Instruct-2507 en IQ3_XXS (el checkpoint ya utilizado en comparativas LEONES con otros motores).
- Qwen3.5-35B-A3B, si se dispone de un checkpoint y formato soportados.

**Compatibilidad Uzu: no demostrada para estos modelos.** Qwen3.5 MoE incluye enrutamiento de expertos dispersos, expertos compartidos y bloques de atención específicos. No basta con que un conversor acepte el nombre del modelo: la arquitectura, el tokenizer, el enrutamiento MoE, las operaciones recurrentes/atención y los kernels correspondientes deben estar implementados y funcionar.

La investigación no debe marcar ningún Qwen MoE como ejecutable en Uzu hasta que se complete una prueba de extremo a extremo con salida válida.

## Perfil de máquina de referencia

Usar la máquina Ubuntu del usuario como objetivo de prueba, verificando de nuevo los valores al iniciar cada ensayo:

- MSI Thin 15 B12UC
- Intel Core i7-12650H; 16 CPU lógicas
- 14,8 GiB de RAM del sistema
- NVIDIA RTX 3050 Laptop, 4 GiB de VRAM
- Ubuntu y kernel instalados en el momento de la prueba

No inferir el consumo real ni el rendimiento a partir de la ficha técnica o de resultados publicados en otra máquina.

## Plan de validación y criterios de promoción

Registrar cada etapa de forma independiente; una etapa fallida no se puede saltar.

1. **Fuentes y revisión de código**
   - Registrar URL, commit exacto de Uzu y Lalamo, fecha y licencia.
   - Inspeccionar targets, backend seleccionado, instrucciones de compilación y soporte real del modelo.
2. **Compilación**
   - Ejecutar en Ubuntu sin alterar servicios existentes.
   - Guardar comando, salida completa, versión de Rust y dependencias.
3. **Modelo**
   - Confirmar formato, revisión del checkpoint, tokenizer, cuantización y ruta de conversión.
   - No descargar pesos grandes ni iniciar un servidor como efecto lateral de una simple inspección.
4. **Smoke test**
   - Cargar el modelo y obtener texto de salida no vacío.
   - Guardar código de salida, errores, tiempo de carga y consumo de RAM/VRAM.
5. **Benchmark LEONES**
   - Usar prompts y parámetros versionados y comparables.
   - Medir por separado tiempo de carga, prefill/prompt processing, TTFT, tokens/s de generación, RAM pico, VRAM pico, contexto y errores.
   - Registrar warm-up, repeticiones, versión del motor, commit, modelo, cuantización y hardware.
6. **Clasificación**
   - Antes de ejecutar: `RESEARCH_ONLY`.
   - Compila pero no carga/infiere: `BUILD_VERIFIED`, no compatible en ejecución.
   - Respuesta válida en la máquina: `EXECUTION_VERIFIED`.
   - Benchmark repetible con artefactos: `MEASURED`, solo para esa combinación concreta de hardware, motor y modelo.

No marcar `MEASURED`, `real_installation=true` ni compatibilidad confirmada con evidencia de otra máquina, una conversión satisfactoria o un proceso que termina sin texto.

## Aislamiento operativo

- Mantener Uzu como motor opcional; no modificar el runtime por defecto ni la configuración de ODS/Hermes.
- No cambiar `.env`, puertos compartidos, servicios o motores existentes para probarlo.
- No instalar dependencias globales si el proyecto permite un entorno aislado.
- Conservar logs y artefactos de prueba bajo un directorio específico de Uzu.
- Comparar resultados solo contra ensayos reproducibles en la misma máquina y con condiciones declaradas.

## Licencias

La licencia del código de Uzu/Lalamo no determina la licencia de los pesos. Antes de distribuir una configuración o checkpoint, registrar por separado la licencia del motor, la herramienta de conversión, los pesos, el tokenizer y cualquier artefacto derivado.

## Resultado actual

**Clasificación:** `RESEARCH_ONLY`  
**Ubuntu/NVIDIA:** no verificado  
**Qwen3.5-4B:** checkpoint Uzu identificado; ejecución en Ubuntu no demostrada  
**Qwen MoE:** soporte Uzu no demostrado  
**Benchmark LEONES:** ninguno realizado para Uzu

Este registro debe actualizarse solo con evidencia nueva y reproducible.
