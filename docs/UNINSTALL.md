# LEONES · Desinstalación y limpieza

LEONES dispone de una limpieza **selectiva**. Las operaciones son independientes: el usuario decide qué componentes retirar.

## Opciones

| Opción | Qué elimina |
|---|---|
| LEONES | Estado local generado por LEONES (`.leones/`). **No borra el checkout fuente ni las evidencias históricas por defecto.** |
| ODS | Contenedores, imágenes y volúmenes identificables como ODS en el runtime operativo. No desinstala Docker ni Podman. |
| Magnitude | `@magnitudedev/cli` instalado globalmente mediante npm. |
| LLM cargados | Todos los modelos locales gestionados por Ollama. |
| TODO | Ejecuta las cuatro operaciones anteriores. |

## Desde el flujo RC2

El flujo RC2 tiene un punto final de **limpieza opcional**, separado de selección, instalación, verificación y benchmark.

Para usar la entrada canónica del flujo completo:

```bash
bash scripts/run_rc2_wizard.sh
```

Cuando el wizard termina correctamente, se ofrece la limpieza selectiva. Se pueden escoger varios componentes en una sola operación (`1,2,4`) o `TODO`.

El propio flujo informa además de que la misma operación puede ejecutarse fuera del wizard.

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
3. La limpieza de ODS debe actuar únicamente sobre recursos identificables como pertenecientes al stack ODS; no debe eliminar contenedores ajenos de forma indiscriminada.
4. La retirada de LLM afecta a los modelos locales que devuelve `ollama list`; no modifica otros runtimes.
5. La opción LEONES no borra el checkout que está ejecutando el propio comando.
6. **Las evidencias históricas no se borran por defecto.** La limpieza de ciclo de vida no altera la validez ni el significado de una medición ya registrada.
7. `dry-run` permite inspeccionar las acciones antes de aplicarlas.

## Relación con la evidencia

La desinstalación es una operación de ciclo de vida y no una nueva medición. Si se eliminan modelos, ODS o Magnitude, las evidencias históricas ya publicadas siguen siendo evidencias de las ejecuciones que las generaron; no deben reinterpretarse como nuevas mediciones.
