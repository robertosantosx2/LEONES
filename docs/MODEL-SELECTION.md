# LEONES — Capa de selección de modelos

## Estado

**Cerrada como contrato de arquitectura v1.0.**

La selección de modelos responde únicamente a:

> Para una tarea, un perfil de hardware y unas restricciones dadas, ¿qué modelos son técnicamente elegibles y cuáles deben descartarse?

No es un benchmark, no es un ranking económico y no es todavía el router de ejecución.

## Flujo canónico

```text
USUARIO
  │ tarea + contexto + restricciones
  ▼
PERFIL HARDWARE
  │ CPU / RAM / VRAM / capacidades
  ▼
ATLAS / FEED
  │ identidad + evidencia + runtime + cuantización
  ▼
ELEGIBILIDAD
  ├─ identidad
  ├─ workload
  ├─ evidencia T2/T3
  ├─ runtime conocido
  ├─ cuantización o peso observado
  ├─ memoria disponible
  └─ contexto
  ▼
LLMFIT (opcional)
  │ estimación de encaje; nunca medición
  ▼
RANKING
  │ calidad + rendimiento disponible + margen memoria + apertura
  │ SIN PRECIO
  ▼
TOP-N
  │
  ├─ con evidencia suficiente → candidato a ejecución
  └─ sin medición física → BENCHMARK_REQUIRED
```

## Estados

- `REJECTED`: no supera una regla dura.
- `INELIGIBLE`: reservado para consumidores que distingan rechazo de inelegibilidad.
- `CANDIDATE`: estado interno previo a ordenar.
- `SELECTED`: candidato elegible fuera del TOP-N.
- `TOP_N`: candidato dentro del conjunto recomendado.
- `BENCHMARK_REQUIRED`: TOP-N que todavía necesita medición antes de una afirmación final de rendimiento.

Todo rechazo conserva una lista de razones. Nunca se descarta silenciosamente un modelo.

## Reglas duras

1. Debe existir identidad de modelo.
2. El workload declarado debe ser compatible.
3. El hardware declarado no puede contradecir el perfil solicitado.
4. La evidencia técnica debe ser `T2` o `T3`.
5. Debe conocerse el runtime.
6. Debe existir cuantización o tamaño de pesos observado.
7. Debe existir una estimación de memoria.
8. La memoria requerida no puede superar la memoria disponible considerada por el perfil.
9. El contexto declarado, si existe, debe ser válido.
10. Si se exige LLMFit, debe existir candidato LLMFit con clasificación de encaje.
11. Un resultado negativo de LLMFit es motivo de rechazo.

Los valores desconocidos permanecen desconocidos; no se inventan.

## Ranking

El `fit_score` es posterior a la elegibilidad y no decide por sí mismo que un modelo sea ejecutable.

La versión 1 usa únicamente señales técnicas disponibles:

- calidad (`quality_score`),
- rendimiento medido si existe (`tokens_per_second`),
- estimación LLMFit si existe,
- margen de memoria,
- apertura JGB cuando está disponible.

**Precio no participa en el score.** El ranking económico/TCO permanece separado.

## LLMFit

LEONES utiliza el adaptador existente `automation/discovery/llmfit_adapter.py` para normalizar LLMFit. La evidencia conserva explícitamente `estimate_basis=llmfit-estimate` y separa `estimated_tps` de cualquier medición física.

LLMFit sirve como primera estimación de encaje, no como fuente de verdad ni como sustituto del benchmark LEONES.

## Salida canónica

El selector está en `scripts/model_selector.py` y genera JSON con:

- política aplicada,
- recuentos de entrada/elegibles/rechazados/TOP-N,
- candidatos ordenados,
- estado de selección,
- fit por dimensión,
- evidencia LLMFit,
- score,
- confianza,
- razones.

Ejemplo:

```bash
python3 scripts/model_selector.py \
  --workload general \
  --hardware 'Intel i5-1035G1 7GB' \
  --ram 7 \
  --context 4096 \
  --top-n 10
```

Para hacer de LLMFit una condición obligatoria:

```bash
python3 scripts/model_selector.py \
  --workload general \
  --hardware 'Intel i5-1035G1 7GB' \
  --ram 7 \
  --require-llmfit-fit
```

## Tests de contrato

`tests/test_model_selector.py` verifica, entre otras cosas:

- memoria como hard gate;
- T2/T3 como mínimo de evidencia;
- separación entre estimación LLMFit y medición;
- obligación de benchmark cuando falta evidencia de LLMFit;
- independencia respecto del precio;
- trazabilidad de los rechazos.

## Qué queda fuera de esta capa

No se mezclan aquí:

- descarga de modelos;
- elección definitiva de runtime;
- cuantización automática;
- ejecución;
- routing dinámico;
- ODS/Magnitude/Buddy/Hermes;
- benchmark físico;
- TCO.

Esas capas consumen la salida de selección. No deben volver a implementar su propia selección paralela.

## Criterio de cierre

La capa se considera cerrada cuando un consumidor puede proporcionar:

`task + hardware + constraints`

y obtener determinísticamente:

`TOP-N + descartados + razones + evidencia + necesidad de benchmark`.

La medición física puede mejorar posteriormente el ranking, pero no debe cambiar el contrato ni borrar el histórico de la decisión.
