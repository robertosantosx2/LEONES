# Evaluación agentiva — protocolo LEONES

## Estado

**🟢 SMOKE TEST CERRADO / EVALUACIÓN AGENTIVA REAL PENDIENTE**

LEONES dispone de un primer smoke test reproducible para comprobar capacidades agentic básicas. Este documento cierra y limpia el protocolo existente; **no certifica una evaluación agentiva completa**.

## Smoke test

Script:

```bash
python3 scripts/leones-evaluacion.py --endpoint http://127.0.0.1:8080
```

El endpoint debe ser local y compatible con la API OpenAI.

| ID | Prueba | Comprueba |
|---|---|---|
| B01 | memoria/localidad | Conservación de un dato exacto dentro de la interacción |
| B02 | archivos | Comprensión de una operación básica sobre un archivo |
| B03 | multietapa | Encadenamiento correcto de varios pasos |
| B04 | recuperación | Razonamiento sobre un fallo y recuperación |
| B05 | coding | Generación de una pequeña pieza de código correcta |

El runner registra PASS/FAIL, tiempo total, tokens cuando el servidor los proporciona, respuesta y errores, y guarda el resultado en JSON.

## Qué queda cerrado

El smoke test queda definido como **prueba rápida de coherencia inicial** de una pila local. Sirve como filtro previo y como señal comparable entre configuraciones.

```text
inferencia
    +
B01–B05
    ↓
señal inicial agentic
```

## Qué NO queda certificado

El smoke test no sustituye una evaluación agentiva completa con herramientas reales ni pruebas instrumentadas de un harness como Buddy/Hermes/LangGraph.

En particular:

- **B02** demuestra actualmente capacidad conversacional relacionada con archivos, no ejecución real de una herramienta de archivos.
- **B04** demuestra actualmente razonamiento conversacional sobre recuperación, no recuperación instrumentada ante un fallo real de herramienta.

Por tanto, un resultado `PASS` no debe interpretarse como prueba de uso real de herramientas.

## Criterio de interpretación

El resultado debe combinarse con la medición de inferencia y, cuando corresponda, con CABE/RULA:

```text
inferencia
    +
smoke test
    +
herramientas reales
    +
medición reproducible
    ↓
valor agentic verificable
```

No se declara que una pila sea adecuada únicamente por obtener PASS en B01–B05.

## Datos y evidencia

Cada ejecución debe conservar su resultado original y permitir identificar endpoint, configuración, fecha y condiciones relevantes. Los resultados derivados no sustituyen al registro primario.

Las pruebas futuras con herramientas reales deberán distinguir explícitamente entre:

- capacidad conversacional;
- llamada de herramienta;
- ejecución efectiva;
- resultado de la herramienta;
- recuperación ante error;
- tiempo y coste de la operación.

## No concurrencia

Todo workflow futuro que escriba resultados canónicos debe respetar la regla global de LEONES: un único grupo escritor `leones-main-writers` y `cancel-in-progress: false`.

## Próxima frontera

No se añade infraestructura ficticia para declarar el bloque terminado. La siguiente ampliación real será la **instrumentación de herramientas y recuperación**, cuando se decida ejecutar esa campaña.

Mientras tanto, el smoke test permanece cerrado como mecanismo de cribado y la evaluación agentiva completa permanece abierta.
