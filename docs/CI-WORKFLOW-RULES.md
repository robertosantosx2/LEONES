# Regla obligatoria de workflows de GitHub Actions

**Estado: 🟢 NORMA DEL PROYECTO**

## Regla de no concurrencia

Todo workflow de `.github/workflows/` que pueda modificar `main`, archivos del repositorio, artefactos publicados o cualquier estado compartido **DEBE** declarar el mismo grupo de concurrencia:

```yaml
concurrency:
  group: leones-main-writers
  cancel-in-progress: false
```

### Motivo

LEONES tiene varios procesos automáticos que generan datos y documentación. Dos ejecuciones simultáneas pueden intentar publicar los mismos archivos y producir conflictos, estados parciales o resultados difíciles de reproducir.

El grupo común convierte esos procesos en una cola: una ejecución termina y publica antes de que la siguiente pueda hacerlo.

`cancel-in-progress: false` es obligatorio porque una ejecución de generación de datos no debe ser cancelada a mitad de camino por otra más reciente.

## Workflows que no escriben

Un workflow que sea estrictamente de lectura, análisis o validación y que no modifique el repositorio puede usar otra política si se documenta expresamente. Si existe cualquier duda, se aplica `leones-main-writers`.

## Regla para workflows futuros

**No se acepta ningún workflow nuevo que escriba en el repositorio sin esta sección.**

Antes de crear o modificar un workflow:

1. comprobar si escribe en `main`;
2. añadir `concurrency` inmediatamente después de `permissions`/antes de `env` o `jobs`;
3. usar exactamente `leones-main-writers`;
4. mantener `cancel-in-progress: false`;
5. comprobar que el workflow no publica archivos generados que otro workflow publique también sin una coordinación explícita.

## Segunda barrera

La concurrencia no sustituye a la publicación segura. Los workflows que hacen commit/push deben conservar, cuando corresponda, el patrón de sincronización con `origin/main` antes del `push`.

## Auditoría

La revisión de workflows debe incluir esta regla como comprobación obligatoria. Si un workflow nuevo no cumple, debe considerarse **fallo de infraestructura CI**, no una advertencia menor.

## Principio

> **En LEONES, todo workflow futuro que escriba estado compartido queda bajo la regla de no concurrencia desde el primer commit.**
