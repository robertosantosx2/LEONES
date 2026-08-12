# Evaluación — Pruebas agentivas estándar

LEONES incorpora un primer **smoke test estándar** para simplificar la evaluación inicial de una pila agentic.

Script:

```bash
python3 scripts/lotb-agentic-test.py
```

El script prueba un endpoint local compatible con la API OpenAI, por defecto:

```text
http://127.0.0.1:8080/v1
```

También acepta:

```bash
python3 scripts/evaluacion-agentic-test.py \
  --base-url http://127.0.0.1:8080/v1 \
  --model local-model \
  --output results/evaluacion/latest.json
```

## Pruebas

| ID | Prueba | Qué comprueba |
|---|---|---|
| B01 | memoria/localidad | Conservación de un dato exacto dentro de la interacción |
| B02 | archivos | Comprensión de una operación básica sobre un archivo |
| B03 | multietapa | Encadenamiento correcto de varios pasos |
| B04 | recuperación | Capacidad de razonar sobre un fallo y su recuperación |
| B05 | coding | Generación de una pequeña pieza de código correcta |

## Qué mide

Cada prueba registra:

- PASS/FAIL;
- tiempo total de respuesta;
- tokens de prompt, completion y total cuando el servidor los proporciona;
- respuesta obtenida;
- errores.

El resultado se guarda en JSON para facilitar su incorporación posterior a las estadísticas de LEONES.

## Qué significa este smoke test

Estas pruebas están diseñadas para responder rápidamente a una primera pregunta:

> **¿Esta configuración local puede ejecutar de forma mínimamente coherente las capacidades agentic básicas de Evaluación?**

No sustituyen la evaluación completa con Buddy/Hermes/LangGraph ni las pruebas instrumentadas de herramientas reales.

Especialmente B02 y B04 son actualmente **pruebas de capacidad conversacional**, no una demostración de ejecución real de herramientas. La ejecución real sobre archivos, recuperación de errores y otras herramientas deberá añadirse a la siguiente versión del protocolo.

## Criterio inicial

El resultado debe interpretarse junto con la medición de inferencia:

```text
inferencia
    +
B01-B05
    +
uso real del harness
    ↓
valor agentic
```

No se debe declarar que una pila es adecuada únicamente porque el smoke test sea positivo: también debe cumplir las condiciones CABE y los criterios de Evaluación correspondientes.
