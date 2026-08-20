# llmfit — primera estimación de modelo por hardware

**Fuente:** [llmfit](https://www.llmfit.org/) / [GitHub](https://github.com/AlexsJones/llmfit)
**Fecha de incorporación:** 2026-08-20
**Tipo:** fuente técnica + componente potencial de preselección
**Estado LEONES:** 🟢 conocimiento integrado / 🟡 integración funcional propuesta

## 1. Qué aporta

`llmfit` es una herramienta local que detecta RAM, CPU, GPU/VRAM y backend disponible y utiliza esos datos para puntuar modelos según **quality, speed, fit y context**. Además selecciona una cuantización y un modo de ejecución que considere viable, incluyendo GPU, CPU+GPU, CPU y offload para MoE. La documentación pública indica soporte para configuraciones multi-GPU, arquitecturas MoE, selección dinámica de cuantización y proveedores/runtimes locales como Ollama, llama.cpp, MLX, Docker Model Runner y LM Studio.

La herramienta expone CLI, TUI, salida JSON y una REST API local (`llmfit serve`). Esto último es especialmente interesante para LEONES porque permite convertir llmfit en una capa de preselección consumible por el recomendador y por otros componentes sin acoplar el núcleo de LEONES a la interfaz de terminal.

## 2. Qué NO debe hacer dentro de LEONES

llmfit debe considerarse **estimador/preselector**, no fuente de verdad del Atlas ni sustituto de las métricas propias.

En particular:

- su `score` no sustituye JGB, CABE, RULA ni ninguna clasificación canónica de LEONES;
- una estimación de velocidad no se convierte en `tokens_per_second` medido;
- que un modelo `fit` no demuestra que funcione correctamente con una carga de trabajo real;
- la base de modelos de llmfit no sustituye la identidad/evidencia/quality gate del Atlas;
- una cuantización elegida por llmfit es una hipótesis operativa que debe conservarse como tal;
- los benchmarks comunitarios externos deben permanecer separados de las mediciones LEONES.

Esto mantiene la regla de LEONES: **DESCUBRIMIENTO → EVIDENCIA → NORMALIZACIÓN → VERIFICACIÓN/MEDICIÓN → ATLAS → RECOMENDACIÓN**.

## 3. Por qué encaja especialmente bien en LEONES

LEONES ya dispone de una matriz de hardware, Atlas, rendimiento, CABE/RULA y recomendador. El problema de la primera interacción con el usuario es distinto: antes de disponer de mediciones propias para su máquina concreta necesitamos una respuesta inicial razonable a:

> «Con este equipo y para esta tarea, ¿qué modelos merece la pena probar primero?»

llmfit cubre precisamente esa primera capa: **hardware real → modelos que caben → cuantización → modo de ejecución → estimación inicial de velocidad/contexto → candidatos**.

La integración propuesta es, por tanto, como **preselector hardware-aware del Router**, no como reemplazo del recomendador completo.

## 4. Flujo propuesto

```text
USUARIO
  ↓
PERFIL DE USO + OBJETIVO
  ↓
HARDWARE DETECTADO / PERFIL MANUAL
  ↓
LLMFIT (primera estimación)
  ↓
TOP-N CANDIDATOS VIABLES
  ↓
IDENTIDAD + EVIDENCIA ATLAS
  ↓
JGB / LICENCIA / SELF-HOSTABILITY
  ↓
CABE / RULA / RENDIMIENTO MEDIDO (si existe)
  ↓
TASK INTELLIGENCE + ROUTER LEONES
  ↓
MODELO RECOMENDADO
  ↓
BENCHMARK / PRUEBA REAL
  ↓
ACTUALIZACIÓN DE EVIDENCIA
```

La idea clave es que **llmfit reduce el espacio de búsqueda antes de gastar recursos en evaluación**.

## 5. Primera recomendación al usuario

La primera respuesta de LEONES no debería ser «este es el mejor modelo», sino una selección corta y explicable:

1. **Candidato principal:** mejor equilibrio entre ajuste al hardware y tarea.
2. **Candidato calidad:** el modelo de mayor calidad que siga siendo viable.
3. **Candidato velocidad:** el que ofrezca la mejor estimación de respuesta dentro del objetivo.
4. **Candidato económico/ligero:** menor coste computacional que mantenga calidad suficiente.

Para cada candidato deben mostrarse, como mínimo:

- modelo/versión;
- parámetros y arquitectura cuando estén disponibles;
- cuantización propuesta;
- memoria estimada y margen;
- modo de ejecución;
- contexto objetivo;
- velocidad estimada, explícitamente marcada como `estimated`;
- fuente de la estimación;
- estado de evidencia en Atlas;
- CABE/RULA si existe medición propia;
- runtime recomendado;
- motivo de selección y principales riesgos.

## 6. Cómo combinar el score de llmfit con LEONES

**No se debe sumar directamente el score de llmfit al `fit_score` existente.**

Se propone conservar sus dimensiones como campos independientes:

```text
llmfit_quality_estimate
llmfit_speed_estimate
llmfit_fit
llmfit_context_fit
llmfit_quantization
llmfit_run_mode
llmfit_memory_estimate
llmfit_runtime
llmfit_source_version
```

Y después construir una decisión LEONES mediante sus propios criterios:

```text
CANDIDATOS LLMFIT
    + identidad/evidencia Atlas
    + licencia/JGB
    + tarea
    + CABE/RULA
    + rendimiento medido
    + coste/precio
    + runtime
    + requisitos de privacidad
    = RECOMENDACIÓN LEONES
```

Esto evita que una herramienta externa se convierta accidentalmente en el criterio soberano del proyecto.

## 7. API como punto de integración

La REST API de llmfit ofrece, entre otros, endpoints para hardware y modelos top. La documentación pública muestra:

```text
GET /api/v1/system
GET /api/v1/models/top?limit=5&min_fit=good&use_case=coding
GET /api/v1/models?min_fit=marginal&runtime=llamacpp&sort=score&limit=20
```

Esto permite una arquitectura limpia:

```text
LEONES UI / CLI
       ↓
  selector inicial
       ↓
 llmfit adapter
       ↓
 JSON normalizado LEONES
       ↓
 Atlas + Router + CABE/RULA
```

La integración debe admitir también un modo **sin llmfit**, porque la disponibilidad de este componente no puede ser un requisito duro para ejecutar el resto del ecosistema.

## 8. Perfil de hardware y perfil de usuario

Hay que separar dos entradas:

### Hardware

- CPU / núcleos;
- RAM disponible;
- GPU(s);
- VRAM;
- memoria unificada cuando corresponda;
- backend/runtime disponible;
- sistema operativo;
- restricciones de energía/portabilidad si el usuario las declara.

### Intención

- uso general;
- coding;
- reasoning;
- chat;
- multimodal;
- embedding;
- agente;
- contexto deseado;
- latencia objetivo;
- velocidad mínima aceptable;
- privacidad/offline;
- preferencia de runtime.

La selección inicial debe cruzar ambas dimensiones. Un modelo que «cabe» pero no satisface la tarea no debe llegar al primer puesto solo por memoria.

## 9. Contexto y memoria

La estimación debe respetar la distinción ya adoptada por LEONES entre tamaño de pesos y memoria total de ejecución.

La memoria efectiva debe considerar, al menos:

```text
pesos cuantizados
+ KV cache
+ overhead del runtime
+ concurrencia/batch
+ margen de seguridad
```

El documento de conocimiento de LEONES sobre LLMs establece además que un modelo que apenas cabe y hace offload agresivo puede ser técnicamente ejecutable pero prácticamente inadecuado. llmfit debe servir para descartar esos casos tempranamente, no para maquillarlos como recomendaciones equivalentes.

## 10. MoE

llmfit reconoce modelos MoE y distingue parámetros totales de parámetros activos para estimar el coste de ejecución. Esto es valioso para LEONES porque evita descartar automáticamente modelos MoE por su número total de parámetros.

Aun así, LEONES debe conservar por separado:

- parámetros totales;
- parámetros activos;
- memoria real/estimada;
- velocidad estimada;
- velocidad medida;
- runtime y configuración.

## 11. Integración con CABE/RULA

La primera estimación puede usar llmfit para priorizar candidatos, pero la decisión de usabilidad de LEONES debe terminar en la evidencia propia cuando exista.

```text
llmfit speed estimate
        ↓
   preselección
        ↓
 benchmark real
        ↓
 tokens_per_second (medido)
        ↓
 CABE / RULA
```

Se conserva el dato continuo `tokens_per_second`; la clasificación no sustituye la medición, siguiendo la regla ya fijada en H09.

## 12. Integración con Router

La integración natural es convertir llmfit en la **fase 0 del Router**:

```text
FASE 0 — hardware fit
FASE 1 — task fit
FASE 2 — evidence/licence fit
FASE 3 — measured performance fit
FASE 4 — runtime fit
FASE 5 — final route
```

De esta forma, el Router no evalúa cientos de modelos contra todas las dimensiones desde cero. Primero recibe un conjunto físicamente plausible.

## 13. Integración con la primera UX de usuario

La interfaz debería pedir inicialmente solo lo necesario:

```text
¿Para qué quieres usar la IA?
[Chat] [Coding] [Reasoning] [Agente] [Multimodal] [Otro]

¿Dónde quieres ejecutarla?
[Este equipo] [Otro equipo]

¿Quieres detectar automáticamente el hardware?
[Sí] [No]
```

Si el usuario acepta detección local, LEONES puede consultar llmfit y devolver inmediatamente una primera shortlist. Si no puede ejecutarse llmfit, se usa el perfil de hardware ya disponible en LEONES.

La segunda interacción debe permitir ajustar preferencias: velocidad, calidad, contexto, privacidad y runtime.

## 14. Evidencia y reproducibilidad

Cada recomendación inicial debe registrar:

- versión de llmfit;
- versión/fecha del catálogo utilizado;
- perfil de hardware detectado;
- perfil de intención;
- contexto solicitado;
- candidatos devueltos;
- configuración de cuantización/runtime;
- score externo de llmfit, sin reinterpretarlo;
- fecha/hora de la estimación;
- decisión final de LEONES;
- si posteriormente hubo medición real.

Esto permitirá estudiar posteriormente cuánto acierta la primera estimación frente a la medición real.

## 15. Fase de implementación recomendada

### F0 — Fuente de conocimiento

- [x] Incorporar llmfit como fuente documental.
- [x] Registrar procedencia y límites.
- [x] Documentar su papel como estimador externo.

### F1 — Adaptador

- [ ] Crear `llmfit_adapter`.
- [ ] Consultar CLI/JSON o REST local.
- [ ] Normalizar la salida al contrato LEONES.
- [ ] Versionar la procedencia.

### F2 — Preselector

- [ ] Recibir hardware + intención.
- [ ] Solicitar top-N candidatos.
- [ ] Aplicar filtros de evidencia/identidad Atlas.
- [ ] Aplicar JGB/licencia/self-hostability.

### F3 — Router

- [ ] Integrar la shortlist en el Router.
- [ ] Combinar con CABE/RULA y mediciones propias.
- [ ] Devolver explicación de por qué se selecciona cada candidato.

### F4 — Validación

- [ ] Comparar estimaciones llmfit con benchmarks reales.
- [ ] Medir error de velocidad y memoria.
- [ ] Identificar familias/hardware donde la estimación sea poco fiable.
- [ ] Ajustar reglas LEONES sin modificar retrospectivamente las mediciones.

## 16. Criterio de éxito

La integración se considerará útil cuando, para una máquina y tarea nuevas, LEONES pueda producir en pocos segundos una shortlist de modelos que:

1. caben con margen razonable;
2. tienen runtime viable;
3. son compatibles con la intención del usuario;
4. tienen identidad/evidencia suficiente;
5. no confunden estimación con medición;
6. puedan pasar directamente a benchmark real;
7. permitan sustituir llmfit posteriormente sin romper el Router.

## 17. Conclusión LEONES

**Sí: llmfit merece incorporarse.** Su mayor valor no es decidir el modelo final, sino resolver de forma rápida y reproducible la primera pregunta física del recomendador: **qué modelos tienen sentido probar en este hardware**.

La arquitectura recomendada es:

> **llmfit = preselector hardware-aware; LEONES = sistema de decisión final.**

Esto encaja especialmente bien con el estado actual del proyecto: H08 aporta la matriz de hardware, H09 aporta CABE/RULA y mediciones, H10 aporta el pipeline Atlas → recomendador y el pilar Router necesita precisamente una fase inicial de reducción del espacio de candidatos.

---

## Referencias

- [llmfit](https://www.llmfit.org/)
- [Repositorio oficial](https://github.com/AlexsJones/llmfit)
- [How llmfit works](https://github.com/AlexsJones/llmfit/blob/main/docs/how-it-works.md)
- [CLI y automatización](https://github.com/AlexsJones/llmfit/blob/main/docs/cli.md)
