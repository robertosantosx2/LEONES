# LEONES · Desinstalación y limpieza

LEONES dispone de una limpieza **selectiva**. Las operaciones son independientes: el usuario decide qué componentes retirar.

## Opciones

| Opción | Qué elimina |
|---|---|
| LEONES | Estado local generado por LEONES (`.leones/`, evidencias/runtime generadas). **No borra el checkout fuente** mientras se está ejecutando. |
| ODS | Contenedores, imágenes y volúmenes identificables como ODS en el runtime operativo. No desinstala Docker ni Podman. |
| Magnitude | `@magnitudedev/cli` instalado globalmente mediante npm. |
| LLM cargados | Todos los modelos locales gestionados por Ollama. |
| TODO | Ejecuta las cuatro operaciones anteriores. |

## Desde el wizard

Al terminar el flujo RC2, la limpieza debe presentarse como una operación opcional e independiente del benchmark. Elegir limpiar no implica repetir selección, instalación ni medición.

El wizard debe mostrar también que la misma operación puede ejecutarse fuera del wizard.

## Fuera del wizard

Desde el checkout de LEONES:

```bash
bash scripts/uninstall.sh
```

También puede invocarse de forma no interactiva:

```bash
bash scripts/uninstall.sh --leones
bash scripts/uninstall.sh --ods
bash scripts/uninstall.sh --magnitude
bash scripts/uninstall.sh --llms
bash scripts/uninstall.sh --all
```

Antes de ejecutar una limpieza destructiva se solicita confirmación. Para una simulación:

```bash
bash scripts/uninstall.sh --dry-run --all
```

Y para una ejecución previamente automatizada:

```bash
bash scripts/uninstall.sh --yes --all
```

## Principios de seguridad

1. **No hay `--all` implícito**: solo se elimina lo seleccionado.
2. LEONES no desinstala Docker/Podman como parte de la retirada de ODS.
3. La limpieza de ODS solo actúa sobre recursos cuyo nombre permita identificarlos como ODS; no elimina contenedores ajenos de forma indiscriminada.
4. La retirada de LLM afecta a los modelos locales que devuelve `ollama list`; no modifica otros runtimes.
5. La opción LEONES no borra el checkout que está ejecutando el propio comando.
6. `dry-run` permite inspeccionar las acciones antes de aplicarlas.

## Relación con la evidencia

La desinstalación es una operación de ciclo de vida y no una nueva medición. Si se eliminan modelos, ODS o Magnitude, las evidencias históricas ya publicadas no deben reinterpretarse como nuevas mediciones; simplemente se deja de disponer localmente de los artefactos/runtime que las generaron.
