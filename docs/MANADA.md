# LEONES — MANADA

## Estado

**🟢 Arquitectura funcional cerrada · implementación pendiente**

MANADA es la capa de coordinación de múltiples modelos/agentes. No sustituye al Router: el Router decide **qué recurso o combinación de recursos conviene**; MANADA decide **cómo coordinar los participantes elegidos**.

## Principio

```text
USUARIO
  ↓
ROUTER
  ↓
selección / composición
  ↓
MANADA
  ├── agente/modelo A
  ├── agente/modelo B
  ├── agente/modelo C
  └── herramientas
  ↓
COORDINACIÓN
  ↓
SÍNTESIS / RESULTADO
```

MANADA no debe convertir automáticamente varias llamadas en "mejor resultado". La coordinación debe tener objetivo, roles, criterio de parada y evidencia.

## Modos

### 1. Single
Un único participante. MANADA actúa como capa transparente.

### 2. Secuencial
Un participante entrega su salida al siguiente.

### 3. Especialistas
Cada participante recibe una función definida: investigación, coding, crítica, verificación, síntesis, etc.

### 4. Debate / crítica
Participantes independientes generan propuestas y otro participante critica o sintetiza.

### 5. Router + fallback
Se prueba el candidato principal y se activa un segundo participante según una condición verificable.

### 6. Verificación
Un participante produce y otro comprueba. La verificación no se considera automáticamente verdadera: conserva evidencia y resultado.

## Roles

Los roles son explícitos y trazables. Ejemplos:

- `planner`
- `researcher`
- `coder`
- `critic`
- `verifier`
- `executor`
- `synthesizer`

Un modelo/agente puede ocupar varios roles, pero cada ejecución debe registrar el rol efectivo.

## Criterios de coordinación

Cada MANADA debe definir:

- objetivo;
- participantes;
- roles;
- orden o grafo de ejecución;
- herramientas autorizadas;
- contexto compartido;
- criterio de parada;
- condición de fallback;
- estrategia de síntesis;
- límite de coste/tiempo;
- evidencia requerida.

## No concurrencia: matiz importante

La regla global de LEONES impide concurrencia **en escritores de datos canónicos**. No significa que MANADA no pueda ejecutar participantes en paralelo cuando la tarea lo requiera.

```text
Ejecución de agentes:
  secuencial o paralela según el plan

Escritura canónica:
  SIEMPRE un único writer
```

Las salidas paralelas se recogen primero como resultados de ejecución y solo después pasan al escritor canónico.

## Presupuesto

MANADA debe respetar límites de:

- tiempo;
- tokens;
- llamadas;
- coste;
- memoria/contexto;
- herramientas.

Si se alcanza un límite, la ejecución termina según el criterio de parada y queda registrada como `budget_exhausted` cuando corresponda.

## Seguridad

Ningún agente obtiene automáticamente las capacidades de otro. Las herramientas se conceden por ejecución y rol.

Debe quedar trazado:

- quién pidió la herramienta;
- qué herramienta se invocó;
- con qué entrada;
- qué devolvió;
- si falló;
- qué agente recibió el resultado.

## Evidencia

MANADA distingue:

```text
salida generada
≠
hecho verificado
≠
resultado de herramienta
≠
resultado físico medido
```

La síntesis no puede elevar una afirmación a evidencia únicamente porque varios agentes coincidan.

## Integración con Agentic

MANADA consume únicamente elementos Agentic elegibles según el circuito LEONES:

```text
Agentic catalogue
      ↓
Gate OSI
      ↓
Evidence / quality
      ↓
Atlas
      ↓
Router
      ↓
MANADA
```

## Integración con Router

El Router puede solicitar:

- un único agente;
- una pareja productor/verificador;
- una composición especializada;
- un fallback;
- una manada completa.

MANADA no puede modificar las preferencias del usuario ni saltarse las restricciones duras del Router.

## Resultado

La salida debe contener, como mínimo:

- resultado final;
- participantes;
- roles;
- secuencia/grafo ejecutado;
- herramientas usadas;
- fallos y recuperaciones;
- coste/tiempo cuando esté disponible;
- evidencia asociada;
- nivel de confianza;
- razón de terminación.

## Observabilidad

Cada ejecución debe disponer de un `run_id` y trazabilidad suficiente para reconstruir la secuencia. Los resultados intermedios no se pierden por sintetizar el resultado final.

## No concurrencia de workflows

Todo workflow que escriba resultados canónicos de MANADA utiliza exclusivamente `leones-main-writers` y `cancel-in-progress: false`.

La ejecución paralela interna de agentes no crea writers adicionales.

## Criterio de cierre

La arquitectura funcional de MANADA queda cerrada. La implementación y las pruebas reales quedan pendientes; no se certifica rendimiento, calidad ni superioridad de ningún patrón hasta disponer de evidencia reproducible.
