# LEONES — RC1: contrato mínimo de tarea agentiva

> **Estado: CERRADO para diseño; pendiente ejecución física.**
>
> Este documento define la primera prueba agentiva comparable de LEONES sin construir otro agente, otro servidor ni otro motor de inferencia.

---

## 1. Objetivo

RC1 no intenta demostrar qué producto es "mejor" en abstracto.

Quiere responder una pregunta reproducible:

> **¿Puede un sistema local de IA completar correctamente una tarea útil, con qué coste temporal y bajo qué hardware/modelo/runtime?**

Los sistemas bajo prueba son:

- **ODS + Hermes** como camino SOHO;
- **Magnitude** como camino de asistente personal;
- el modelo y hardware reales disponibles en el host.

LEONES aporta el protocolo de tarea, la medición, la evidencia y la publicación.

---

## 2. Principio de comparación

No se comparan internamente los productos por sus implementaciones. Se compara el resultado observable de una tarea.

```text
                 MISMA TAREA
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
      ODS + Hermes          Magnitude
          │                     │
   su agente + backend     su agente + engine
          │                     │
          └──────────┬──────────┘
                     ↓
              resultado observable
                     │
                 LEONES
                     │
          medición + evidencia
                     │
                   MANADA
```

Si una capacidad no existe en uno de los productos, no se inventa una equivalencia. Se marca como `not_comparable` y se conserva la razón.

---

## 3. Tarea RC1-A01

La primera tarea debe ser deliberadamente pequeña, determinista y auditable.

### Objetivo funcional

Partiendo de un repositorio/directorio de prueba preparado por LEONES, el agente debe:

1. inspeccionar un conjunto pequeño de archivos;
2. localizar información concreta mediante sus herramientas disponibles;
3. producir un informe estructurado con los datos solicitados;
4. escribir el informe en una ruta conocida;
5. terminar sin modificar archivos fuera del workspace autorizado.

La tarea no depende de conocimiento externo ni de una web cambiante.

### Entrada

Un fixture versionado por LEONES que contenga pocos archivos de texto y datos estructurados. El contenido y SHA-256 del fixture forman parte de la evidencia.

### Salida

Un único artefacto de resultado, por ejemplo `report.json`, con un esquema versionado y un conjunto pequeño de campos cuya corrección pueda comprobarse automáticamente.

### Criterio de éxito

La tarea es `success` únicamente si:

- el artefacto existe;
- es válido según el esquema;
- contiene todos los campos obligatorios;
- los valores esperados coinciden;
- no se detectan modificaciones fuera del workspace permitido;
- y el agente finaliza correctamente.

Un resultado parcial no se convierte en éxito por puntuación subjetiva.

---

## 4. Variables controladas

Siempre que la arquitectura lo permita se fijan:

- fixture y versión;
- prompt de tarea;
- modelo y revisión;
- cuantización;
- contexto objetivo;
- temperatura y parámetros equivalentes;
- herramientas permitidas;
- workspace;
- criterio de corrección;
- número de repeticiones;
- warm-up;
- condiciones de red.

Las diferencias inevitables se registran explícitamente.

---

## 5. Métricas

La métrica primaria es **tarea completada correctamente**.

Métricas secundarias:

- `success` / `failure`;
- tiempo de pared;
- número de tool calls;
- errores de herramientas;
- recuperaciones;
- tokens de entrada/salida cuando estén disponibles;
- throughput observado cuando el runtime lo exponga;
- uso de memoria/GPU cuando pueda observarse sin introducir instrumentación que cambie sustancialmente la ejecución;
- coste estimado únicamente como dato derivado, nunca como medición primaria.

### Regla

`tok/s` **no sustituye** a `task_success`.

Una ejecución rápida que no completa la tarea correctamente no supera una ejecución más lenta que sí la completa.

---

## 6. Contrato de ejecución

Cada ejecución debe producir un identificador único `execution_id` y conservar, como mínimo:

```text
execution_id
started_at
finished_at
product
agent
model
model_revision
quantization
runtime
runtime_version
hardware
context
prompt_hash
task_id
task_version
warmup_count
measurement_index
wall_time_seconds
tool_calls
tool_errors
recovery_count
task_status
result_artifact
result_sha256
```

Los campos no observables deben ser `null`/`unknown`, nunca inventados.

---

## 7. Repetición

Para una primera prueba física se recomienda:

- 1 warm-up;
- 5 ejecuciones medidas;
- mismo fixture;
- mismo modelo/configuración siempre que ambos productos lo permitan.

La primera ejecución puede servir para detectar errores de instalación, pero no debe mezclarse silenciosamente con las mediciones si las condiciones difieren.

Con cinco ejecuciones LEONES conserva cada evidencia individual y calcula agregados derivados.

---

## 8. Qué significa "misma tarea"

La igualdad relevante es funcional, no necesariamente de interfaz.

ODS/Hermes puede resolver la tarea con unas herramientas y Magnitude con otras. Eso es parte del objeto de estudio.

No se exige:

- el mismo número de llamadas internas;
- el mismo prompt interno;
- la misma arquitectura de herramientas;
- el mismo servidor;
- el mismo mecanismo de memoria.

Sí se exige:

- mismo objetivo observable;
- mismo fixture;
- mismo criterio de corrección;
- mismo límite de seguridad/workspace;
- misma regla de éxito.

---

## 9. Inferencia y tarea son capas distintas

LEONES mantiene dos registros relacionados pero no los mezcla:

```text
inference evidence
    └── modelo + engine + hardware + tok/s

agentic task evidence
    └── agente + herramientas + tarea + éxito + tiempo
```

Una medición de `llama-cli` sirve para caracterizar inferencia.

Una ejecución de Hermes/Magnitude sirve para caracterizar una tarea agentiva.

No se publica una como sustituto de la otra.

---

## 10. Relación con ODS

ODS ya proporciona la infraestructura que necesitamos:

```text
ODS
 ├── llama-server
 └── Hermes
       ↓
 OpenAI-compatible API
```

LEONES debe observar el sistema sin duplicar esas capas.

La primera hipótesis experimental es por tanto:

`LEONES task runner → Hermes → ODS llama-server → modelo`

La interfaz exacta y la telemetría disponible se verificarán físicamente antes del benchmark.

---

## 11. Relación con Magnitude

Magnitude se prueba por su camino nativo.

La hipótesis documental es:

`LEONES task runner → Magnitude → engine/modelo gestionado por Magnitude`

Si Magnitude permite seleccionar explícitamente un endpoint externo, esa ruta se documentará como una variante de interoperabilidad, no como sustitución silenciosa de su camino nativo.

---

## 12. Hardware de consumo

RC1 prioriza hardware de consumo porque es el objetivo final de LEONES.

El perfil debe registrar como mínimo:

- CPU;
- núcleos/hilos;
- RAM disponible y total;
- GPU/iGPU;
- VRAM cuando exista;
- sistema operativo;
- acelerador/backend utilizado;
- versión del driver/runtime relevante;
- cualquier limitación térmica o energética observable.

Los tiers de hardware son una **clasificación de decisión**, no una sustitución de la medición real.

---

## 13. AirLLM y FreeToken

AirLLM y FreeToken no se convierten en motores paralelos obligatorios de LEONES.

Cuando aporten una mejora real a ODS o Magnitude se seguirá el contrato ya congelado:

1. intentar upstream;
2. si no es inmediato, crear un conector mínimo;
3. medir la mejora;
4. conservar procedencia;
5. evitar forks permanentes.

---

## 14. Publicación en MANADA

Solo se promociona a conocimiento colectivo un resultado que conserve:

```text
tarea
+ configuración
+ hardware
+ ejecución
+ resultado
+ evidencia
+ procedencia
```

Los agregados publicados deben poder rastrearse hasta las ejecuciones originales.

Una cifra sin evidencia no entra como `measured`.

---

## 15. Gate de Ubuntu

**Todavía no se ejecuta Ubuntu.**

Ubuntu pasa a ser imprescindible cuando estén preparados:

- fixture RC1;
- runner mínimo;
- esquema de evidencia;
- adaptador ODS/Hermes;
- adaptador Magnitude;
- comandos de instalación/verificación;
- checklist de hardware;
- ruta de conservación de artefactos.

Entonces la sesión será estrictamente:

```text
instalar
  ↓
verificar
  ↓
ejecutar
  ↓
medir
  ↓
conservar evidencia
```

No se rediseña arquitectura delante de Ubuntu.

---

## Estado

**Diseño RC1 cerrado.**

Siguiente trabajo en repositorio: implementar únicamente los artefactos mínimos que materializan este contrato. Después se solicita Ubuntu para la primera verificación física.
