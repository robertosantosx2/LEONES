# Runtime Check

## Objetivo

`runtime_check` comprueba una única cosa: si un ejecutable de `llama.cpp` está disponible en el sistema y qué versión declara.

## Qué no hace

- no instala llama.cpp;
- no descarga modelos;
- no modifica configuración;
- no ejecuta inferencia.

## Uso

```bash
python -m leones.runtime_check
```

También se puede indicar otro nombre de ejecutable:

```bash
python -m leones.runtime_check --executable llama-cli
```

## Por qué está separado

LEONES necesita conocer qué runtimes están disponibles antes de que Router pueda considerarlos. Esta comprobación debe ser pequeña y reutilizable.

```text
Hardware → Runtime Check → Router → Runtime
```

La siguiente pieza será la ejecución mínima de un modelo ya preparado; no se añadirá descarga ni selección de modelos a este script.
