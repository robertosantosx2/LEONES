# Decisiones — Atlas → recomendador diario enriquecido

**Estado: PROVISIONAL / EN VALIDACIÓN**

## D1 — Separar JGB, CABE y RULA

**Decisión:** mantenerlas como dimensiones independientes.

**Motivo:** apertura/libertad, viabilidad material y utilidad práctica responden a preguntas distintas.

**Invariante:** no calcular JGB a partir de rendimiento; no calcular RULA a partir de CABE.

## D2 — No destructividad del enriquecedor

**Decisión:** `atlas_recommendation_enrich.py` hace merge sobre el CSV existente.

**Alternativa descartada:** generar un CSV nuevo con únicamente las columnas de enriquecimiento.

**Motivo:** una fase posterior no puede destruir datos producidos por fases anteriores.

## D3 — Desconocimiento explícito

**Decisión:** conservar valores desconocidos y estados de evidencia.

**Alternativa descartada:** rellenar automáticamente con valores estimados sin marcar.

**Motivo:** LEONES prioriza evidencia trazable sobre falsa precisión.

## D4 — Validación dentro del workflow

**Decisión:** comprobar columnas críticas antes de publicar.

**Motivo:** un pipeline automático debe fallar de forma visible cuando rompe su contrato de salida.

## D5 — El runtime forma parte de la configuración

**Decisión:** conservar `runtime`, `runtime_version` y `backend` como dimensiones del sistema.

**Motivo:** modelo, hardware y runtime forman una configuración experimental; el nombre del modelo aislado no basta para reproducir rendimiento.

## D6 — Documentación como condición de cierre

**Decisión:** la fase no se considera completamente cerrada hasta documentar arquitectura, reglas, decisiones, validación y trazabilidad.

**Motivo:** el conocimiento de LEONES debe sobrevivir al cambio de código y permitir auditoría y evolución.
