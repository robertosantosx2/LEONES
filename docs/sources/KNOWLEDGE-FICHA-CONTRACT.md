# Contrato de fichas de conocimiento LEONES

## Propósito

La sección **Conocimiento de IA en Local** no es un directorio de enlaces. Es la capa documental que transforma una fuente externa, proyecto, herramienta, runtime, workspace o metodología en conocimiento trazable que pueda alimentar la prospección de LEONES sin confundirse con evidencia propia.

Cada ficha debe permitir responder seis preguntas:

1. **Qué es** el proyecto o fuente.
2. **Qué problema intenta resolver**.
3. **Qué evidencia primaria existe** y de dónde procede.
4. **Qué puede aprender LEONES**.
5. **Qué no demuestra** y qué queda pendiente de verificar.
6. **Cómo podría entrar en el pipeline ejecutable** si supera los gates correspondientes.

## Capas que nunca deben mezclarse

```text
FUENTE / DESCUBRIMIENTO
        ↓
ANÁLISIS LEONES
        ↓
EVIDENCIA PRIMARIA
        ↓
CANDIDATO
        ↓
QUALITY GATE
        ↓
LLMFit / FIT
        ↓
runtime-selection.v1
        ↓
EXECUTOR
        ↓
GRADER
        ↓
BENCHMARK
        ↓
EVIDENCE LEONES
        ↓
ROUTER / ATLAS
```

Una ficha puede recomendar estudiar un proyecto sin recomendar utilizarlo. Una cifra externa puede conservarse como evidencia externa sin convertirse en una medición LEONES.

## Estructura obligatoria de una ficha ampliada

### 1. Identidad

- nombre oficial;
- nombre de referencia LEONES cuando sea necesario desambiguar;
- organización/autores;
- repositorio oficial;
- documentación/paper/proyecto oficial;
- licencia cuando esté verificada;
- fecha de revisión;
- estado de procedencia.

### 2. Qué es

Explicación comprensible y técnicamente precisa. Debe identificar su **capa arquitectónica**: modelo, cuantización, runtime, serving, despliegue, selector, benchmark, harness, workspace, agente, herramienta o fuente metodológica.

### 3. Qué no es

Esta sección es obligatoria cuando exista riesgo de confusión entre capas. Ejemplos:

- FreeToken no es un selector de modelos.
- Odysseus no es un runtime de inferencia.
- LLMFit no es el benchmark canónico de LEONES.
- Magnitude no convierte automáticamente sus estimaciones en mediciones LEONES.

### 4. Arquitectura y mecanismos

Explicar los mecanismos que justifican su interés: memoria, scheduling, caché, offload, cuantización, agentes, herramientas, MCP, serving, hardware-awareness, etc. No basta con repetir marketing.

### 5. Evidencia

Separar explícitamente:

- **evidencia primaria**: paper, repositorio oficial, documentación del autor;
- **evidencia externa**: benchmark o análisis de terceros;
- **estimación**: predicción de una herramienta;
- **medición LEONES**: ejecución reproducible propia.

Las cifras deben conservar sus condiciones: hardware, modelo, versión, cuantización, contexto, workload, concurrencia y configuración cuando estén disponibles.

### 6. Valor para LEONES

Explicar qué hipótesis del proyecto confirma, cuestiona o amplía. Debe conectarse con componentes reales de LEONES y no limitarse a una descripción general.

### 7. Integración propuesta

Cuando corresponda, representar la cadena concreta:

```text
selector → runtime-selection.v1 → executor → grader → evidence → Router
```

Para un workspace/harness:

```text
modelo → runtime → endpoint → workspace/harness → workload → grader
```

### 8. Variables que debe considerar el selector

Cuando la fuente afecte a selección o runtime, enumerar variables relevantes. Para runtimes MoE, por ejemplo:

- VRAM;
- RAM;
- ancho de banda de memoria;
- host↔GPU/PCIe;
- transferencia CPU↔GPU;
- tamaño total/activo de expertos;
- localidad y reutilización;
- KV cache;
- contexto;
- workload;
- latencia objetivo;
- throughput;
- compatibilidad modelo/cuanti/runtime.

### 9. Qué debe medir LEONES

Definir los campos mínimos necesarios para convertir la hipótesis externa en evidencia reproducible. Como mínimo, identidad de modelo/runtime, hardware, versiones, configuración, memoria, TTFT, TPOT/tokens por segundo, throughput bajo concurrencia, contexto, resultado del workload y artefactos del grader cuando sea aplicable.

### 10. Limitaciones

Registrar explícitamente:

- hardware soportado;
- sistemas operativos;
- dependencias;
- compatibilidad de modelos;
- estado de desarrollo;
- issues relevantes;
- ausencia de evidencia;
- condiciones que impidan generalizar resultados.

### 11. Clasificación LEONES

Usar estados claros, por ejemplo:

- `source-inspiration`
- `research-candidate`
- `runtime-candidate`
- `workspace-reference`
- `harness-reference`
- `preselector`
- `verified-primary`
- `measured`
- `rejected`
- `unresolved`

La clasificación describe el estado dentro de LEONES; no pretende calificar universalmente el proyecto.

### 12. Conclusión

Cerrar con una decisión documental breve:

- qué aporta;
- dónde encaja;
- qué prioridad tiene;
- qué falta para convertirlo en candidato ejecutable;
- qué evidencia debe producirse antes de influir en el Router.

## Regla específica para FreeToken y Odysseus

Los dos proyectos deben permanecer separados porque representan capas diferentes:

```text
                   LEONES
                      │
          ┌───────────┴───────────┐
          │                       │
 runtime-selection          workload / workspace
          │                       │
      FreeToken               Odysseus
          │                       │
          └──── endpoint ─────────┘
                    │
                 workload
                    │
                 grader
                    │
                 evidence
```

Esto permite evaluar una combinación **FreeToken + Odysseus** sin convertir ninguno de los dos en autoridad sobre el otro.

## Regla editorial de la web

La ficha web debe ser un resumen navegable de la ficha documental, no una copia superficial. Cada tarjeta debe contener como mínimo:

- identidad y clasificación;
- explicación de qué es;
- problema que resuelve;
- cómo lo utiliza LEONES;
- límites/evidencia;
- enlace a la ficha ampliada;
- enlace a la fuente primaria.

Las fichas especialmente importantes —FreeToken, Odysseus, LLMFit, AirLLM, Magnitude, ODS y las metodologías de evaluación— deben disponer de una sección suficientemente amplia para que un lector pueda entender su papel sin abrir el repositorio.

## Regla de trazabilidad

> **Descubrir no es verificar. Estimar no es medir. Ejecutar no es aprobar. Medir no es recomendar automáticamente.**

Una señal externa solo puede influir en la recomendación final después de atravesar los gates definidos por LEONES y conservar su procedencia.
