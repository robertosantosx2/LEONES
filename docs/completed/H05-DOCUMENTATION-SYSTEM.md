# H05 — Sistema documental de LEONES

## 1. Por qué existe

Un proyecto con muchos scripts y workflows puede funcionar y, aun así, ser imposible de mantener. H05 convierte la documentación en parte del mecanismo de cierre.

La regla es:

```text
IMPLEMENTAR → VALIDAR → ACEPTAR → DOCUMENTAR → ENLAZAR → CERRAR
```

## 2. Qué es una fase

Una fase es un paquete de trabajo que tiene objetivo, alcance, arquitectura, decisiones, validación y estado. Los identificadores Hxx permanecen estables para conservar trazabilidad.

## 3. Qué significa aceptada

Una fase 🟢 ACEPTADA debe tener implementación validada, documentación y referencias suficientes para poder explicar por qué se considera cerrada.

Aceptar no significa que la tecnología quede congelada. Significa que el comportamiento acordado tiene una base comprobada y que las mejoras posteriores pueden identificarse como evolución.

## 4. Documentos de una fase

Cuando procede, un paquete contiene:

- `README.md`: qué es, para qué sirve y cuál es su estado.
- `ARCHITECTURE.md`: cómo se conectan las piezas.
- `DECISIONS.md`: por qué se eligió una solución.
- `VALIDATION.md`: qué se comprobó y con qué evidencia.
- `DIAGRAMS.md`: esquemas complejos que merecen mantenerse aparte.

## 5. Por qué también documentamos fuera de la fase

La documentación de fase responde a «¿qué se aceptó?». La documentación de `docs/completed/` responde a «¿cómo lo mantiene una persona que acaba de llegar?». Son preguntas distintas.

Por eso los dos niveles se enlazan y no se sustituyen.

## 6. Limpieza

Una fase terminada debe quedar sin trazas de depuración ni borradores sin propósito. Pero un fixture, ejemplo o dato sintético utilizado para una prueba reproducible debe conservarse y explicarse.

La limpieza nunca debe eliminar evidencia de aceptación ni archivos necesarios para repetir una prueba.

## 7. Cómo actualizar una fase terminada

Si un cambio altera el contrato, hay que:

1. identificar el hito afectado;
2. explicar el cambio;
3. actualizar arquitectura/decisiones si procede;
4. ejecutar validaciones;
5. actualizar el estado;
6. revisar los README y enlaces;
7. solo entonces volver a declarar la fase aceptada.

## Enlaces

- Protocolo: [`docs/DOCUMENTATION_PROTOCOL.md`](../DOCUMENTATION_PROTOCOL.md)
- Índice de fases: [`docs/phases/README.md`](../phases/README.md)
- Auditoría: [`docs/phases/PHASE_AUDIT_2026-08.md`](../phases/PHASE_AUDIT_2026-08.md)
- Decisiones: [`LEONES_DECISION_LOG.md`](../../LEONES_DECISION_LOG.md)
