# Arquitectura visual de REDIL

**Estado:** propuesta documental; no representa un despliegue ya realizado ni validado físicamente.

![Diagrama vectorial de la arquitectura distribuida de REDIL](ARQUITECTURA-REDIL.svg)

## Gráfico complementario — Distributed Llama

![Integración de Distributed Llama como backend opcional de REDIL](DISTRIBUTED-LLAMA-REDIL.svg)

Este segundo gráfico detalla el límite entre el gateway de REDIL y el motor de inferencia distribuida. La ruta convencional sigue disponible como fallback; el adaptador experimental encapsula root/workers, métricas y errores. Las flechas muestran relaciones lógicas, no una instalación existente.

## Cómo leer el diagrama

- **Máquina 1 — Gateway REDIL:** entrada única, políticas, autenticación, enrutamiento, fallback y observabilidad.
- **Máquina 2 — Distributed Llama:** backend opcional y experimental para inferencia distribuida. No sustituye al gateway ni al router de REDIL.
- **Máquinas 3–12:** diez roles de servicio ilustrativos. No significa que haya que disponer de diez ordenadores físicos; los servicios pueden agruparse o reubicarse según mediciones.
- **Almacenamiento y red:** infraestructura lógica compartida. Compartir almacenamiento no implica memoria RAM unificada.

## Límites de esta representación

Las especificaciones de RAM/GPU y la asignación de servicios son perfiles orientativos, no un inventario real de equipos. La compatibilidad con Qwen3.5, LFM3 y cualquier backend concreto debe verificarse con versiones fijadas y pruebas reproducibles. Los resultados publicados o estimados no cuentan como mediciones de LEONES.

La arquitectura y el plan de validación se describen en [README.md](README.md) y [DISTRIBUTED-LLAMA-EXPERIMENTAL.md](DISTRIBUTED-LLAMA-EXPERIMENTAL.md).
