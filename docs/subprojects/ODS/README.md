# Subproyecto ODS — Osmantic Deployment System

## Objetivo

Integrar ODS en LEONES como **instalador/stack de referencia**, no como dependencia obligatoria del núcleo.

ODS proporciona una pila local de IA que integra inferencia, UI, agentes, workflows, RAG, voz, generación de imagen y operación del stack. En la revisión del 20-08-2026 se identificó `v2.6.0` como release estable.

Fuente: https://github.com/Osmantic/ODS

## Papel dentro de LEONES

```text
LEONES
 ├── Atlas              identidad/evidencia
 ├── Benchmark          medición
 ├── Recommender        selección
 └── ODS adapter        instalación + despliegue
                         ↓
                 servicios locales
```

ODS debe consumir recomendaciones de LEONES y exponer al sistema de medición información suficiente para reproducir:

- hardware;
- modelo seleccionado;
- runtime/backend;
- versión ODS;
- configuración relevante;
- servicios activos.

## Reglas

1. ODS es una integración opcional.
2. LEONES no depende de APIs internas no versionadas de ODS.
3. La instalación debe fijar versión/tag o commit auditado cuando se use en producción o benchmarking.
4. Nunca se convierte una afirmación de ODS en medición LEONES sin ejecución y evidencia primaria.
5. Las credenciales y secretos de ODS nunca entran en resultados públicos.

## Instalación de referencia

ODS documenta instalación manual mediante clon del repositorio y `./install.sh`; también dispone de instalador para Linux/macOS y Windows.

Para LEONES se recomienda inicialmente la ruta de **clon + ref fijada**, porque es más reproducible para benchmarks que seguir `main`.

## Adaptador LEONES

Fases previstas:

1. `detect` — leer hardware sin exponer PII.
2. `select` — consultar recomendación LEONES.
3. `pin` — fijar versión ODS/modelo.
4. `install` — instalar en entorno dedicado.
5. `verify` — comprobar servicios.
6. `measure` — ejecutar benchmarks LEONES.
7. `report` — producir resultado canónico.
8. `uninstall/recover` — limpiar o restaurar.

## Validación

ODS mantiene documentación específica de soporte, instalación, arquitectura y validación de releases. Su arquitectura se basa en manifiestos de servicios, Docker Compose y capas específicas de hardware.

LEONES reutilizará esa evidencia como **evidencia externa** y añadirá medición propia cuando ejecute el stack.

## Estado

🟡 Diseño de integración. La implementación del adaptador y la primera instalación reproducible son la siguiente fase.
