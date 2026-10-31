# Open-dCoder — cuaderno detallado del experimento V1/V2

**Fecha:** 2026-10-31  
**Equipo:** Ubuntu, MSI Thin 15 B12UC, Intel Core i7-12650H (16 hilos), 14.8 GiB RAM, NVIDIA RTX 3050 Laptop (4 GiB VRAM), driver 580.178.04, CUDA 13.0.  
**Modelo:** `fredzzp/open-dcoder-0.5B`, snapshot HF `d0d86d5b99960c05258bb1f8265dd91564dbac67`.  
**Estado:** MEASURED — benchmark repetido de una tarea, con validación funcional V2. No es un benchmark general de inteligencia.

Este cuaderno complementa el [informe principal](README.md) y conserva la metodología, las correcciones del validador y los resultados por versión. La tabla V2 es la referencia vigente; V1 y las mediciones exploratorias se conservan como histórico.

## 1. Entorno reproducible conocido

| Elemento | Valor |
|---|---|
| SO | Ubuntu |
| Equipo | MSI Thin 15 B12UC |
| CPU | Intel Core i7-12650H |
| Hilos lógicos | 16 |
| RAM | 14.8 GiB |
| GPU | NVIDIA RTX 3050 Laptop |
| VRAM física | 4 GiB |
| Driver / CUDA | 580.178.04 / 13.0 |
| Python | 3.12.15 |
| PyTorch | 2.11.0+cu128 |
| Transformers | 4.54.1 |
| huggingface-hub | 0.36.2 |
| datasets | 4.4.1 |
| torchdata | 0.11.0 |
| einops | 0.8.2 |
| Directorio repo | `~/open-dcoder/Open-dLLM` |
| Entorno virtual | `~/open-dcoder/.venv` |
| Instalación | editable, `open-dcoder 0.1.0` |

### Modelo y archivos

- 494,032,768 parámetros.
- Arquitectura Qwen2 adaptada para difusión de texto.
- BF16; pesos Safetensors: 1,260,367,448 bytes (~1.174 GiB).
- Tokenizer Qwen2TokenizerFast, vocabulario 151,666.
- Token máscara `<M>`, ID 151665.
- Snapshot HF: `d0d86d5b99960c05258bb1f8265dd91564dbac67`.
- La carga en GPU se completó correctamente.

### Ajustes locales de compatibilidad

Los imports eager de módulos no necesarios cargaban SeedOmni y componentes multimodales MoVQGAN incompatibles con Transformers 4.54.1 por el símbolo `PILImageResampling`. Para desbloquear el camino Qwen2 se reemplazaron temporalmente los inicializadores:

- `veomni/models/__init__.py`
- `veomni/models/transformers/__init__.py`
- `veomni/data/__init__.py`

Backups conservados con sufijo `.open-dcoder-backup`. Son cambios locales temporales, no una solución upstream. No restaurar ni eliminar backups sin revisar primero el entorno. Se ejecutó `model.diffusion_generate`, no `model.generate()`. El warning de estado distribuido no inicializado es esperado en esta ejecución single-process.

## 2. Tarea y protocolo

Prompt de evaluación (contenido funcional): escribir solo código Python con una función recursiva `factorial(n)`, lanzar `ValueError` para enteros negativos e incluir `print(factorial(5))`.

Parámetros comunes a V1 y V2:

| Parámetro | Valor |
|---|---|
| `max_new_tokens` | 64 posiciones |
| `steps` | 16, 32, 64, 128 |
| `alg` | `p2` |
| `temperature` | 0.2 |
| `top_k` | 200 |
| `alg_temp` | 0.5 |
| Secuencias | 1 |
| Historial | desactivado |
| Warmup | 1 por configuración, excluido |
| Repeticiones medidas | 3 por configuración |
| Semillas | mismas semillas en V1/V2 |

El tiempo se midió con reloj monotónico y sincronización CUDA alrededor de la generación. La tasa se calcula como 64 posiciones divididas por la mediana de tiempo. La VRAM es el máximo asignado por PyTorch observado en la región medida. No equivale a tokens/s autoregresivos.

## 3. Evolución del validador

### V1 — problema detectado

El extractor V1 no manejaba bien texto introductorio, bloques Markdown ni métodos dentro de `class Solution`. Clasificaba como inválidas respuestas que contenían código Python válido. Por tanto, el 0/3 histórico de V1 no permite concluir que todas las generaciones fueran erróneas.

### V2 — corrección

El script `~/open-dcoder/benchmark_opendcoder_v2.py` incorporó:
1. extracción de bloques Markdown y código rodeado de texto;
2. detección de función independiente o método de `class Solution`;
3. análisis sintáctico con `ast.parse`;
4. whitelist de nodos AST;
5. ejecución aislada de la función/método extraído;
6. comprobaciones de `factorial(5) == 120` y de que un argumento negativo provoca `ValueError`.

El runner V1 está en `~/open-dcoder/benchmark_opendcoder.py`; se preservó una copia como `~/open-dcoder/benchmark_opendcoder_v1.py`.

**Límites de V2:** no ejecuta el módulo completo ni imports/instrucciones externas; aun así, la whitelist AST no es un sandbox de seguridad. Además, el validador no comprueba por separado que se haya incluido literalmente `print(factorial(5))`. Comprueba la función/método, no todos los requisitos de formato del prompt.

## 4. Resultados V1 — histórico

| Pasos | Mediana (s) | Posiciones/s | Pico VRAM | Resultado del validador V1 |
|---:|---:|---:|---:|---|
| 16 | 0.446 | 143.34 | 1.184 GiB | 0/3 marcadas válidas |
| 32 | 0.891 | 71.80 | 1.184 GiB | 0/3 marcadas válidas |
| 64 | 1.774 | 36.08 | 1.184 GiB | 0/3 marcadas válidas |
| 128 | 3.521 | 18.17 | 1.184 GiB | 0/3 marcadas válidas |

La validación V1 quedó invalidada por falsos negativos del extractor. Las cifras de tiempo siguen siendo útiles como referencia histórica, no como resultado funcional.

## 5. Resultados V2 — referencia vigente

| Pasos | Mediana (s) | Mín (s) | Máx (s) | Posiciones/s | Pico VRAM | Sintaxis | Funcional |
|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 16 | 0.456 | 0.453 | 0.458 | 140.30 | 1.184 GiB | 3/3 | 3/3 |
| 32 | 0.906 | 0.905 | 0.908 | 70.66 | 1.184 GiB | 3/3 | 0/3 |
| 64 | 1.809 | 1.809 | 1.812 | 35.37 | 1.184 GiB | 3/3 | 3/3 |
| 128 | 3.583 | 3.578 | 3.636 | 17.86 | 1.184 GiB | 3/3 | 3/3 |

Los contadores de sintaxis y funcionalidad se refieren a las tres salidas medidas; el warmup se excluye.

### Análisis de las salidas

- **16 pasos:** 3/3 sintácticas y 3/3 funcionales. Función recursiva independiente correcta, con `ValueError` para negativos. Algunas respuestas añadían texto introductorio y comillas triples espurias; el extractor recuperó la función.
- **32 pasos:** 3/3 sintácticas y 0/3 funcionales. Las respuestas incluían una clase `Solution`, pero el caso recursivo llamaba a `factorial(n-1)` como nombre global no definido en vez de llamar al método. También devolvía 0 para negativos en lugar de lanzar `ValueError`. Es un fallo real de código, no del parser.
- **64 pasos:** 3/3 sintácticas y 3/3 funcionales. Función recursiva correcta y rechazo de negativos.
- **128 pasos:** 3/3 sintácticas y 3/3 funcionales. La salida podía contener texto introductorio y Markdown, pero el extractor localizó la función válida.

## 6. Comparación de rendimiento V1/V2

| Pasos | V1 posiciones/s | V2 posiciones/s | Variación aprox. |
|---:|---:|---:|---:|
| 16 | 143.34 | 140.30 | -2.1 % |
| 32 | 71.80 | 70.66 | -1.6 % |
| 64 | 36.08 | 35.37 | -2.0 % |
| 128 | 18.17 | 17.86 | -1.7 % |

Las diferencias pequeñas son compatibles con ruido/overhead; no demuestran cambio de rendimiento del motor. V2 mejora sobre todo la calidad de la evaluación, al separar sintaxis y funcionalidad y extraer correctamente Markdown/clases.

## 7. Auditoría de temperatura y top-k

Transformers mostró el warning de que `temperature` y `top_k` no eran flags de generación válidos y podían ignorarse. La inspección del código confirmó:

- `MDMGenerationConfig.__init__` extrae `temperature`, `top_k`, `steps`, `alg`, `alg_temp`;
- `_mdm_sample` lee `generation_config.temperature` y `generation_config.top_k`;
- `sample_tokens()` escala logits por temperatura cuando corresponde y aplica top-k antes de softmax;
- con temperatura positiva utiliza muestreo categórico;
- en `alg="p2"`, `sample_tokens` recibe temperatura y top-k;
- `alg_temp` afecta ramas Gumbel-TopK como `entropy`, `maskgit_plus` y `topk_margin`, pero no se utiliza igual en la rama `p2`.

Conclusión prudente: existen rutas de código que consumen temperatura/top-k, pero el warning no se ha eliminado y falta una prueba A/B controlada. Se registra como parámetros inspeccionados en el código, con efecto experimental pendiente de confirmación diferencial.

## 8. Mediciones exploratorias previas

No mezclar estas cifras con V1/V2:

- Primera generación de 64 posiciones: 1.622 s, 39.47 posiciones/s, pico VRAM 1.149 GiB; salida no válida.
- Tres ejecuciones factorial de 16 pasos: 1.276 s, 0.471 s y 0.471 s; media 0.739 s; pico VRAM aproximado 1.215 GiB.
- Otro barrido inicial 16/32/64/128 registró 1.013, 0.883, 1.759 y 3.506 s, con 63.21, 72.49, 36.39 y 18.25 posiciones/s. No se considera el benchmark de referencia porque fue previo a la revisión de protocolo/validador.

## 9. Conclusiones

- La RTX 3050 ejecutó Open-dCoder 0.5B BF16 en GPU.
- V2 midió un pico de 1.184 GiB asignados en todas las configuraciones.
- En la tarea factorial, 16, 64 y 128 pasos lograron 3/3 soluciones funcionales; 32 pasos 0/3.
- 16 pasos fue la configuración más rápida entre las que superaron las pruebas funcionales: mediana 0.456 s y 140.30 posiciones/s.
- 16 pasos fue ~4 veces más rápido que 64 y casi 8 veces más rápido que 128 en esta tarea.
- No se puede generalizar el resultado a otras tareas ni afirmar que más pasos mejoran siempre la calidad.
- No se asigna puntuación Artificial Analysis ni ranking de inteligencia.
- No comparar directamente posiciones/s con tokens/s autoregresivos.

## 10. Limitaciones y trabajo pendiente

1. Añadir SHA exacto del repo Open-dLLM, hashes de scripts, `pip freeze`, sistema/kernel y comandos exactos.
2. Conservar salidas brutas, logs, seeds y configuración por ejecución.
3. Ampliar a factorial, Fibonacci, búsqueda binaria, ordenación, cadenas y estructuras de datos.
4. Definir tests externos por tarea: casos normales, límites, negativos, errores y excepciones.
5. Medir por separado extracción, sintaxis, funcionalidad, formato y cumplimiento del prompt.
6. Añadir más semillas y repeticiones; publicar dispersión y tasa de éxito.
7. Probar 8/16/32/64/128 pasos.
8. Hacer ablaciones de temperatura, top-k y algoritmo para confirmar efecto.
9. Medir tiempo de carga, latencia inicial, VRAM asignada/reservada, RAM, temperatura y potencia.
10. Mantener ejecución de código generado en entorno aislado; el validador AST no reemplaza un sandbox.
11. Comparar solo con protocolos y unidades explícitamente equivalentes.

## 11. Referencias

- [Open-dLLM](https://github.com/zhangsheng93/Open-dLLM)
- [Modelo fredzzp/open-dcoder-0.5B](https://huggingface.co/fredzzp/open-dcoder-0.5B)
- [Informe principal Open-dCoder en LEONES](README.md)
- [Índice de subproyectos LEONES](../README.md)
