# LEONES — Conector OpenAI-compatible común: ODS y Magnitude

> **RC1 — decisión arquitectónica congelada**
>
> ODS/Hermes y Magnitude pueden consumir un backend OpenAI-compatible. LEONES aprovechará esa coincidencia para mantener **un único conector mínimo**, en lugar de construir dos integraciones de inferencia paralelas.

## 1. Decisión

LEONES no necesita conocer dos protocolos de inferencia distintos para la primera integración agentiva.

La frontera común será:

```text
                         LEONES
                           │
                  selección / plan
                           │
                tarea agentiva RC1
                           │
             ┌─────────────┴─────────────┐
             │                           │
            ODS                       Magnitude
             │                           │
           Hermes                  agent / provider
             │                           │
             └─────────────┬─────────────┘
                           │
                 OpenAI-compatible
                           │
                    /v1/chat/completions
                           │
                 backend de inferencia
                           │
                    modelo local
                           │
                    medición LEONES
                           │
                       evidencia
```

La misma pieza de LEONES debe encargarse de:

1. construir la configuración del endpoint;
2. comprobar disponibilidad;
3. consultar los modelos expuestos;
4. ejecutar la llamada mínima de inferencia;
5. conservar metadatos de la ejecución;
6. dejar la medición y la evidencia en manos de los contratos de LEONES.

El conector **no** debe convertirse en un agente, un runtime ni un nuevo servidor.

## 2. Por qué esto simplifica LEONES

ODS ya documenta una API OpenAI-compatible y Hermes consume el proveedor mediante esa interfaz. En ODS, la ruta local por defecto conecta Hermes con `llama-server` y el endpoint `/v1`. citeturn0search0turn0search1

Magnitude también documenta un proveedor `openai-generic` con `baseUrl`, `model`, `apiKey`, `temperature` y headers opcionales. Esto permite apuntar Magnitude a un servidor OpenAI-compatible externo. citeturn1search1turn1search2

Por tanto, LEONES puede tratar ambos productos como **clientes de una misma frontera de inferencia** cuando la prueba experimental así lo permita.

Esto reduce:

- código;
- adaptadores duplicados;
- superficie de pruebas;
- divergencia de configuración;
- mantenimiento;
- riesgo de inventar una API propia.

## 3. No significa que ODS y Magnitude sean iguales

El conector común sólo unifica la **interfaz de inferencia**.

No unifica:

- el agente;
- la planificación;
- las herramientas;
- la memoria;
- el navegador;
- el perfilado de hardware;
- la selección de modelos;
- el runtime nativo;
- la configuración interna;
- la trayectoria agentiva;
- ni la forma en que cada producto mide o reporta internamente.

La comparación de LEONES debe conservar esas diferencias.

```text
                interfaz común
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
      ODS/Hermes              Magnitude
        │                         │
   comportamiento             comportamiento
   propio                     propio
        │                         │
        └────────────┬────────────┘
                     ↓
              medición LEONES
```

## 4. Backend de referencia para RC1

Para la primera prueba física de ODS/Hermes, el backend de referencia sigue siendo `llama-server`, porque es la ruta local documentada por ODS/Hermes. citeturn0search0turn0search9

Para Magnitude hay dos caminos válidos:

### A. Camino nativo

Magnitude utiliza su propia capacidad local de inferencia. Este camino debe medirse como **Magnitude nativo** cuando el objetivo sea saber qué experiencia ofrece Magnitude en hardware de consumo.

### B. Camino OpenAI-compatible

Magnitude puede configurarse con `provider: 'openai-generic'` y un `baseUrl` externo. citeturn1search1

Este camino permite conectar Magnitude al mismo endpoint que ODS/Hermes.

### Regla RC1

El conector común se implementa una sola vez, pero los benchmarks deben identificar explícitamente cuál de estos caminos se está midiendo.

No se puede publicar:

> "Magnitude = X tok/s"

sin indicar si el modelo fue servido por el motor nativo de Magnitude o por un endpoint externo.

## 5. Contrato mínimo del conector

El conector debe ser deliberadamente pequeño.

Conceptualmente:

```text
OpenAICompatibleEndpoint

base_url
api_key
model

health()
list_models()
chat(messages, **generation_options)
```

El contrato de LEONES debe devolver datos normalizados suficientes para correlacionar la llamada con la evidencia:

```text
provider_id
base_url
model
request_id
started_at
finished_at
latency
usage (si está disponible)
response_status
error (si existe)
```

No debe imponer campos que el servidor no pueda observar.

Los valores desconocidos permanecen `unknown`.

## 6. Health check

La comprobación mínima debe seguir la convención OpenAI-compatible:

```text
GET /v1/models
```

La prueba física debe conservar:

- URL efectiva sin secretos;
- HTTP status;
- modelos anunciados;
- modelo seleccionado;
- timestamp;
- versión del stack cuando sea observable.

En ODS, la propia documentación recomienda consultar `/v1/models` para conocer el nombre exacto del modelo servido. citeturn0search3

## 7. Llamada mínima

La prueba funcional inicial debe ser una llamada de chat sencilla:

```text
POST /v1/chat/completions
```

con:

- un modelo explícito;
- un único mensaje de usuario;
- límites de generación explícitos;
- sin herramientas;
- sin streaming en el health smoke test.

La prueba agentiva se ejecutará después y tendrá su propio contrato.

## 8. Separación entre inferencia y agente

El conector no debe registrar la trayectoria completa del agente como si fuese una llamada de inferencia.

Debe existir una correlación:

```text
agent_execution_id
       │
       ├── inference_request_1
       ├── inference_request_2
       ├── tool_call_1
       ├── inference_request_3
       └── outcome
```

Así LEONES puede responder por separado:

- cuánto tardó el modelo;
- cuántas llamadas realizó el agente;
- qué herramientas utilizó;
- cuánto tardó la tarea;
- si terminó correctamente.

## 9. Medición

El conector **no calcula una métrica de rendimiento propia** que compita con JALÓN 3.

Puede conservar `usage` o tiempos que el endpoint entregue, pero la autoridad es:

```text
JALÓN 3
   ↓
medición LEONES
   ↓
evidence
   ↓
validation
```

Esto mantiene la separación entre:

- dato observado del proveedor;
- dato reportado por el producto;
- medición física realizada por LEONES.

## 10. Configuración segura

Nunca se guarda en evidencia:

- API keys;
- tokens de sesión;
- cookies;
- secretos del entorno.

La evidencia puede conservar:

```text
base_url = http://127.0.0.1:8080/v1
api_key_present = true
api_key_value = REDACTED
```

Para servidores locales sin autenticación, el conector debe aceptar una clave ficticia si el SDK/protocolo la exige, pero nunca confundirla con una credencial real.

## 11. Reutilización del mismo endpoint

El caso que RC1 quiere hacer posible es:

```text
llama-server
     │
     └── http://127.0.0.1:8080/v1
             │
        ┌────┴────┐
        ↓         ↓
   ODS/Hermes  Magnitude
```

Esto permite realizar una prueba controlada donde:

- hardware = constante;
- backend = constante;
- modelo = constante;
- endpoint = constante;
- tarea = constante;
- agente = variable.

El resultado puede entonces atribuirse con mucha más claridad a la capa agentiva.

Posteriormente se puede repetir:

```text
Magnitude nativo
```

para medir la experiencia completa que Magnitude ofrece cuando controla también la inferencia.

## 12. Orden de benchmark RC1

El orden queda fijado:

### B0 — endpoint

```text
GET /v1/models
POST /v1/chat/completions
```

Objetivo: demostrar que la frontera funciona.

### B1 — inferencia controlada

Modelo + prompt + contexto + generación controlados.

Objetivo: medir el backend según JALÓN 3.

### B2 — ODS/Hermes

Misma máquina + tarea agentiva versionada.

Objetivo: medir tarea completa.

### B3 — Magnitude vía OpenAI-compatible

Misma máquina + mismo endpoint + misma tarea cuando la arquitectura lo permita.

Objetivo: comparar la capa agente manteniendo constante el backend.

### B4 — Magnitude nativo

Magnitude controla su propia inferencia.

Objetivo: medir la experiencia completa de Magnitude en hardware de consumo.

### B5 — publicación

Promover únicamente resultados que superen los quality gates de LEONES y conservar la procedencia completa para MANADA.

## 13. Consecuencia para los tiers de hardware

Esta decisión refuerza el objetivo principal de LEONES: **hardware de consumo**.

LLMFit aporta el fit previo.

ODS puede cubrir la ruta SOHO.

Magnitude puede cubrir la ruta de asistente personal.

LEONES mide ambas rutas sobre hardware real.

Por tanto, los tiers no deben modelar únicamente "cuántos GB de VRAM tiene la máquina". Deben terminar expresando:

```text
hardware
   ↓
modelo que cabe
   ↓
runtime/backend
   ↓
agente
   ↓
tarea que completa
   ↓
tiempo / rendimiento
```

El tier es útil si permite responder qué puede hacer realmente una máquina de consumo.

## 14. AirLLM y FreeToken

La decisión anterior se mantiene:

> **AirLLM y FreeToken no se convierten ahora en dos nuevos motores internos de LEONES.**

Cuando llegue el momento, LEONES los aportará a ODS/Magnitude:

1. upstream cuando tenga sentido;
2. conector mínimo si upstream no lo incorpora todavía;
3. evidencia de la mejora;
4. sin duplicar infraestructura innecesariamente.

El conector OpenAI-compatible no impide esa evolución. Al contrario, proporciona una frontera estable para integrar nuevas capacidades sin rehacer la capa agentiva de LEONES.

## 15. Regla de minimalismo

Este documento fija explícitamente:

> **Un protocolo común antes que dos adaptadores.**

Y las reglas de trabajo de LEONES siguen siendo:

- poco código;
- cada pieza una responsabilidad;
- comentarios que expliquen decisiones;
- README/documentación que explique cómo utilizarla;
- reutilizar upstream antes de copiarlo;
- medir antes de afirmar;
- conservar evidencia;
- no mantener forks sin justificación.

## 16. Gate antes de Ubuntu

Antes de instalar nada físicamente, GitHub debe dejar preparados:

- contrato del conector;
- implementación mínima;
- tests unitarios;
- fixtures OpenAI-compatible;
- runner de health check;
- runner de chat mínimo;
- redacción de secretos;
- correlación con `execution_id`;
- documentación de ODS;
- documentación de Magnitude;
- definición B0–B5.

Sólo después:

```text
Ubuntu
  ↓
instalar/arrancar backend
  ↓
B0
  ↓
B1
  ↓
B2/B3/B4
  ↓
evidence
```

## Estado

**DECISIÓN CONGELADA PARA RC1.**

ODS y Magnitude comparten una frontera OpenAI-compatible utilizable por LEONES. El primer conector agentivo será común. Las diferencias internas de cada producto se conservarán como variables experimentales y no se ocultarán bajo el conector.
