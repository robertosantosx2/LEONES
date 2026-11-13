# NEPENTHES · Plantilla de informe motor + modelo

> Copiar este documento para cada combinación concreta de motor y modelo. Sustituir todos los campos entre corchetes. No rellenar métricas no medidas: usar `No medido` o `No disponible`.

## 1. Identificación de la ejecución

- **ID Nepenthes:** `NEPENTHES_[MOTOR]_[MODELO]_[AAAAMMDD]`
- **Fecha/hora local:** [ISO 8601 con zona horaria]
- **Host:** [equipo y sistema operativo]
- **Objetivo:** [prueba funcional / rendimiento / memoria / comparación]
- **Tipo de campaña:** [independiente / mismo motor-otro modelo / mismo modelo-otro motor]
- **Estado:** [planificada / ejecutada / validada / incompleta]

## 2. Motor

- **Nombre:** [motor]
- **Repositorio y URL:** [URL]
- **Versión/build:** [versión, build, commit]
- **Binario:** [ruta]
- **Backend:** [CPU/CUDA/Metal/etc.]
- **Argumentos completos:** [comando exacto o enlace a manifest]
- **API/endpoint:** [URL, puerto, API]
- **PID:** [PID durante la ejecución]

## 3. Modelo

- **Nombre/familia:** [modelo]
- **Archivo:** [ruta y nombre exactos]
- **Arquitectura:** [arquitectura]
- **Parámetros:** [total/activos si aplica]
- **Cuantización/formato:** [GGUF/tipo]
- **Tamaño:** [bytes/GiB]
- **SHA-256:** [hash o No calculado]
- **Contexto declarado:** [tokens]

## 4. Plataforma y recursos

| Elemento | Valor |
|---|---|
| CPU | [modelo] |
| RAM | [GiB] |
| Swap | [GiB y uso inicial/final] |
| GPU | [modelo y VRAM] |
| Driver | [versión] |
| CUDA/runtime/toolkit | [versiones o N/A] |
| Kernel | [versión] |
| Procesos competidores | [detalle] |

## 5. Protocolo y controles

- **Tarea/prompt:** [descripción y ubicación del prompt literal]
- **Repeticiones:** [número de ejecuciones independientes]
- **Temperatura:** [valor]
- **max_tokens:** [valor]
- **Presupuesto de razonamiento enviado:** [valor / no enviado]
- **Formato de razonamiento:** [valor]
- **Thinking/template kwargs:** [valores]
- **Contexto/batch/ubatch/threads:** [valores]
- **GPU layers/offload:** [valor]
- **CPU-MoE/caché expertos:** [valores]
- **Caché de prompt:** [fríos/calientes; tokens cacheados]
- **Diferencias respecto a la referencia:** [lista]

Indicar expresamente si el motor confirma que admite y aplica cada extensión de API. Enviar un parámetro no demuestra que el servidor lo haya aplicado.

## 6. Scripts y reproducción

- **Runner:** [enlace al `run_NEPENTHES_*.py`]
- **Inspector:** [enlace al `inspect_NEPENTHES_*.py`]
- **Versión/commit de scripts:** [commit]
- **Comando exacto de ejecución:**

```bash
[comando completo]
```

- **Comando exacto de inspección:**

```bash
[comando completo]
```

- **Directorio de evidencia:** [ruta]
- **Contenido preservado:** [manifest, respuestas, muestras, logs, hashes, archivo comprimido]

## 7. Resultados

| Repetición | Prompt tokens | Tokens generados | Cacheados | Prefill tok/s | Generación tok/s | Finish reason |
|---:|---:|---:|---:|---:|---:|---|
| 1 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

- **Mediana:** [valores]
- **Rango:** [valores]
- **Desviación:** [método y valores]
- **TTFT/TTFM:** [si se midió]
- **VRAM:** [mínimo/media/máximo]
- **RAM/RSS:** [mínimo/media/máximo]
- **CPU:** [métrica]
- **Temperatura/potencia GPU:** [métricas]
- **Swap y disco:** [métricas, indicar si son del sistema o atribuibles al proceso]
- **Errores/timeouts/truncamientos:** [detalle]

No mezclar prefill frío y caliente. No llamar independientes a repeticiones que reutilizan el mismo ID o la misma respuesta.

## 8. Evaluación funcional y calidad

- **Resultado esperado:** [criterios]
- **Resultado observado:** [resumen]
- **Corrección funcional:** [sí/no/parcial/no evaluada]
- **Defectos detectados:** [lista]
- **Pruebas/assertions:** [detalle]
- **Limitaciones:** [detalle]

## 9. Interpretación

[Separar observaciones de hipótesis. Explicar qué variables impiden o permiten comparar con otras ejecuciones.]

## 10. Conclusión

[Conclusión limitada a esta combinación de motor, modelo, configuración, host y fecha.]

## 11. Evidencias y referencias

- [Manifest]
- [Respuesta(s) íntegra(s)]
- [Muestras de recursos]
- [Logs]
- [SHA256SUMS]
- [Archivo tar.gz]
- [Metodología Nepenthes](tandem-qwen35-reasoning-budget-methodology-2026-11-12.md)

---

**Regla de publicación:** un informe corresponde a un único par motor + modelo y una campaña identificada. Si cambia el motor o el modelo, crear otro informe usando esta plantilla.