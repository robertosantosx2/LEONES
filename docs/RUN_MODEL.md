# Run Model

## Objetivo

`run_model` ejecuta una única inferencia contra un modelo local ya preparado mediante `llama-cli`.

## Uso

```bash
python -m leones.run_model models/model.gguf "Explica qué es una red neuronal" --max-tokens 128
```

También permite indicar otro ejecutable:

```bash
python -m leones.run_model models/model.gguf "Hola" --executable llama-cli
```

## Qué hace

1. comprueba que el archivo local existe;
2. comprueba que `llama-cli` está disponible;
3. ejecuta un prompt explícito;
4. devuelve la salida.

## Qué no hace

- no selecciona el modelo;
- no descarga nada;
- no cuantiza;
- no hace fine-tuning;
- no ejecuta benchmarks;
- no modifica Atlas.

## Papel en LEONES

Es la primera frontera de ejecución real y deliberadamente pequeña:

```text
Model Preparation → Runtime Check → Run Model
```

La selección automática llegará en una capa posterior, mediante Leones Router.
