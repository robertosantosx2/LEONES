# CanIRun.ai — compatibilidad modelo ↔ hardware desde el navegador

**Fuente:** [CanIRun.ai](https://www.canirun.ai/) / [GitHub](https://github.com/midudev/canirun.ai)
**Fecha de incorporación:** 2026-08-25
**Tipo:** fuente técnica + referencia de preselección hardware-aware
**Estado LEONES:** 🟢 conocimiento integrado / 🟡 integración funcional propuesta

## 1. Qué es

CanIRun.ai responde a una pregunta muy próxima al problema inicial de LEONES: **qué modelos de IA abierta puede ejecutar razonablemente este hardware**.

Su propuesta se diferencia de un benchmark físico: detecta el hardware desde el navegador, calcula requisitos aproximados de memoria para diferentes cuantizaciones y genera una clasificación de compatibilidad. El proyecto declara que la detección se realiza en el cliente mediante APIs del navegador como WebGL/WebGPU, `navigator.deviceMemory` y un microbenchmark ligero de CPU; los resultados no se envían al servidor.

La web actual organiza modelos por usos como chat/coding/reasoning, imagen y vídeo, y ofrece vistas de modelos, dispositivos, comparación y tier list. Las fichas de modelo incluyen cuantizaciones y comandos de ejecución para herramientas como Ollama y LM Studio, además de `runai` cuando procede.

## 2. Arquitectura y funcionamiento

El flujo conceptual publicado por el proyecto es:

```text
BROWSER
  ↓
HARDWARE DETECTION
  ├─ CPU / cores
  ├─ RAM
  ├─ GPU / VRAM
  ├─ memory bandwidth
  └─ Apple / mobile / GPU database
  ↓
MODEL MATCHING
  ↓
QUANTIZATION REQUIREMENTS
  ↓
COMPATIBILITY / SPEED / HEADROOM
  ↓
GRADE S–F
  ↓
MODEL RECOMMENDATIONS
```

La documentación del repositorio describe cálculos para siete niveles de cuantización, desde Q2_K hasta F16, y un algoritmo que combina estado de ejecución, velocidad estimada, margen de memoria y tamaño del modelo para producir una nota S–F.

La web también expone una API CORS con endpoints para listar modelos, evaluar compatibilidad y recomendar modelos a partir de un perfil de hardware. Esto convierte CanIRun.ai en algo más interesante para LEONES que una simple interfaz: puede funcionar como **fuente externa de estimaciones normalizables**.

## 3. Qué aporta al conocimiento de LEONES

CanIRun.ai aporta una segunda perspectiva independiente sobre el problema **hardware → modelo**.

En el estado actual de LEONES, su interés principal es triple:

1. **Preselección rápida:** reducir el espacio de modelos antes de descargar pesos o ejecutar benchmarks.
2. **Cross-check de estimaciones:** comparar una estimación externa independiente con LLMFit y con la matriz de hardware de LEONES.
3. **UX de detección automática:** estudiar un flujo de usuario muy corto basado en detección local del equipo y posterior shortlist de modelos.

No debe convertirse en una fuente soberana de decisión. Su score S–F pertenece a CanIRun.ai y debe conservarse como dato externo, no mezclarse con los scores o clasificaciones internas de LEONES.

## 4. Relación con LLMFit

CanIRun.ai y LLMFit atacan una zona parcialmente coincidente, pero desde ángulos diferentes.

```text
                 HARDWARE + INTENCIÓN
                         │
          ┌──────────────┴──────────────┐
          ↓                             ↓
       LLMFit                       CanIRun.ai
   CLI / local / API            Browser / API / UX
          │                             │
          └──────────┬──────────────────┘
                     ↓
             CANDIDATOS EXTERNOS
                     ↓
              ATLAS + EVIDENCIA
                     ↓
            RUNTIME / QUANT / TASK
                     ↓
             BENCHMARK LEONES
                     ↓
              MEDICIÓN REAL
```

La combinación correcta **no es sumar sus scores**. LEONES debe conservar cada resultado como una señal independiente y estudiar posteriormente dónde coinciden y dónde divergen.

Esto abre una línea de validación especialmente útil: **LLMFit estimate vs CanIRun estimate vs measured LEONES**.

## 5. Detección de hardware

CanIRun.ai utiliza información disponible desde el navegador y una base de datos de hardware. Declara soporte para familias NVIDIA RTX 30/40/50, A100/H100, AMD RX, Intel Arc, Apple Silicon y dispositivos móviles, entre otros.

Para LEONES esto es una referencia útil para UX, pero no debe asumirse que la detección del navegador equivale a un inventario físico exhaustivo. El navegador puede ocultar o simplificar características, y la identificación de una GPU mediante renderer strings no demuestra por sí sola el estado real del backend de inferencia.

Por ello, en LEONES la detección debe quedar en la capa de **perfil de hardware**, y la capacidad efectiva de ejecución debe verificarse posteriormente mediante runtime y benchmark.

## 6. Cuantización y memoria

CanIRun.ai calcula requisitos de memoria para varias cuantizaciones: Q2_K, Q3_K_M, Q4_K_M, Q5_K, Q6_K, Q8_0 y F16 en la documentación del proyecto.

La web actual explica que sus cifras de VRAM suponen Q4_K_M y un pequeño overhead de runtime, y advierte que los modelos MoE cargan todos los expertos en memoria aunque solo algunos estén activos por token.

Esto encaja con una regla importante de LEONES:

```text
memoria de pesos
      ≠
memoria total de ejecución

memoria total ≈ pesos + KV cache + runtime overhead
                 + contexto + batch/concurrencia + margen
```

Por tanto, una cifra de CanIRun.ai debe registrarse como **estimación condicionada por supuestos**, nunca como prueba de que un modelo vaya a funcionar con una carga real.

## 7. MoE

La ficha de CanIRun.ai distingue arquitecturas dense y MoE y muestra parámetros activos. Esto es útil porque evita interpretar únicamente el número total de parámetros como coste de cómputo por token.

Sin embargo, LEONES debe conservar separadamente:

- parámetros totales;
- parámetros activos;
- memoria de pesos;
- memoria de ejecución;
- cuantización;
- contexto;
- runtime;
- velocidad estimada;
- velocidad medida.

La estimación de compatibilidad no debe ocultar el coste real de residencia de los expertos ni del runtime.

## 8. API y posible adaptador LEONES

El repositorio documenta una API CORS con, entre otros, estos endpoints:

```text
GET  /api/models
GET  /api/models/:id
POST /api/compatibility
POST /api/recommend
```

El endpoint de compatibilidad acepta un perfil de hardware y un modelo/cuántización; el de recomendación puede devolver modelos compatibles para un perfil determinado.

Esto permite plantear un adaptador independiente:

```text
LEONES selector
      ↓
canirun_adapter
      ↓
JSON normalizado LEONES
      ↓
source = canirun.ai
kind = estimated
      ↓
Atlas / evidencia / filtros
      ↓
Router
```

El adaptador debe conservar versión/fecha de la fuente, hardware utilizado, modelo, cuantización, resultado de compatibilidad, score externo y cualquier supuesto relevante.

## 9. Qué NO debe hacer dentro de LEONES

CanIRun.ai no debe:

- sustituir Atlas como fuente de identidad;
- sustituir el quality gate de evidencia;
- convertir una nota S–F en una clasificación canónica de LEONES;
- convertir `estimated tokens/s` en `measured tokens/s`;
- declarar un modelo `verified` porque CanIRun lo marque como compatible;
- sustituir los benchmarks físicos;
- ocultar las condiciones de cuantización, contexto o runtime;
- mezclarse con LLMFit mediante una media o suma arbitraria de scores.

La regla sigue siendo:

> **Fuente externa → evidencia → estimación → candidato → runtime → benchmark → medición LEONES.**

## 10. Posible papel en el selector

Se propone considerar CanIRun.ai como **preselector externo secundario / cross-validator** del selector LEONES, después de LLMFit y antes de la evaluación física.

Una arquitectura posible sería:

```text
HARDWARE + INTENCIÓN
        ↓
 ┌──────┴─────────┐
 ↓                ↓
LLMFIT         CanIRun.ai
 ↓                ↓
 └──────┬─────────┘
        ↓
  UNION / INTERSECTION
  DE CANDIDATOS
        ↓
Atlas + JGB + evidencia
        ↓
cuantización + runtime
        ↓
benchmark
        ↓
medición LEONES
        ↓
Router
```

La intersección puede servir como filtro conservador cuando ambas fuentes coincidan. Las discrepancias son igualmente valiosas: deben conservarse como **divergencia de estimadores** y pueden alimentar futuras pruebas de calidad.

No debe asumirse que la intersección sea siempre mejor que la unión; la política debe depender del objetivo del selector y de los resultados históricos de validación.

## 11. Valor para la web de conocimiento

La ficha de CanIRun.ai debe enseñar una distinción importante para el usuario:

**"Cabe según un estimador" no significa "rinde bien medido por LEONES".**

La ficha debe permanecer en las cuatro capas del contrato de conocimiento:

- **Fuente / Descubrimiento:** CanIRun.ai y su repositorio upstream.
- **Evidencia:** arquitectura, API, catálogo, cuantizaciones y documentación publicada.
- **Estimación:** compatibilidad, memoria, velocidad y grade S–F calculados por CanIRun.ai.
- **Medición LEONES:** inicialmente pendiente; cualquier benchmark posterior deberá registrar hardware, modelo, cuantización, runtime, contexto y protocolo.

## 12. Relación con el pipeline LEONES

La incorporación encaja en la cadena ya establecida:

```text
PROSPECTOR
   ↓
ATLAS / EVIDENCIA
   ↓
HARDWARE PROFILE
   ↓
LLMFIT ───────────┐
                  ├→ PRESELECCIÓN / CROSS-CHECK
CANIRUN.AI ───────┘
                  ↓
        runtime-selection.v1
                  ↓
              EXECUTOR
                  ↓
               GRADER
                  ↓
              BENCHMARK
                  ↓
        EVIDENCE / MEASUREMENT
                  ↓
                ROUTER
```

CanIRun.ai, por tanto, **no introduce una nueva capa de verdad**. Introduce otra fuente de estimación que debe permanecer separada hasta que LEONES pueda contrastarla experimentalmente.

## 13. Plan de integración

### F0 — Conocimiento

- [x] Analizar web y repositorio upstream.
- [x] Registrar función, arquitectura, API y límites.
- [x] Incorporar ficha a la web de conocimiento.

### F1 — Adaptador de estimación

- [ ] Definir `canirun_adapter`.
- [ ] Normalizar `/api/compatibility` y `/api/recommend`.
- [ ] Registrar procedencia, versión y supuestos.
- [ ] Mantener `estimated` separado de `measured`.

### F2 — Cross-validation

- [ ] Ejecutar LLMFit y CanIRun sobre perfiles hardware equivalentes.
- [ ] Comparar candidatos, cuantizaciones y memoria estimada.
- [ ] Registrar divergencias sin convertirlas automáticamente en errores.

### F3 — Benchmark

- [ ] Seleccionar candidatos divergentes y coincidentes.
- [ ] Ejecutar runtime-selection.v1.
- [ ] Medir rendimiento físico.
- [ ] Calcular error de cada estimador frente a medición LEONES.

### F4 — Selector

- [ ] Utilizar el historial de acierto para ponderar fuentes.
- [ ] Mantener sustituibilidad de CanIRun.ai.
- [ ] No incorporar su score S–F como score LEONES.

## 14. Criterio de éxito

CanIRun.ai será una integración útil si permite mejorar la primera shortlist sin contaminar la semántica de evidencia y medición de LEONES.

El criterio no será que CanIRun.ai "acierte siempre", sino poder responder de forma reproducible:

1. qué predijo;
2. bajo qué supuestos;
3. qué predijo LLMFit;
4. qué decidió el selector LEONES;
5. qué ocurrió realmente al ejecutar;
6. dónde falla cada estimador;
7. qué evidencia posterior permite mejorar el selector.

## 15. Conclusión LEONES

**Sí: CanIRun.ai merece incorporarse como fuente de conocimiento y referencia técnica.** Su valor principal para LEONES es complementar LLMFit con una perspectiva independiente, browser-first y orientada a UX sobre la compatibilidad modelo ↔ hardware.

La posición recomendada es:

> **CanIRun.ai = estimador externo de compatibilidad + referencia de UX; LEONES = sistema de evidencia, selección y medición.**

Su incorporación es especialmente valiosa porque permite evolucionar desde una única estimación de fit hacia un sistema en el que varias fuentes independientes formulan hipótesis y LEONES decide mediante evidencia y medición física.

## Referencias

- [CanIRun.ai](https://www.canirun.ai/)
- [Repositorio oficial](https://github.com/midudev/canirun.ai)
- [API de compatibilidad](https://canirun.ai/api/compatibility)
- [API de recomendación](https://canirun.ai/api/recommend)
