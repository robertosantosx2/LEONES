# JALÓN 12 — Superficie de usuario V1

**Estado:** 🟠 CONTRATO PREPARADO · IMPLEMENTACIÓN PENDIENTE
**Rama:** `rc1-minimal-script-cleanup`

## Propósito

JALÓN 12 no crea una arquitectura nueva. Convierte la cadena canónica de JALONES 1–11 en una superficie que una persona pueda utilizar sin conocer los contratos internos.

La cadena interna permanece:

`selection → runtime → execution → measurement → evidence → decision → recommendation → publication → output → trace`

JALÓN 12 sólo define cómo entra una persona y cómo recibe el resultado.

## Principio fundamental

El usuario interactúa con **una única entrada V1**.

La entrada de usuario no vuelve a seleccionar, medir, puntuar ni recomendar por su cuenta. Solicita una operación y entrega el control a los contratos canónicos existentes.

## Entrada mínima

La superficie V1 debe poder recibir, de forma documentada:

- modelo o familia de modelo;
- tarea o intención del usuario;
- restricciones relevantes de hardware/uso cuando existan;
- permiso para ejecutar una medición física cuando sea necesaria.

## Salida mínima

Debe presentar:

- recomendación;
- motivo legible;
- fuentes/señales externas utilizadas;
- evidencia medida disponible;
- estado de verificación;
- identificador de operación E2E;
- indicación explícita de cualquier parte no ejecutada.

## Reglas de procedencia

1. Una señal externa sigue siendo externa.
2. Una estimación sigue siendo estimación.
3. Una observación sigue siendo observación.
4. Una medición local sólo se declara cuando existe ejecución física conservada.
5. Una recomendación procede del contrato de decisión/recomendación, no de una puntuación paralela de la interfaz.
6. La salida no modifica la evidencia original.

## Regla de simplicidad

Una persona con pocos conocimientos de programación debe poder seguir la guía de uso y completar una operación soportada sin aprender qué es un adapter, un gate o un JALÓN.

Los comentarios internos, en cambio, deben explicar esas piezas con lenguaje sencillo para facilitar el mantenimiento.

## Criterio de cierre

JALÓN 12 se cerrará cuando exista:

- una entrada V1 única;
- un flujo de usuario completo sobre la cadena existente;
- salida legible y machine-readable;
- documentación de instalación y uso;
- tests del flujo feliz y de errores;
- auditoría `-strict-` verde;
- y, cuando el caso lo requiera, una ejecución física real conservada como evidencia.

**No es criterio de cierre:** medir todos los modelos o todos los runtimes disponibles.

**Frase de recuperación:**

> JALÓN 12 = hacer utilizable por una persona la arquitectura ya construida, sin crear una segunda arquitectura.
