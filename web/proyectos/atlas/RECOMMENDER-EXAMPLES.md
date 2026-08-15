# Recommender v0.1 — casos iniciales

Estos casos son **plantillas de evaluación**, no mediciones de rendimiento. Las celdas de calidad, tok/s y JGB permanecen vacías hasta disponer de evidencia.

## Caso A — CPU 16 GB, chat

```text
hardware = cpu-i5-16gb
workload = chat
contexto mínimo = 4K
```

Candidatos iniciales: Qwen3-8B Q4_K_M.

El motor puede evaluar memoria/contexto, pero **no debe afirmar una velocidad ni una clasificación JGB sin evidencia**.

## Caso B — CPU 32 GB, coding

```text
hardware = cpu-i7-32gb
workload = coding
contexto mínimo = 8K
```

Candidato inicial: Qwen3-14B Q4_K_M.

La recomendación final queda pendiente de observaciones de rendimiento y evidencia de calidad/JGB.

## Caso C — CPU 64 GB, coding/chat

```text
hardware = cpu-i7-64gb
workload = coding o chat
contexto mínimo = 8K
```

Candidato inicial: Qwen3-30B Q4_K_M.

Es una configuración candidata por capacidad de memoria, no una afirmación de que sea la mejor opción.

## Caso D — 128 GB, reasoning

```text
hardware = cpu-128gb
workload = reasoning
contexto mínimo = 16K
```

Candidato inicial: Qwen3-30B Q4_K_M.

La adecuación de calidad y rendimiento requiere datos de evidencia.

## Caso E — RTX 4060 8 GB

```text
hardware = rtx4060-8gb
```

Candidatos iniciales: Qwen3-8B y Qwen3-14B en Q4_K_M, según workload y configuración real.

La VRAM disponible no debe interpretarse como garantía de que toda la ejecución ocurra exclusivamente en GPU: el runtime y la configuración de offload importan.

## Regla de estos ejemplos

```text
CANDIDATO
   ≠
RECOMENDACIÓN FINAL
```

Los ejemplos prueban la conexión del motor con la matriz de deployments. El ranking definitivo comienza cuando el Atlas tenga observaciones y evidencias suficientes.
