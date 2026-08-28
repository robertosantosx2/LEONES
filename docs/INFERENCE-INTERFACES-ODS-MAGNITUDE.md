# LEONES — Interfaces de inferencia: ODS, Hermes y Magnitude

> **Decisión de arquitectura RC1**
>
> LEONES no construye un motor de inferencia ni un agente paralelo. Consume los mecanismos que ya proporcionan ODS/Hermes y Magnitude y se ocupa de seleccionar, ejecutar, medir, validar y conservar evidencia.

## 1. Decisión cerrada

La primera integración agentiva de LEONES debe partir de **ODS/Hermes mediante su interfaz OpenAI-compatible hacia `llama-server`**.

Magnitude se tratará de forma diferente: su arquitectura actual incorpora **su propio motor de inferencia basado en llama.cpp**, por lo que no debemos forzar `llama-server` como requisito de Magnitude.

Esto produce dos caminos de ejecución legítimos:

```text
                    LEONES
                       |
              selección / decisión
                       |
             +---------+---------+
             |                   |
            ODS              Magnitude
             |                   |
           Hermes          agente + ACN
             |                   |
   OpenAI-compatible       provider / engine
             |                   |
       llama-server       motor propio sobre llama.cpp
             |                   |
             +---------+---------+
                       |
                 tarea real
                       |
                 medición LEONES
                       |
                    evidencia
                       |
                     MANADA
```

## 2. ODS + Hermes

La documentación oficial de ODS describe Hermes como un servicio que habla con el proveedor de modelo mediante una **API compatible con OpenAI**. En la configuración local por defecto, ODS apunta Hermes a `llama-server` mediante `llama-server:8080/v1`.

Por tanto, para LEONES:

- Hermes es el **harness/agente**;
- `llama-server` es el **backend de inferencia local** por defecto;
- la frontera que debemos integrar y observar es la **API OpenAI-compatible**;
- `llama-cli` no es la interfaz agentiva de ODS;
- LEONES no debe duplicar Hermes ni implementar otro agente.

Referencia primaria: `nxpatterns/Osmantic-ODS`, `ods/docs/HERMES.md`.

## 3. `llama-cli` frente a `llama-server`

No son intercambiables dentro del protocolo de LEONES.

### `llama-cli`

Se utiliza para una ejecución directa y controlada del modelo. Es adecuado para el benchmark de bajo nivel de JALÓN 3 porque permite fijar prompt, contexto, generación y capturar el throughput observado.

### `llama-server`

Es el servicio HTTP OpenAI-compatible de llama.cpp. Es adecuado cuando un agente, como Hermes, necesita consumir el modelo como proveedor.

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

LEONES puede reutilizar ambos caminos sin convertir ninguno en un runtime propio.

## 4. Magnitude

La documentación oficial actual de Magnitude define el producto como un agente local con **su propio motor de inferencia**. El README del proyecto indica que dicho motor está escrito en Rust y construido sobre llama.cpp, y que Magnitude perfila el hardware, recomienda modelos y gestiona la carga/configuración local.

La arquitectura del repositorio separa, entre otros componentes, `clients`, `sdk`, `acn`, `ai`, `providers` y `agent`. Esto significa que la interfaz de inferencia debe entenderse como una capacidad interna del producto, no como una simple dependencia de un `llama-server` externo.

Magnitude también declara soporte para usar un endpoint OpenAI-compatible externo. Esa capacidad es útil como ruta de interoperabilidad, pero **no debe convertirse en la hipótesis de referencia del benchmark de Magnitude**: el benchmark debe medir primero el camino nativo que el producto ofrece al usuario.

Referencia primaria: `magnitudedev/magnitude`, `README.md` y documentación de arquitectura del repositorio.

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

No se debe ejecutar todavía hasta haber terminado la auditoría documental de Magnitude y preparado el contrato mínimo de tarea.

La primera prueba física deberá ser:

```text
hardware de consumo real
        |
        +--> ODS + Hermes + llama-server
        |
        +--> Magnitude nativo
        |
        +--> misma tarea versionada
        |
        +--> misma familia/modelo cuando sea posible
        |
        +--> evidencia LEONES
```

La comparación debe mantener constantes todas las variables que realmente puedan mantenerse constantes y registrar explícitamente las que sean diferentes por arquitectura.

## 7. Qué NO hacemos

- No creamos `LEONES-server`.
- No creamos un agente LEONES que sustituya a Hermes o Magnitude.
- No obligamos a Magnitude a utilizar `llama-server` si su camino nativo es distinto.
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

- ¿qué proceso inicia ODS para servir el modelo?
- ¿qué endpoint consume Hermes?
- ¿qué interfaz utiliza Magnitude en su camino nativo?
- ¿qué proveedor/engine utiliza Magnitude?
- ¿qué modelo concreto vamos a probar?
- ¿qué tarea agentiva vamos a ejecutar?
- ¿qué variables serán constantes?
- ¿qué variables serán específicas de cada producto?
- ¿qué evidencia debemos conservar?
- ¿cómo se convertirá la ejecución en un resultado publicable en MANADA?

Solo entonces se pasa a Ubuntu para `instalar -> ejecutar -> medir -> conservar evidencia`.

## 10. Fuentes primarias

- ODS / Hermes: `nxpatterns/Osmantic-ODS`, `ods/docs/HERMES.md`.
- Magnitude: `magnitudedev/magnitude`, `README.md`.
- Magnitude architecture guidance: `AGENTS.md` y estructura de `packages/`.
- llama.cpp: documentación oficial de `llama-server` y su API OpenAI-compatible.

Estas fuentes son normativas para esta decisión. Si cambian upstream, LEONES debe revisar este documento antes de cambiar su arquitectura.

---

## Estado

**CERRADO para el diseño de RC1.**

Pendiente únicamente la ejecución física y la verificación experimental de las interfaces en el hardware de consumo objetivo. Esa ejecución requiere Ubuntu.
