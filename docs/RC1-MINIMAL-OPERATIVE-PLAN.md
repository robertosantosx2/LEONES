# LEONES RC1 — Plan de ejecución mínima operativa

> **Estado:** plan canónico de ejecución.
>
> **Objetivo:** llevar LEONES desde investigación y conocimiento hasta una primera ruta física completa, demostrable y publicable, con el mínimo código propio.

## 1. Resultado que buscamos

RC1 no pretende ser una plataforma completa. Debe demostrar una sola cosa importante:

> **Para una tarea concreta y un hardware de consumo concreto, LEONES puede pasar de conocimiento → selección → sistema especializado → ejecución → benchmark → evidencia → publicación en MANADA.**

Todo lo demás se conserva como investigación o se prepara para fases posteriores.

## 2. Arquitectura congelada

```text
PROSPECTOR / INVESTIGACIÓN / ATLAS
              ↓
       perfil de hardware
              ↓
            LLMFit
              ↓
           LEONES
     "qué merece probarse"
              ↓
       ┌──────┴──────┐
       ↓             ↓
     ODS           Magnitude
     SOHO       asistente personal
       │             │
       └──────┬──────┘
              ↓
       runtime real del sistema
              ↓
          tarea real
              ↓
      benchmark LEONES
              ↓
       evidencia física
              ↓
            MANADA
```

`llama.cpp` permanece como ruta física de referencia para validar el contrato de ejecución/medición cuando todavía no corresponda medir ODS o Magnitude.

## 3. Reglas que gobiernan el plan

Se aplican [`LEONES-Rules.md`](LEONES-Rules.md) y [`LEONES-Rules-STRICT.md`](LEONES-Rules-STRICT.md).

La regla de implementación es:

> **Poco código, cada pieza con una responsabilidad, comentarios que expliquen decisiones y README que explique cómo utilizarla.**

La segunda regla es upstream-first: reutilizar antes de construir.

## 4. Fase A — congelar el núcleo

### Objetivo

Determinar qué piezas actuales de LEONES pertenecen realmente al camino RC1.

### Trabajo

- auditar scripts que hacen selección, perfilado, ejecución, medición y publicación;
- identificar duplicaciones;
- conservar Atlas, investigación y conocimiento aunque no estén en el camino mínimo;
- documentar cada script que sobreviva;
- deprecar funcionalidad redundante únicamente después de identificar su sustituto;
- mantener tests del contrato que siga siendo canónico.

### Gate

```text
núcleo pequeño + responsabilidades claras + tests + documentación
```

## 5. Fase B — LLMFit y hardware de consumo

### Objetivo

Usar LLMFit como primera estimación de encaje, no crear otro sistema de fit.

### Trabajo

1. observar el formato real de salida de LLMFit;
2. mapear solamente los datos necesarios al perfil de LEONES;
3. separar estimación de medición;
4. definir tiers operativos de consumo.

### Tiers RC1

Los tiers deben describir capacidades, no prometer rendimiento.

Como mínimo deben contemplar:

- CPU-only con 16 GB;
- CPU-only con 32 GB;
- CPU-only con 64 GB;
- iGPU / memoria compartida;
- GPU de consumo con 8 GB de VRAM;
- GPU de consumo con 12–16 GB de VRAM;
- GPU de consumo con 24 GB o más;
- portátiles con GPU de consumo;
- equipos SOHO con más memoria;
- configuraciones que queden fuera de capacidad.

Los límites exactos se fijarán a partir de las capacidades observadas por LLMFit y de las mediciones LEONES, no de cifras inventadas.

## 6. Fase C — ODS y Magnitude

### Objetivo

No construir un sistema agente nuevo. Integrar el sistema especializado que ya resuelva el escenario.

### ODS / SOHO

Comprobar:

- instalación real;
- punto de entrada;
- motor de inferencia utilizado;
- Hermes y demás componentes ya incluidos;
- forma de seleccionar modelo/runtime;
- interfaz mínima que LEONES necesita.

### Magnitude / asistente personal

Comprobar:

- instalación real;
- punto de entrada;
- arquitectura de agente/asistente;
- gestión de modelos/runtime;
- hardware soportado;
- interfaz mínima que LEONES necesita.

### Decisión

No se decide por preferencia arquitectónica. Se decide según el escenario:

| Necesidad | Ruta |
|---|---|
| SOHO | ODS |
| Asistente personal | Magnitude |
| Caso no cubierto | estudiar otra integración |

## 7. Fase D — AirLLM y FreeToken

No se incorporan como una capa paralela de LEONES.

Cuando aporten una mejora útil:

```text
AirLLM / FreeToken
       ↓
   evaluar valor
       ↓
 ODS / Magnitude
       ↓
 intentar upstream
       ↓
 conector mínimo si es necesario
```

El objetivo es mejorar el sistema que finalmente ejecutará la tarea.

## 8. Fase E — Hermes

Hermes se conserva donde ya forme parte de ODS y aporte su funcionalidad.

LEONES no implementará un Hermes alternativo.

Si la ruta ODS demuestra que Hermes es parte esencial de la trayectoria agentiva, se medirá como parte del sistema ODS, conservando claramente la frontera entre:

- rendimiento del modelo/runtime;
- rendimiento de la trayectoria agentiva;
- éxito de la tarea.

## 9. Fase F — benchmark RC1

RC1 necesita una sola tarea suficientemente representativa para demostrar el recorrido completo.

Antes de ejecutar se fijan:

- objetivo de la tarea;
- prompt/protocolo;
- herramientas permitidas;
- criterio de éxito;
- warm-up;
- repeticiones;
- timeout;
- métricas;
- artefactos conservados.

### Dos capas de resultado

**Runtime:** tokens/s, latencia y métricas que el runtime proporcione de forma comparable.

**Tarea/agente:** éxito, errores, llamadas a herramientas, recuperación, tiempo total y artefactos.

No se mezclan ambas capas en una cifra única sin justificación.

## 10. Fase G — evidencia

JALÓN 3 define el contrato operativo de medición real.

Cada resultado físico debe conservar, cuando corresponda:

- identidad del modelo;
- cuantización;
- runtime y versión;
- hardware real;
- configuración;
- contexto;
- protocolo;
- ejecución;
- timestamps;
- métricas observadas;
- logs;
- artefactos;
- hashes cuando sean aplicables.

La evidencia debe permitir contestar:

> **¿Podría otra persona saber exactamente qué se ejecutó y bajo qué condiciones?**

## 11. Fase H — recomendación

La recomendación se construye después de la evidencia:

```text
fit estimado
   +
restricciones del usuario
   +
medición real
   +
resultado de tarea
   +
TCO cuando esté disponible
   ↓
recomendación
```

Una cifra externa puede orientar la búsqueda, pero no sustituye el dato físico cuando la afirmación es de rendimiento local.

## 12. Fase I — MANADA

MANADA recibe solamente resultados con procedencia clara.

Payload mínimo:

- identidad de modelo;
- hardware;
- runtime;
- configuración relevante;
- tarea/benchmark;
- resultado;
- nivel de evidencia;
- `execution_id`;
- timestamp;
- referencia a artefactos.

La publicación debe conservar la distinción entre `estimated`, `reported`, `observed`, `measured` y `verified`.

## 13. Ubuntu: último gate

Ubuntu no es una fase de diseño.

Se solicita cuando el siguiente paso requiera comprobar físicamente:

- hardware efectivo;
- runtime instalado;
- compatibilidad;
- modelo cargable;
- memoria/VRAM;
- rendimiento;
- comportamiento agentivo;
- consumo.

El procedimiento será:

```text
preflight
→ instalar solo lo imprescindible
→ ejecutar
→ medir
→ conservar evidencia
→ validar
→ publicar
```

## 14. Gate para pedir Ubuntu

Antes de pedir Ubuntu deben estar cerrados:

- [x] Rules.
- [x] JALÓN 3.
- [x] arquitectura RC1.
- [x] frontera ODS/Magnitude.
- [x] regla upstream-first.
- [x] regla AirLLM/FreeToken.
- [ ] auditoría del núcleo mínimo.
- [ ] integración contractual ODS/Magnitude.
- [ ] formato real de LLMFit.
- [ ] tiers RC1 basados en capacidades observadas.
- [ ] benchmark de tarea elegido y fijado.
- [ ] payload MANADA preparado.

Cuando esos puntos estén cerrados, la siguiente acción física será Ubuntu.

## 15. Criterio de éxito RC1

RC1 queda demostrada con **una** trayectoria completa y reproducible:

```text
hardware de consumo
→ LLMFit
→ LEONES
→ ODS o Magnitude
→ runtime real
→ tarea real
→ benchmark
→ evidencia
→ recomendación
→ MANADA
```

No se exige cubrir todos los tiers ni todos los runtimes.

## 16. Después de RC1

Solo después de demostrar el camino mínimo se amplía:

1. más tareas;
2. más hardware de consumo;
3. más modelos;
4. más runtimes;
5. aportaciones upstream de AirLLM/FreeToken;
6. más escenarios ODS/Magnitude;
7. más evidencia colectiva en MANADA.

Cada ampliación debe justificar su coste en código y mantenimiento.

## 17. Definición de terminado

Una pieza está terminada cuando:

- hace una sola cosa;
- tiene la mínima implementación razonable;
- explica las decisiones no obvias en comentarios;
- tiene README/documentación operativa;
- tiene tests adecuados;
- no duplica una capacidad existente;
- deja evidencia cuando corresponde.

Una ruta está terminada cuando además puede ejecutarse de principio a fin y otra persona puede reconstruir qué ocurrió.
