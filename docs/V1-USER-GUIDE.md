# LEONES V1 — guía de uso

## Qué es esto

LEONES ayuda a responder qué combinación de **modelo + runtime + hardware + configuración** es razonable para una tarea de IA local.

La regla más importante es: **LEONES no inventa una medición**. Una estimación, un dato publicado por otra fuente y una medición realizada físicamente son cosas distintas.

## Primer uso

Desde la raíz del repositorio:

```bash
./scripts/run_leones_v1.sh
```

Si el sistema no permite ejecutar el archivo directamente:

```bash
bash scripts/run_leones_v1.sh
```

También puede ejecutarse directamente con Python:

```bash
python3 scripts/leones_v1.py preflight --pretty
```

## Qué hace el primer comando

El `preflight` comprueba únicamente lo que puede observarse sin ejecutar un benchmark:

- versión de Python;
- sistema operativo y arquitectura;
- procesador detectado;
- número de CPUs que el sistema expone;
- runtimes conocidos disponibles en el `PATH`;
- presencia de los contratos canónicos de LEONES.

El resultado es JSON y su estado es `observed`.

**No mide tokens por segundo. No crea un ranking. No decide qué modelo recomendar.**

## Qué significa que aparezca un runtime

Que un programa aparezca como disponible significa únicamente que el sistema puede localizarlo. No significa que esté correctamente configurado, que tenga un modelo instalado ni que haya demostrado rendimiento.

Por ejemplo, detectar `ollama` o `llama-cli` no equivale a tener una medición física válida.

## De dónde sale una recomendación

La V1 reutiliza los contratos ya cerrados. La cadena conceptual es:

```text
hardware observado
       ↓
selección / decisión canónica
       ↓
runtime autorizado
       ↓
ejecución real
       ↓
medición
       ↓
evidencia
       ↓
recomendación
       ↓
salida publicada
       ↓
traza E2E
```

Cada capa transporta la información de la anterior. Ninguna capa de salida debe recalcular el rendimiento ni crear un segundo sistema de scoring.

## Cuándo hace falta la máquina física

La parte que depende de una ejecución real no se puede demostrar solamente leyendo código o ejecutando tests de CI. Para esa fase hay que disponer del hardware y runtime correspondientes.

Cuando se haga esa ejecución, LEONES debe conservar la evidencia producida por el runtime y mantener su identidad, protocolo, artefacto, hash y resultado.

## Estados de evidencia

LEONES distingue, como mínimo:

- `estimated`: estimación;
- `reported`: dato declarado por una fuente;
- `observed`: dato observado en el entorno;
- `measured`: medición ejecutada;
- `verified`: dato que ha superado el control de calidad correspondiente;
- `unknown`: todavía no demostrado.

No deben intercambiarse estos estados para hacer que una recomendación parezca más segura de lo que realmente es.

## Para una persona con pocos conocimientos de programación

Si sólo quieres comprobar que LEONES puede ver tu máquina, ejecuta:

```bash
./scripts/run_leones_v1.sh
```

Si quieres entender el resultado, busca primero `status`, `runtimes_detected` y `contracts_present`.

Si todos los contratos aparecen como `true`, la instalación de los contratos de software está presente. Eso **no significa todavía que se haya ejecutado una prueba física**.

## Principio -strict-

Cuando una tarea se marque como `-strict-`, debe aplicarse siempre esta disciplina:

1. **Limpiar:** eliminar duplicaciones, restos, ambigüedades y lógica paralela innecesaria.
2. **Fijar:** convertir la decisión correcta en contrato, prueba o documentación verificable.
3. **Dar esplendor:** explicar claramente el funcionamiento, tanto en comentarios internos como en documentación Markdown externa.
4. Auditar antes de declarar cerrado un bloque.
5. No introducir una segunda arquitectura para solucionar un problema que ya tiene contrato.

La documentación interna debe poder entenderla alguien con pocos conocimientos de programación. La documentación externa debe explicar cómo utilizar el resultado sin exigir conocer la implementación.

## Limitación actual de esta puerta de entrada

Este lanzador es la **primera puerta de la V1**. El `preflight` observa la máquina; la ejecución física y la producción de una recomendación real siguen dependiendo de los contratos y runtimes existentes. No se debe presentar el preflight como si fuese un benchmark.
