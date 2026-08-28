# LEONES RC1 — Núcleo mínimo operativo

> **Estado: EN CONSTRUCCIÓN**
>
> Este documento convierte `LEONES Rules` en un plan ejecutable. El objetivo de RC1 no es terminar LEONES: es demostrar una única cadena mínima, limpia y reproducible desde el hardware del usuario hasta conocimiento publicado.

## 1. Objetivo de RC1

RC1 debe poder responder de forma demostrable:

> **Dado un hardware de consumo y una tarea, ¿qué modelo/runtime es razonable, qué ruta de ejecución conviene, qué ocurrió realmente al ejecutarla y qué evidencia podemos publicar?**

La ruta canónica queda congelada como:

```text
HARDWARE
   ↓
LLMFit
   ↓
LEONES
   ├── identidad/evidencia
   ├── fit y decisión
   └── selección de ruta
          ↓
   ┌──────┴────────┐
   ↓               ↓
 ODS / SOHO     Magnitude / personal
   ↓               ↓
 ejecución real / agente
   └──────┬────────┘
          ↓
   benchmark LEONES
          ↓
   evidencia física
          ↓
      validación
          ↓
        MANADA
```

LEONES es el **árbitro de evidencia y medición**. ODS y Magnitude son posibles superficies/entornos de ejecución. LLMFit es una primera señal de encaje.

---

## 2. Qué NO vamos a construir en RC1

Para proteger el minimalismo:

- no otro detector de hardware completo si LLMFit/ODS ya proporcionan la capacidad;
- no otro agente generalista si ODS ya aporta Hermes;
- no otro servidor de inferencia;
- no otro catálogo de modelos;
- no una capa propietaria para cada runtime;
- no soporte simultáneo de todos los runtimes;
- no un benchmark universal de todos los modelos;
- no duplicar la lógica de ODS o Magnitude dentro de LEONES;
- no incorporar AirLLM o FreeToken al núcleo antes de demostrar su necesidad.

Una integración que no contribuya a la ruta RC1 queda fuera del camino canónico o se mueve a `deprecated`.

---

## 3. Fase A — Reconocimiento de capacidades existentes

### Objetivo

Determinar con precisión qué debemos aportar nosotros y qué debemos consumir de proyectos externos.

### LLMFit

LLMFit ya detecta hardware, puntúa modelos por fit, velocidad estimada, calidad y contexto, ofrece JSON para automatización y dispone de benchmark real de tok/s/TTFT. Su documentación actual también describe comandos `fit`, `recommend --json`, `info`, `bench` y `doctor`.

Por tanto, LEONES no debe duplicar ese trabajo. Debe consumirlo como **señal de preselección** y conservar su procedencia.

Referencia: [LLMFit](https://github.com/AlexsJones/llmfit).

### ODS

ODS ya empaqueta inferencia local con `llama-server`, interfaz, dashboard, selección automática de modelo/hardware, agentes, workflows, RAG y observabilidad. Hermes es actualmente su ruta agentiva local por defecto.

Por tanto, LEONES debe aprovechar ODS como **plataforma SOHO**, no reconstruirla.

Referencias:

- [ODS](https://github.com/Osmantic/ODS)
- [Hermes en ODS](https://github.com/Osmantic/ODS/blob/main/ods/docs/HERMES.md)
- [ODS Quickstart](https://github.com/Osmantic/ODS/blob/main/ods/QUICKSTART.md)

### Magnitude

Magnitude queda como segunda superficie de ejecución para el escenario de **asistente personal**, especialmente cuando su enfoque y capacidades aporten algo que ODS no cubra de forma suficiente.

LEONES debe mantener esta frontera: **decidir primero; ejecutar después; medir siempre desde LEONES**.

---

## 4. Fase B — Contrato LLMFit → LEONES

### Entrada mínima

```json
{
  "hardware": {},
  "use_case": "",
  "runtime_preferences": [],
  "context_tokens": 0
}
```

### Salida mínima normalizada

```json
{
  "source": "llmfit",
  "source_version": "",
  "observed_at": "",
  "hardware": {},
  "candidate": {
    "model_id": "",
    "model_name": "",
    "fit": "",
    "estimated_tps": null,
    "estimated_memory_gb": null,
    "context_tokens": null,
    "quantization": null,
    "runtime": null
  },
  "provenance": {
    "kind": "estimated",
    "raw_artifact_sha256": ""
  }
}
```

### Regla

El adaptador no puede convertir `estimated_tps` en `measured_tps`.

Una medición posterior de LEONES debe generar un nuevo registro y conservar el vínculo con la hipótesis original.

---

## 5. Fase C — Tiers de hardware de consumo

Los tiers de RC1 deben ser **operativos**, no una clasificación estética.

Como mínimo deben distinguir:

| Dimensión | Debe conservarse |
|---|---|
| CPU | modelo/arquitectura/hilos |
| RAM | capacidad utilizable |
| GPU | fabricante/modelo |
| VRAM | capacidad |
| iGPU/unified memory | sí/no y capacidad cuando sea posible |
| aceleración | backend real |
| almacenamiento | capacidad libre relevante |
| OS | familia/versión |
| runtime | backend concreto |

La clasificación inicial puede usar bandas, pero nunca debe ocultar los valores observados.

### Principio

```text
Tier = resumen operativo
Hardware profile = evidencia detallada
```

ODS puede tener sus propios tiers. LEONES no los copia ciegamente: los conserva como información externa y define su propia taxonomía mínima cuando sea necesaria para comparar escenarios.

---

## 6. Fase D — Decisión ODS vs Magnitude

La decisión se produce aquí:

```text
LLMFit
  ↓
LEONES
  ↓
¿SOHO / servidor personal?
  │
  ├── sí → ODS
  │          └── Hermes cuando proceda
  │
  └── asistente personal → Magnitude
```

No significa que cada caso deba usar exactamente una opción. Significa que RC1 tiene una **decisión explícita y trazable**, en lugar de mezclar plataformas sin criterio.

### Criterios mínimos

- compatibilidad hardware;
- modelo candidato;
- contexto requerido;
- runtime disponible;
- modalidad de uso;
- agente/herramientas necesarios;
- coste operacional;
- posibilidad de medir;
- reproducibilidad.

La decisión debe producir una razón legible, no solo un identificador.

---

## 7. Hermes: aprovechar, no duplicar

Hermes se incorpora a RC1 **a través de ODS** cuando ODS sea la ruta elegida.

No se crea un `LEONES Hermes`.

LEONES conserva:

- qué versión de ODS/Hermes se utilizó;
- qué modelo/backend recibió Hermes;
- configuración relevante;
- ejecución;
- trazas/evidencia disponible;
- resultado de la tarea;
- mediciones LEONES.

Hermes aporta la capa agente; LEONES aporta la disciplina de medición y evidencia.

---

## 8. Fase E — AirLLM y FreeToken

Quedan **fuera del núcleo RC1 inicial**.

Cuando la ruta ODS/Magnitude esté funcionando, se evaluarán como capacidades candidatas para aportar:

```text
AirLLM / FreeToken
       ↓
¿la capacidad falta en ODS/Magnitude?
       ↓
¿es útil en hardware de consumo?
       ↓
¿podemos contribuir upstream?
   ┌───┴────┐
  sí       no
   ↓        ↓
upstream  conector fino
```

El objetivo es evitar forks y evitar que LEONES se convierta en un contenedor de tecnología ajena.

---

## 9. Fase F — Benchmark LEONES

El benchmark se ejecuta **después de la decisión de plataforma**.

Debe fijar:

- modelo/revisión;
- cuantización;
- runtime/versión;
- hardware;
- contexto;
- prompt/protocolo;
- warm-up;
- iteraciones;
- límite de salida;
- TTFT si está disponible;
- tokens/s;
- memoria/VRAM si está disponible;
- consumo si está disponible;
- comando;
- stdout/stderr;
- timestamp;
- `execution_id`;
- hash del artefacto.

### Dos familias de medición

**Runtime benchmark**

Mide la capacidad de inferencia.

**Agent benchmark**

Mide una tarea real: trayectoria, herramientas, éxito, errores, tiempo y artefactos.

Nunca se mezclan ambas en una única cifra.

---

## 10. Fase G — MANADA

MANADA es el destino de conocimiento, no la fuente de verdad de una medición.

Solo se publica como conocimiento validado aquello que haya superado el gate correspondiente.

La publicación debe mantener:

- origen;
- timestamp;
- hardware;
- modelo;
- runtime;
- configuración;
- método;
- evidencia;
- versión del contrato.

---

## 11. Fase H — instalación real

Primero se completa todo lo posible fuera de Ubuntu:

```text
contrato
→ fixtures
→ adaptador
→ tests
→ documentación
→ simulación
→ integración
→ gate
```

**Solo entonces Ubuntu.**

### Primera sesión Ubuntu prevista

La primera sesión física tendrá como objetivo demostrar una sola ruta completa, no explorar el sistema.

Checklist previsto:

1. instalar/verificar LLMFit;
2. capturar hardware;
3. producir candidatos;
4. ejecutar LEONES;
5. elegir ODS o Magnitude;
6. ejecutar la tarea;
7. medir;
8. conservar evidencia;
9. validar;
10. preparar publicación MANADA.

Cuando lleguemos a este punto, se avisará explícitamente: **«AHORA NECESITO UBUNTU»**.

---

## 12. Fase I — Deprecación

Una vez que la ruta RC1 esté demostrada, se auditará todo el repositorio.

Se clasifica cada pieza:

| Estado | Significado |
|---|---|
| `canonical` | participa en RC1 |
| `supporting` | necesario para una pieza canónica |
| `experimental` | útil pero no necesario |
| `deprecated` | trabajo histórico fuera del camino actual |

Lo deprecated se mueve o marca en una rama/directorio explícito y no debe ser importado por la ruta canónica.

No se elimina evidencia histórica.

---

## 13. Orden de ejecución

### Paso 1 — ahora

- congelar reglas;
- documentar LLMFit;
- crear contrato de integración;
- definir tiers mínimos;
- identificar duplicaciones.

### Paso 2

- construir adaptador LLMFit → LEONES;
- tests unitarios y contractuales;
- fixture reproducible.

### Paso 3

- implementar decisión ODS/Magnitude como contrato;
- no ejecutar todavía;
- tests de selección.

### Paso 4

- preparar adaptador de ejecución mínimo;
- preparar captura de evidencia;
- preparar benchmark.

### Paso 5

**Aquí aparecerá Ubuntu.**

### Paso 6

- ejecución física;
- benchmark;
- evidencia;
- validación.

### Paso 7

- MANADA;
- auditoría final;
- deprecación de lo que haya quedado fuera.

---

## 14. Criterio de RC1 terminado

RC1 está terminado cuando podemos demostrar al menos un caso completo:

```text
hardware de consumo real
      ↓
LLMFit
      ↓
LEONES
      ↓
ODS o Magnitude
      ↓
modelo/runtime real
      ↓
tarea real
      ↓
benchmark LEONES
      ↓
evidencia validada
      ↓
MANADA
```

Y podemos reconstruir la respuesta sin depender de memoria humana ni de una terminal perdida.

---

## 15. Regla de cierre

> **Una ruta completa y reproducible es RC1. Todo lo demás es backlog hasta que esa ruta exista.**

Documento normativo complementario: [`docs/LEONES-RULES.md`](LEONES-RULES.md).
