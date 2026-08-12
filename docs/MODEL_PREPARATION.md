# Model Preparation

## Objetivo

`model_prepare` comprueba que un modelo local está listo para pasar al Runtime.

## Qué comprueba

1. que el archivo existe;
2. que tiene un formato conocido por LEONES;
3. que el SHA-256 coincide cuando se proporciona uno.

Formatos iniciales reconocidos: `GGUF`, `safetensors`, `bin` y `onnx`.

## Qué no hace

No descarga, convierte, cuantiza ni ejecuta modelos.

## Uso

```bash
python -m leones.model_prepare models/model.gguf
```

Con hash:

```bash
python -m leones.model_prepare models/model.gguf --sha256 <64-hex>
```

## Principio

La preparación es una barrera sencilla entre un archivo externo y el Runtime:

```text
fuente → descarga → preparación → Runtime
```

Si una fase posterior necesita conversión, extracción de metadatos o cuantización, tendrá su propia herramienta.
