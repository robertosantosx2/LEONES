# Auditoría inicial de subproyectos ODS y Magnitude

> Estado: integración base fijada; auditoría técnica inicial completada.

## ODS

ODS (Osmantic Deployment System) es un servidor de IA local que instala y conecta inferencia, Open WebUI, dashboard, voz, agentes, workflows, RAG, búsqueda, generación de imágenes y herramientas operativas. Su documentación declara soporte para Linux, Windows y macOS, con Intel Arc experimental. La documentación actual declara `v2.6.0` como release estable; LEONES consumirá un commit/tag fijado, nunca `main` implícitamente.

**ODS conserva la responsabilidad de:** instalación, lifecycle, detección de hardware, selección/configuración de modelo, runtime, servicios y health.

**LEONES conserva la responsabilidad de:** preflight independiente, evidencia/procedencia, normalización, benchmark independiente, clasificación T0–T3 y recomendación.

ODS no se convierte en dependencia Python del núcleo LEONES.

## Magnitude

El repositorio oficial objetivo es `magnitudedev/magnitude`, no `magnitudedev/browser-agent`. Magnitude se presenta como agente de coding open source con motor de inferencia local propio; perfila el hardware, recomienda configuraciones de modelo y usa un motor Rust sobre llama.cpp. Su CLI se distribuye como `@magnitudedev/cli` y la documentación actual indica macOS/Linux, con Windows mediante WSL.

**Magnitude conserva la responsabilidad de:** CLI/lifecycle del agente, perfilado de hardware, catálogo/configuración de modelos, inferencia y ejecución del agente.

**LEONES conserva la responsabilidad de:** observación, procedencia, normalización, separación estimado/medido, benchmark independiente y evidencia Atlas.

## Regla común

Ambos proyectos se incorporan como gitlinks fijados a commits concretos. LEONES no copia ni modifica su código fuente. Los adaptadores y contratos viven en LEONES y usan interfaces públicas/documentadas.

## Próxima fase

1. Contrato de preflight/health/evidence para ODS.
2. Contrato equivalente para Magnitude.
3. Adaptadores mínimos.
4. Tests unitarios sin exigir runtime completo en CI.
5. E2E separado con hardware/runtime real.
6. Documentación de instalación, rollback, privacidad y benchmark.
