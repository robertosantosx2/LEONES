# Cosmic Lightning — informe de descarga, procedencia y preparación experimental

**Fecha:** 2026-10-31  
**Estado:** artefactos descargados y auditados localmente; ejecución y benchmark de inferencia pendientes.  
**Equipo de referencia:** Ubuntu en MSI Thin 15 B12UC, Intel Core i7-12650H, 16 CPU lógicas, 14.8 GiB RAM, NVIDIA RTX 3050 Laptop GPU con 4 GiB VRAM.

## 1. Resumen ejecutivo

Se descargaron dos repositorios de Hugging Face:

1. **Modelo original:** [cosmicstack/cosmic-lightning](https://huggingface.co/cosmicstack/cosmic-lightning)
2. **Conversión GGUF:** [bartowski/cosmicstack_cosmic-lightning-GGUF](https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF)

El original ocupa aproximadamente **3.48 GB** y el conjunto de GGUF aproximadamente **25 GB**. Se recopilaron metadatos del repositorio, archivos, hashes y datos de licencia/procedencia. La revisión del original quedó fijada para reproducibilidad.

**Importante:** esta fase no demuestra todavía que el modelo funcione en llama.cpp, TensorFold u otro motor. No se deben atribuir velocidades, prefill, TTFT ni calidad hasta ejecutar pruebas controladas.

## 2. Repositorio original: identificación y revisión

| Campo | Valor |
|---|---|
| Repositorio | `cosmicstack/cosmic-lightning` |
| URL | https://huggingface.co/cosmicstack/cosmic-lightning |
| Revisión descargada | `b5c2c76e95397a0b73cb618a2ec506a755f2832d` |
| Creación indicada por Hub | 2026-10-29 19:33:48 UTC |
| Última modificación indicada por Hub | 2026-10-29 19:59:08 UTC |
| Visibilidad | Público |
| Acceso | No gated; descarga sin autenticación |
| Tarea declarada | `text-generation` |
| Licencia declarada en metadatos | Apache-2.0 |
| Etiquetas relevantes | `lfm3`, `transformers`, `safetensors`, `custom_code` |

### Archivos descargados del original

- `README.md`
- `chat_template.jinja`
- `config.json`
- `configuration_lfm3.py`
- `generation_config.json`
- `lfm3_conv.py`
- `model.safetensors` — aproximadamente 3.3 GB (3,457,635,448 bytes)
- `modeling_lfm3.py`
- `tokenizer.json` — aproximadamente 18 MB
- `tokenizer_config.json`

La presencia de `configuration_lfm3.py` y `modeling_lfm3.py`, junto con las etiquetas del repositorio, apunta a una implementación basada en la familia LFM3 con código de Transformers personalizado. La compatibilidad real con cada runtime debe comprobarse, no suponerse.

## 3. Repositorio GGUF y cuantizaciones descargadas

Repositorio: [bartowski/cosmicstack_cosmic-lightning-GGUF](https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF)

Directorio local utilizado:

`~/modelos/cosmic-lightning/GGUF`

Tamaño aproximado de todo el directorio: **25 GB**.

### Archivos GGUF

| Cuantización | Tamaño (bytes) | Tamaño decimal aproximado |
|---|---:|---:|
| IQ2_M | 651,650,112 | 651.7 MB |
| IQ3_M | 925,533,248 | 925.5 MB |
| IQ3_XS | 812,467,264 | 812.5 MB |
| IQ3_XXS | 780,870,720 | 780.9 MB |
| IQ4_NL | 1,115,636,800 | 1,115.6 MB |
| IQ4_XS | 997,303,360 | 997.3 MB |
| Q2_K | 701,310,016 | 701.3 MB |
| Q3_K_L | 887,579,712 | 887.6 MB |
| Q3_K_M | 847,299,648 | 847.3 MB |
| Q3_K_S | 811,500,608 | 811.5 MB |
| Q4_0 | 1,057,971,264 | 1,058.0 MB |
| Q4_1 | 1,145,353,280 | 1,145.4 MB |
| Q4_K_L | 1,190,388,800 | 1,190.4 MB |
| Q4_K_M | 1,115,636,800 | 1,115.6 MB |
| Q4_K_S | 1,053,787,200 | 1,053.8 MB |
| Q5_K_M | 1,352,451,136 | 1,352.5 MB |
| Q5_K_S | 1,268,171,840 | 1,268.2 MB |
| Q6_K | 1,516,143,680 | 1,516.1 MB |
| Q6_K_L | 1,582,933,056 | 1,582.9 MB |
| Q6_K_S | 1,456,718,912 | 1,456.7 MB |
| Q8_0 | 1,846,238,272 | 1,846.2 MB |
| BF16 | 3,466,625,792 | 3,466.6 MB |

> Los tamaños corresponden a los archivos registrados en la auditoría local. MB se expresa aquí en unidades decimales (1 MB = 1,000,000 bytes).

### Archivos auxiliares del repositorio GGUF

- `cosmicstack_cosmic-lightning-calibration-v6.txt` — aproximadamente 1 MB
- `imatrix.gguf` — aproximadamente 3.6 MB
- Archivos JSON de layouts
- Archivos auxiliares de tipos de tensor

No todos los archivos auxiliares tenían hash remoto publicado en el árbol de Hugging Face; esa diferencia quedó anotada en el expediente local.

## 4. Integridad y hashes

Se ejecutó una comprobación local de SHA-256 para los archivos descargados y se compararon los hashes disponibles con los publicados por Hugging Face.

Resultado documentado en la sesión:
- Los archivos GGUF contrastados coinciden con los SHA-256 publicados en Hub.
- `model.safetensors` y `tokenizer.json` del repositorio original coinciden con los hashes de Hub.
- Algunos sidecars/layouts no tienen hash remoto para realizar comparación directa.

Registro local completo:
`~/modelos/cosmic-lightning/expediente-licencia/SHA256SUMS-COMPLETO.txt`

Este resultado acredita integridad respecto de los hashes publicados por el repositorio en el momento de la comprobación; no constituye una auditoría criptográfica independiente del autor ni una validación del comportamiento del modelo.

## 5. Entorno de descarga

Se creó un entorno virtual Python aislado:

`~/venvs/huggingface`

Comandos ejecutados:

```bash
mkdir -p ~/venvs
python3 -m venv ~/venvs/huggingface
source ~/venvs/huggingface/bin/activate
pip install --upgrade pip
pip install --upgrade huggingface_hub
hf --version
```

Versiones registradas:
- Python: 3.14
- pip: 26.2.2
- huggingface_hub / CLI `hf`: 2.4.0

### Comandos de descarga reproducibles

Modelo original:

```bash
mkdir -p ~/modelos/cosmic-lightning/original
hf download cosmicstack/cosmic-lightning \
  --local-dir ~/modelos/cosmic-lightning/original
```

Repositorio GGUF:

```bash
mkdir -p ~/modelos/cosmic-lightning/GGUF
hf download bartowski/cosmicstack_cosmic-lightning-GGUF \
  --local-dir ~/modelos/cosmic-lightning/GGUF
```

Para reproducir exactamente el original, usar la revisión fijada:

```bash
hf download cosmicstack/cosmic-lightning \
  --revision b5c2c76e95397a0b73cb618a2ec506a755f2832d \
  --local-dir ~/modelos/cosmic-lightning/original
```

## 6. Expediente de licencia y procedencia

Directorio local del expediente:

`~/modelos/cosmic-lightning/expediente-licencia`

En la sesión se generó/consultó el resumen de metadatos y repositorio:

`resumen-repositorio.txt`

La licencia declarada en la ficha de Hugging Face es **Apache License 2.0**. Antes de redistribuir pesos o publicar derivados, se recomienda conservar junto al artefacto:
- copia de la licencia aplicable y avisos de copyright;
- README y ficha de origen;
- identificador de revisión exacto;
- nombres de los repositorios de origen y conversión;
- hashes de los archivos redistribuidos;
- atribución de la conversión GGUF a su repositorio correspondiente;
- nota de que el GGUF es una conversión, no el artefacto original publicado por `cosmicstack`.

La licencia de la conversión GGUF y las obligaciones de redistribución deben revisarse por separado en el repositorio de bartowski, sin inferir que la ficha del modelo original resuelve automáticamente todos los términos de la conversión.

## 7. Consideraciones de ejecución en el equipo de referencia

Hardware de referencia: RTX 3050 Laptop con 4 GiB de VRAM y 14.8 GiB de RAM del sistema.

La cuantización IQ3_XXS (780.9 MB de archivo) es una candidata razonable para la primera prueba de carga por su reducido tamaño, pero el tamaño del archivo **no equivale** al consumo total de memoria en ejecución. También intervienen:
- buffers del runtime y del backend;
- contexto y caché KV;
- memoria temporal de evaluación;
- capas que se descarguen a GPU;
- arquitectura y kernels compatibles;
- reserva de VRAM del escritorio y otros procesos.

La primera ejecución debería usar contexto modesto y generación corta; posteriormente se puede aumentar contexto y offload de GPU en pasos, registrando consumo y errores.

## 8. Plan de validación pendiente

| Fase | Estado | Qué debe registrarse |
|---|---|---|
| Identificar arquitectura y configuración | Parcial: inspección de metadatos iniciada | `config.json`, arquitectura, parámetros y contexto declarado |
| Confirmar runtime y versión | Pendiente | llama.cpp / TensorFold / otros; commit o versión exacta |
| Carga inicial de GGUF | Pendiente | cuantización, comando, éxito/error, RAM y VRAM |
| Prueba de generación | Pendiente | prompt, tokens de entrada/salida, temperatura, seed |
| Medición de velocidad | Pendiente | prefill (tokens/s), generación (tokens/s), TTFT y tiempo total |
| Comparación entre cuantizaciones | Pendiente | mismo prompt, contexto, backend y parámetros |
| Evaluación cualitativa | Pendiente | tareas reproducibles, rúbrica y respuestas completas |
| Registro en LEONES | Este informe | actualizar cuando existan resultados reales |

## 9. Plantilla mínima para el futuro benchmark

Para cada ejecución, registrar:
- fecha y hora;
- equipo, sistema operativo, driver CUDA y memoria libre;
- runtime, versión/commit y parámetros de compilación;
- ruta y cuantización del GGUF, tamaño y SHA-256;
- contexto, batch, número de capas en GPU, threads;
- prompt exacto y número de tokens de entrada;
- máximo de tokens nuevos, temperatura, top-p, seed;
- tiempo de carga, TTFT, prefill en tokens/s;
- generación en tokens/s y duración total;
- RAM máxima y VRAM máxima;
- resultado: éxito, OOM, error de arquitectura o salida incorrecta;
- texto generado y evaluación.

## 10. Conclusión de esta fase

La descarga del modelo original y de la colección GGUF se completó. La revisión del repositorio original está fijada, los tamaños de las cuantizaciones están inventariados y los hashes disponibles fueron contrastados con Hugging Face.

**No hay aún resultados de inferencia medidos.** La siguiente etapa es identificar el runtime compatible, comprobar carga en el Ubuntu de referencia y ejecutar un benchmark reproducible. Las cifras de rendimiento y calidad se incorporarán a este informe únicamente después de obtenerlas experimentalmente.

## Referencias

- Modelo original: https://huggingface.co/cosmicstack/cosmic-lightning
- Revisión original: `b5c2c76e95397a0b73cb618a2ec506a755f2832d`
- Conversión GGUF: https://huggingface.co/bartowski/cosmicstack_cosmic-lightning-GGUF
- Expediente local de hashes: `~/modelos/cosmic-lightning/expediente-licencia/SHA256SUMS-COMPLETO.txt`
