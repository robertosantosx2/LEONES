# Model Sources

## Objetivo

Separar tres operaciones que no deben mezclarse:

```text
Model Source  → describe el origen
Downloader    → descarga un archivo explícito
Atlas         → registra metadatos y evidencia
Runtime       → ejecuta un modelo ya preparado
```

## Seguridad mínima

Una fuente contiene una URL HTTP/HTTPS y, cuando sea posible, un SHA-256 esperado.

El downloader:

1. valida la fuente;
2. descarga exactamente el destino indicado;
3. calcula SHA-256 mientras descarga;
4. elimina el archivo si el hash esperado no coincide.

No decide qué modelo descargar ni afirma que una licencia sea válida.

## Ejemplo de uso desde Python

```python
from leones.model_download import download
from leones.model_source import ModelSource

source = ModelSource(
    "https://example.org/model.gguf",
    "<sha256-64-hex-chars>",
)
download(source, "models/model.gguf")
```

La descarga automática desde catálogos, Hugging Face u otras fuentes se añadirá como una capa posterior. Primero mantenemos una operación elemental y verificable.
