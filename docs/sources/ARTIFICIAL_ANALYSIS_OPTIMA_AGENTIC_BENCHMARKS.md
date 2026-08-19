# Artificial Analysis / Optima — benchmarks de tareas agentivas

## Estado

🟢 **INTEGRADO COMO FUENTE DE CONOCIMIENTO**  
🟡 **Aplicación en Benchmark Agentic V1: siguiente fase**

## Fuente

Vídeo aportado al proyecto:

https://m.youtube.com/watch?v=H-TTBsquXjw

La fuente se incorpora como referencia metodológica para el diseño de evaluaciones agentivas. No se trata de una medición propia de LEONES ni de evidencia de rendimiento de un modelo concreto.

## Qué aprovechamos

La lección principal para LEONES es desplazar el benchmark desde la respuesta aislada del modelo hacia la **tarea completa ejecutada por un sistema agentivo**.

El objeto evaluado debe ser:

```text
MODELO
 + SCAFFOLD / AGENTE
 + HERRAMIENTAS
 + ENTORNO
 + POLÍTICAS / PERMISOS
 + PROTOCOLO DE EVALUACIÓN
        ↓
     EJECUCIÓN
        ↓
 TRAZA + RESULTADO + COSTE
```

Esto encaja con la arquitectura actual de LEONES, donde la evaluación agentiva ya se considera un bloque independiente y el smoke test B01–B05 se reconoce explícitamente como cribado, no como certificación completa. Véase `docs/EVALUACION_AGENTIC_TESTS.md`.

## Principios incorporados

### 1. La unidad básica es la tarea

Una tarea debe tener:

- objetivo explícito;
- condiciones iniciales;
- herramientas disponibles;
- restricciones y permisos;
- criterio de éxito;
- artefacto o estado final esperado cuando proceda;
- presupuesto de tiempo/tokens/coste cuando proceda;
- método de evaluación reproducible.

### 2. Separar outcome y trajectory

LEONES debe registrar dos dimensiones distintas:

**Outcome**

- ¿alcanzó el objetivo?
- ¿el artefacto final es correcto?
- ¿cumplió las restricciones?

**Trajectory**

- pasos realizados;
- llamadas de herramientas;
- argumentos;
- resultados de herramientas;
- errores;
- recuperaciones;
- reintentos;
- tiempo entre pasos;
- tokens/coste cuando estén disponibles.

Un agente puede obtener el resultado correcto con una trayectoria ineficiente o insegura; ambos hechos deben conservarse.

### 3. Herramientas reales

B02 y B04 del smoke test actual no deben confundirse con uso real de herramientas: la documentación vigente ya señala que B02 comprueba capacidad conversacional sobre archivos y que B04 comprueba razonamiento conversacional sobre recuperación. La siguiente generación debe instrumentar ejecución efectiva.

### 4. Grading múltiple

Cuando una tarea no pueda verificarse completamente de forma determinista, se podrán combinar:

- graders deterministas;
- rúbricas estructuradas;
- comparación pairwise;
- revisión humana cuando sea necesaria.

Los graders deben quedar versionados y separados del resultado que evalúan.

### 5. Métricas multidimensionales

No reducir la evaluación a un único score. Registrar como mínimo, cuando sean observables:

- `success`;
- `task_score`;
- `time_seconds`;
- `input_tokens`;
- `output_tokens`;
- `total_tokens`;
- `tool_calls`;
- `tool_errors`;
- `recovery_count`;
- `cost`;
- `safety_violations`;
- `artifact_quality`.

Los campos no observables deben permanecer `unknown`, nunca inferirse.

## Familias propuestas para Agentic Benchmark V1

| Familia | Objetivo |
|---|---|
| A01 Tool Use | Seleccionar y utilizar correctamente una herramienta |
| A02 Multi-step | Resolver una tarea con varios pasos dependientes |
| A03 Files & Artifacts | Crear/modificar/verificar artefactos reales |
| A04 Recovery | Recuperarse de errores reales de herramientas o entorno |
| A05 Long Horizon | Mantener coherencia en tareas largas |
| A06 Research | Buscar, contrastar y sintetizar evidencia |
| A07 Coding | Inspeccionar, modificar, probar y entregar código |
| A08 Local Operations | Ejecutar tareas sobre un entorno local controlado |
| A09 Safety | Respetar permisos, límites y acciones prohibidas |
| A10 Cost/Latency | Resolver dentro de presupuestos de tiempo/coste |

## Diseño de una tarea canónica

```yaml
id: A04-001
family: recovery
objective: "..."
initial_state: "..."
tools:
  - filesystem
  - shell
constraints:
  - "..."
success_criteria:
  - "..."
artifacts:
  - "..."
budgets:
  max_seconds: null
  max_tokens: null
grader: "..."
golden_state: "..."
```

El formato definitivo deberá integrarse con el esquema de resultados de LEONES y no duplicar contratos existentes.

## Trazabilidad

Cada ejecución debe poder reconstruirse mediante:

```text
benchmark_id
→ task_id
→ task_version
→ model_id/version
→ quantization
→ runtime/version
→ scaffold/version
→ hardware_profile
→ tools/version
→ execution_id
→ raw_trace
→ grader_version
→ derived_metrics
```

Esto es especialmente importante para Open LLM Atlas: el resultado agentivo depende del sistema de ejecución y no debe atribuirse automáticamente al modelo aislado.

## Separación de evidencia

La fuente externa proporciona **metodología e inspiración de diseño**.

No debe convertirse automáticamente en:

- benchmark LEONES ejecutado;
- medición LEONES;
- score de un modelo;
- evidencia de hardware;
- evidencia de CABE/RULA.

La cadena oficial continúa siendo:

```text
FUENTE EXTERNA
      ↓
CONOCIMIENTO / MÉTODO
      ↓
DISEÑO DE TAREA
      ↓
EJECUCIÓN LEONES
      ↓
MEDICIÓN PRIMARIA
      ↓
EVALUACIÓN
      ↓
RESULTADO REPRODUCIBLE
```

## Relación con B01–B05

El smoke test actual permanece válido como filtro rápido:

- B01 memoria/localidad
- B02 archivos
- B03 multietapa
- B04 recuperación
- B05 coding

Pero Agentic Benchmark V1 debe convertir especialmente B02 y B04 en pruebas con herramientas instrumentadas y ampliar B03 hacia tareas de mayor horizonte.

## Relación con CABE/RULA

CABE/RULA continúa siendo una clasificación de adecuación por rendimiento de inferencia y no debe mezclarse con la calidad agentiva.

Ejemplo conceptual:

```text
TOKENS/S → CABE/RULA

ÉXITO EN TAREA → AGENTIC PERFORMANCE

TIEMPO/COSTE → EFICIENCIA

SEGURIDAD → SAFETY
```

La recomendación final puede combinar estas dimensiones, pero debe conservarlas separadas y auditables.

## Criterios de aceptación futuros

Agentic Benchmark V1 no se considerará cerrado hasta disponer de:

1. tareas versionadas;
2. entorno reproducible;
3. herramientas reales instrumentadas;
4. trazas primarias conservadas;
5. graders versionados;
6. resultados repetibles;
7. separación entre modelo, runtime y scaffold;
8. métricas de calidad, tiempo y coste;
9. pruebas de recuperación;
10. documentación y CI.

## Regla de higiene

No introducir infraestructura ficticia ni declarar una capacidad medida sin ejecución real. Los resultados estimados deberán marcarse como `estimated`; los ausentes como `unknown`.

---

**Uso en LEONES:** fuente metodológica para el pilar **9. Benchmark & Evaluation** y para la evolución del bloque **7. Agents**.
