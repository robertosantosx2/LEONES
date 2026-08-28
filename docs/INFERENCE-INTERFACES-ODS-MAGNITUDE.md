# LEONES — Interfaces de inferencia: ODS, Hermes y Magnitude

> **Decisión de arquitectura RC1**
>
> LEONES no construye un motor de inferencia ni un agente paralelo. Consume los mecanismos que ya proporcionan ODS/Hermes y Magnitude y se ocupa de seleccionar, ejecutar, medir, validar y conservar evidencia.

## 1. Decisión cerrada

ODS/Hermes y Magnitude tienen una frontera de interoperabilidad común: **OpenAI-compatible**.

Por tanto, LEONES implementará **un único conector OpenAI-compatible** para la primera integración agentiva. No habrá un conector específico para ODS y otro distinto para Magnitude salvo que una diferencia real, demostrada experimentalmente, lo haga imprescindible.

```text
                         LEONES
                           |
                  selección / decisión
                           |
                  tarea agentiva RC1
                           |
             +-------------+-------------+
             |                           |
            ODS                       Magnitude
             |                           |
           Hermes                  agent / provider
             |                           |
             +-------------+-------------+
                           |
                  OpenAI-compatible
                           |
                  /v1/models
                  /v1/chat/completions
                           |
                  backend de inferencia
                           |
                     modelo local
                           |
                    medición LEONES
                           |
                       evidencia
                           |
                         MANADA
```

El conector común sólo unifica la **frontera de inferencia**. No unifica los agentes, las herramientas, la memoria, el navegador, el perfilado de hardware ni los motores internos.

La especificación detallada está en [`OPENAI-COMPATIBLE-CONNECTOR-ODS-MAGNITUDE.md`](OPENAI-COMPATIBLE-CONNECTOR-ODS-MAGNITUDE.md).

## 2. ODS + Hermes

La documentación oficial de ODS describe Hermes como un servicio que habla con el proveedor de modelo mediante una **API compatible con OpenAI**. En la configuración local por defecto, ODS apunta Hermes a `llama-server` mediante `llama-server:8080/v1`. citeturn0search0turn0search1

Por tanto, para LEONES:

- Hermes es el **harness/agente**;
- `llama-server` es el **backend de inferencia local** por defecto de ODS;
- la frontera que debemos integrar y observar es la **API OpenAI-compatible**;
- `llama-cli` no es la interfaz agentiva de Hermes;
- LEONES no debe duplicar Hermes ni implementar otro agente.

ODS también documenta que su API puede consumirse directamente con el SDK de OpenAI y que `/v1/models` permite conocer el modelo servido. citeturn0search3

## 3. `llama-cli` frente a `llama-server`

No son intercambiables dentro del protocolo de LEONES.

### `llama-cli`

Se utiliza para una ejecución directa y controlada del modelo. Es adecuado para el benchmark de bajo nivel de JALÓN 3 porque permite fijar prompt, contexto, generación y capturar el throughput observado.

### `llama-server`

Es el servicio HTTP OpenAI-compatible de llama.cpp. Es adecuado cuando un agente necesita consumir el modelo como proveedor.

La separación queda fijada así:

```text
JALÓN 3 / benchmark bajo nivel
    -> llama-cli
    -> medición directa

RC1 / tarea agentiva ODS
    -> Hermes
    -> OpenAI-compatible API
    -> llama-server
    -> modelo
    -> tarea
    -> medición de tarea por LEONES
```

LEONES reutiliza ambos caminos sin convertir ninguno en un runtime propio.

## 4. Magnitude

Magnitude se orienta a un agente con modelos locales integrados, perfilado de hardware y selección/configuración de modelos. Su documentación pública indica además que puede conectarse a un **endpoint OpenAI-compatible externo**. citeturn1search0

La documentación de proveedores de Magnitude define explícitamente:

```text
provider: 'openai-generic'
options:
  model
  baseUrl
  apiKey?
  temperature?
  headers?
```

Esto permite utilizar el mismo tipo de endpoint que consume ODS/Hermes. citeturn1search1turn1search2

Por tanto Magnitude tiene dos rutas legítimas para LEONES:

### A. Magnitude nativo

Magnitude controla su propia inferencia local. Esta es la ruta que debe medirse cuando la pregunta sea:

> **¿Qué experiencia completa ofrece Magnitude en este hardware de consumo?**

### B. Magnitude mediante OpenAI-compatible

Magnitude utiliza `openai-generic` para consumir un endpoint externo. Esta ruta es especialmente valiosa para LEONES porque permite reutilizar el mismo conector y, si se apunta al mismo backend que ODS/Hermes, mantener constante la inferencia mientras se compara la capa agente.

La ruta B **no sustituye** a la ruta A: son experimentos diferentes y deben etiquetarse como tales.

## 5. Qué debe medir LEONES

LEONES no debe medir únicamente tokens por segundo. Debe distinguir dos niveles.

### Nivel A — inferencia

Reutiliza el protocolo de JALÓN 3:

- modelo;
- revisión/identidad;
- cuantización;
- runtime/engine;
- versión;
- hardware;
- contexto;
- prompt;
- warm-up;
- número de ejecuciones;
- throughput;
- tiempos;
- ejecución identificable;
- evidencia reproducible.

### Nivel B — tarea agentiva

Mide el resultado de una tarea completa:

- tarea conocida y versionada;
- estado inicial conocido;
- herramientas permitidas;
- número de pasos/tool calls;
- errores;
- recuperaciones;
- tiempo de pared;
- tokens si el runtime los expone;
- tarea completada o no;
- criterios de corrección;
- evidencia de la trayectoria;
- hardware real.

La métrica principal de LEONES pasa a ser conceptualmente:

> **tareas completadas bajo unas condiciones de hardware, modelo y runtime reproducibles.**

`tok/s` sigue siendo una métrica auxiliar, no el objetivo final.

## 6. Primera prueba física

La primera prueba física debe aprovechar el conector común y separar claramente los experimentos:

```text
hardware de consumo real
        |
        +--> ODS + Hermes + llama-server
        |          |
        |       conector común
        |
        +--> Magnitude + OpenAI-compatible
        |          |
        |       mismo conector
        |
        +--> Magnitude nativo
                   |
                camino propio
```

Para la comparación ODS/Hermes ↔ Magnitude mediante endpoint común, se mantendrán constantes, cuando sea posible:

- hardware;
- backend;
- modelo;
- cuantización;
- contexto;
- tarea;
- prompt/protocolo;
- límites de generación.

Las diferencias que no puedan mantenerse constantes deben quedar registradas, no ocultas.

## 7. Qué NO hacemos

- No creamos `LEONES-server`.
- No creamos un agente LEONES que sustituya a Hermes o Magnitude.
- No creamos dos conectores para la misma interfaz.
- No obligamos a Magnitude a utilizar `llama-server` en su camino nativo.
- No confundimos una prueba de `llama-cli` con una prueba de Hermes.
- No publicamos un resultado agentivo como si fuera una medición de tokens/s.
- No inventamos equivalencias entre métricas producidas por diferentes motores.
- No modificamos ODS o Magnitude antes de conocer exactamente sus interfaces y límites.

## 8. Regla de upstream

Cuando LEONES encuentre una mejora que pertenezca realmente al runtime o al agente upstream, se intentará:

1. aportar la mejora al upstream correspondiente;
2. mantener un conector/adaptador mínimo en LEONES si la integración upstream no es inmediata;
3. documentar la diferencia y su procedencia;
4. evitar forks permanentes salvo necesidad justificada.

Esto aplica especialmente a las futuras aportaciones de **AirLLM** y **FreeToken** a ODS/Magnitude.

## 9. Gate antes de Ubuntu

Ubuntu se solicita solamente cuando el repositorio ya pueda responder documentalmente a estas preguntas:

- ¿qué endpoint OpenAI-compatible expone ODS?
- ¿qué endpoint consume Hermes?
- ¿cómo se configura Magnitude para `openai-generic`?
- ¿cuál es el camino nativo de Magnitude?
- ¿qué backend y modelo concreto vamos a probar?
- ¿qué tarea agentiva vamos a ejecutar?
- ¿qué variables serán constantes?
- ¿qué variables serán específicas de cada producto?
- ¿qué evidencia debemos conservar?
- ¿cómo se convertirá la ejecución en un resultado publicable en MANADA?

El diseño ya responde estas preguntas. El siguiente paso que requiere Ubuntu es la verificación física:

```text
instalar -> arrancar -> health -> inferencia -> tarea -> medir -> conservar evidencia
```

## 10. Fuentes primarias revisadas

- ODS / Hermes: `Osmantic/ODS`, `ods/docs/HERMES.md`. citeturn0search0
- ODS integration guide / OpenAI compatibility. citeturn0search3
- ODS architecture / agent execution flow. citeturn0search9
- Magnitude: sitio oficial y capacidad de conectar un endpoint OpenAI-compatible. citeturn1search0
- Magnitude LLM Providers: `openai-generic`, `baseUrl`, `model`, `apiKey` y opciones. citeturn1search1
- Magnitude compatible LLMs: ejemplo de configuración `openai-generic`. citeturn1search2
- llama.cpp: servidor OpenAI-compatible, como backend físico de referencia cuando corresponda.

Estas fuentes son normativas para la decisión de diseño. Si cambian upstream, LEONES debe revisar este documento antes de cambiar su arquitectura.

---

## Estado

**CERRADO para el diseño de RC1.**

La interfaz común ya no es una hipótesis: ODS/Hermes y Magnitude documentan compatibilidad con la frontera OpenAI-compatible. LEONES utilizará un único conector mínimo para esa frontera y conservará como experimento separado el camino nativo de Magnitude.

**Ubuntu aún no es necesario para diseñar el conector. Sí será necesario para verificar físicamente los endpoints, ejecutar las tareas y producir la primera evidencia real de RC1.**
