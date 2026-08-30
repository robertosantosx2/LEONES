# JALÓN 3 — Protocolo de medición real y evidencia

**Estado: 🟢 CERRADO OPERATIVAMENTE**  
**Fecha de cierre operativo: 2026-08-28**  
**Contrato:** `runtime-benchmark-evidence.v1.1`  
**Runtime validado:** `llama.cpp`  
**Runner canónico:** `scripts/run_jalon3_audit.sh`

## 1. Decisión

JALÓN 3 queda cerrado de forma operativa. El contrato de medición ya no es solo diseño: existe una ejecución física real que lo satisface y el runner canónico declara:

```text
CONTRACT_GATE=PASS
TESTS_GATE=PASS
DIFF_GATE=PASS
REAL_RUNTIME_EVIDENCE_GATE=PASS
REPRODUCIBILITY_GATE=PASS
JALON3_OPERATIONAL_CLOSE=PASS
AUDIT_EXIT_CODE=0
```

## 2. Evidencia física de cierre

La ejecución aceptada por el runner registra:

- `execution_id`: `rt-8f5164e3648c46a3a91e1f1b637d83f6`
- modelo: `Qwen3-0.6B`
- nombre: `Qwen3 0.6B Instruct Awq`
- cuantización: `Q4_K_M`
- runtime: `llama.cpp`
- versión: `0.3.0-dev (build 10655, commit cb300598d)`
- warm-up: `1`
- mediciones declaradas: `5`
- mediciones encontradas: `5`
- exit code: `0`
- artefacto GGUF identificado y localizado
- SHA-256 del artefacto verificado
- stdout/stderr y mediciones individuales conservados

## 3. Contrato que queda fijado

`runtime-benchmark-evidence.v1.1` exige identidad del modelo y artefacto, protocolo de workload, warm-up, iteraciones, métricas, entorno, runtime, ejecución, stdout/stderr y hashes.

Se mantiene la separación entre:

```text
reported / estimated  !=  measured
API benchmark         !=  local runtime measurement
selection             !=  execution
execution             !=  evidence publication
```

## 4. Runner canónico

`scripts/run_jalon3_audit.sh` es el único punto operativo de auditoría de JALÓN 3.

Garantías fijadas:

- sincronización segura con `origin/<branch>`;
- no fuerza-push;
- bloqueo contra ejecuciones concurrentes;
- rechazo de cambios de trabajo ajenos al runner;
- validación del contrato y schema;
- ejecución completa de pytest;
- `git diff --check`;
- validación física de `llama.cpp`;
- comprobación de hash y tamaño del artefacto;
- comprobación de identidad y reproducibilidad;
- conservación de auditoría local y espejo `docs/audits/jalon3/latest.txt`;
- publicación automática segura con reintentos de sincronización.

## 5. Criterio de cierre satisfecho

El criterio original exigía una ejecución real que pasara por el runtime gate, utilizara un artefacto identificado, ejecutara el runtime real, produjera evidencia válida, conservara las mediciones y stdout/stderr, registrara identidad, timestamps, hardware y versión del runtime y pudiera reutilizarse por el sistema de evidencia/recomendación.

La auditoría física ha demostrado todos esos requisitos.

## 6. Regla de continuidad

No se rediseña JALÓN 3 ni se altera retroactivamente su evidencia.

El flujo queda fijado como:

```text
selección → runtime gate → ejecución → medición → evidencia → validación → conservación
```

La siguiente etapa debe consumir este contrato, no crear otro sistema paralelo.

## 7. Siguiente bloque

El siguiente bloque lógico es cerrar el contrato de decisión **LEONES → ODS | Magnitude**, usando además **LLMFit** como fuente de ajuste/fit cuando corresponda, y derivar los tiers de hardware de consumo de las capacidades reales de esas herramientas.

Los tiers de LEONES no podrán convertirse en una segunda base de datos de modelos: serán una capa de interpretación sobre las salidas de ODS, Magnitude y LLMFit.
