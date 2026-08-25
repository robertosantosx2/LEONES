# Cross-validation de Fit / CanIRun — 2026-08-25

## Objetivo
Comparar de forma controlada los estimadores externos de compatibilidad hardware/modelo antes de convertir sus resultados en candidatos para `runtime-selection.v1`.

## Fuentes
1. LLMFit — https://github.com/AlexsJones/llmfit
2. CanIRun.ai — https://github.com/midudev/canirun.ai
3. localmodel.run — https://github.com/ansumanshah/localmodel.run
4. VRAMBudget — https://github.com/webdevtodayjason/vrambudget
5. LLM Checker — https://github.com/signerless/llm-checker
6. LLM-Hardware-Advisor — https://github.com/gitstq/LLM-Hardware-Advisor

## Regla fundamental
Ningún resultado externo se convierte directamente en `measurement` ni en recomendación final. Cada fuente conserva identidad, versión/fecha y metodología.

## Matriz común
| Dimensión | Registro requerido |
|---|---|
| Hardware | CPU, GPU, VRAM, RAM, almacenamiento, bandwidth si disponible |
| Modelo | repo/model id, parámetros, arquitectura, MoE/active params |
| Cuantización | formato, bits, fichero/tamaño |
| Contexto | tokens de contexto y KV assumptions |
| Runtime | runtime/backend si la fuente lo explicita |
| Fit | yes/no/score/unknown |
| Memoria estimada | valor + unidad + fuente |
| Throughput estimado | tok/s + metodología |
| Fuente | URL + versión/commit/fecha |
| Evidencia | claim reproducible |
| Medición LEONES | solo después del executor real |

## Conjunto inicial de pruebas
### Perfil H01 — CPU-only
- Intel i5/i7
- RAM: 16 GB
- GPU: ninguna
- Objetivo: modelos pequeños/medianos y cuantizados.

### Perfil H02 — CPU + 32 GB
- Intel i7 equivalente
- RAM: 32 GB
- GPU: ninguna
- Objetivo: comprobar cómo cambian los límites de memoria y contexto.

### Perfil H03 — RTX 4060 8 GB
- GPU: NVIDIA RTX 4060 8 GB
- RAM: 32 GB
- Objetivo: cuantización, offload y diferencia entre fit y throughput.

### Perfil H04 — workstation 64 GB
- RAM: 64 GB
- GPU configurable
- Objetivo: MoE/offload y modelos que exceden VRAM.

## Modelos iniciales
El conjunto debe incluir deliberadamente casos fáciles, fronterizos y claramente imposibles:
- 7–9B instruct cuantizado.
- 14–16B cuantizado.
- 30–35B cuantizado.
- 70B cuantizado.
- un MoE cuyo total de parámetros exceda ampliamente la VRAM.

No se fija un modelo concreto aquí si la versión exacta del artefacto no está registrada. La prueba debe usar identificador y cuantización exactos.

## Clasificación de discrepancias
- `AGREE_FIT`: todos los estimadores relevantes coinciden.
- `AGREE_NO_FIT`: coinciden en no-fit.
- `MEMORY_DISAGREEMENT`: difieren en memoria prevista.
- `FIT_DISAGREEMENT`: uno o más dicen fit y otro no.
- `PERFORMANCE_DISAGREEMENT`: fit coincide pero throughput estimado diverge.
- `METHODOLOGY_GAP`: no existe dato comparable.
- `STALE_DATA`: fuente sin versión/fecha suficientemente reciente.

## Quality gate
Una discrepancia no se resuelve mediante promedio de scores. Se conserva el resultado de cada fuente y se abre un caso de verificación.

Orden de resolución:
1. verificar modelo/cuanti/contexto exactos;
2. verificar hardware detectado;
3. verificar supuestos de KV cache/overhead;
4. verificar runtime/backend;
5. ejecutar benchmark LEONES;
6. registrar `measured_*` y evidencia;
7. documentar qué estimador acertó o falló.

## Integración con runtime-selection.v1
El cross-validator solo produce `candidate_evidence` y señales de confianza. El selector debe poder distinguir:
- `fit_external`;
- `fit_consensus`;
- `fit_verified`;
- `performance_estimated`;
- `performance_measured`.

Solo `fit_verified` + requisitos funcionales satisfechos + benchmark válido puede promover un candidato a recomendación fuerte.

## Resultado esperado
Construir un dataset de discrepancias, no un ranking de herramientas. El objetivo es aprender qué estimaciones son robustas, en qué hardware fallan y qué variables deben pasar al contrato `runtime-selection.v1`.

## Estado
`designed-not-run` — contrato y matriz definidos; falta ejecutar las combinaciones con los estimadores y el executor controlado.