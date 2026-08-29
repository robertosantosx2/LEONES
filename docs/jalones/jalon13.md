# JALÓN 13 — V1 READINESS GATE

## Objetivo

Cerrar la preparación de la primera V1 utilizable sin crear una segunda arquitectura.

Este jalón comprueba que la puerta de usuario, los contratos canónicos y las pruebas están conectados de forma coherente antes de exigir una ejecución física nueva.

## Regla fundamental

JALÓN 13 no calcula velocidad, no puntúa modelos y no decide una recomendación alternativa.

La medición real sigue perteneciendo al runtime y a `runtime-benchmark-evidence.v1.1`. La decisión sigue perteneciendo al contrato de decisión. La recomendación sigue perteneciendo al contrato canónico. Esta capa sólo comprueba que las piezas necesarias para la V1 están presentes y que la entrada de usuario delega correctamente.

## Qué debe quedar PASS

1. Existe una única entrada de usuario.
2. El preflight valida el entorno sin fingir una medición.
3. Los contratos canónicos de decisión, E2E, recomendación y output están presentes.
4. Las pruebas completas pasan.
5. Los runners de auditoría son ejecutables.
6. `git diff --check` queda limpio.
7. No aparece un segundo sistema de benchmark, scoring o ranking.
8. La documentación explica qué hace y qué no hace la V1.

## Qué queda para una V1 física completa

La primera ejecución real de extremo a extremo sobre el hardware del usuario debe producir evidencia física nueva y reproducible. Eso no se sustituye por una simulación ni por datos declarativos.

Cuando se haga esa ejecución, se conserva la evidencia y se verifica mediante los contratos ya cerrados.

## Criterio de cierre

`JALON13_V1_READINESS_CLOSE=PASS` significa que el producto está preparado para la prueba física final de V1 y que no hace falta rediseñar la arquitectura para ejecutarla.
