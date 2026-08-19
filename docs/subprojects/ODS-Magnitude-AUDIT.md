# Auditoría inicial de subproyectos ODS y Magnitude

> Estado: base de integración fijada; auditoría técnica inicial.

## 1. ODS

ODS (Osmantic Deployment System) es un servidor de IA local que instala y conecta inferencia, Open WebUI, dashboard, voz, agentes, workflows, RAG, búsqueda, generación de imágenes y herramientas operativas. Su documentación declara soporte para Linux, Windows y macOS, con Intel Arc en estado experimental. La versión estable declarada es `v2.6.0`; para integración reproducible LEONES se utilizará un commit/tag fijado, no `main` como dependencia implícita.

### Responsabilidad de ODS

- instalación y lifecycle del stack;
- detección de hardware y selección de modelo;
- configuración del runtime;
- arranque/parada de servicios;
- health y operación del stack.

### Responsabilidad de LEONES

- preflight independiente;
- captura de evidencia y procedencia;
- normalización del perfil técnico;
- benchmark independiente;
- clasificación T0–T3;
- recomendaciones y trazabilidad.

ODS no debe convertirse en una dependencia Python del núcleo LEONES.

## 2. Magnitude

La organización oficial `magnitudedev` mantiene actualmente el repositorio `magnitude`, descrito como agente de coding open source con motor de inferencia local propio. El README declara instalación mediante `@magnitudedev/cli`, soporte macOS/Linux y Windows mediante WSL, perfilado de hardware, recomendación automática de modelos y un motor de inferencia Rust sobre llama.cpp.

El repositorio oficial correcto para esta integración es:

`https://github.com/magnitudedev/magnitude`

El repositorio `magnitudedev/browser-agent` es otro producto: agente de navegador vision-first. No se debe confundir con el Magnitude coding agent que constituye el subproyecto objetivo.

### Responsabilidad de Magnitude

- CLI y lifecycle del agente;
- perfilado de hardware;
- catálogo y configuración de modelos;
- inferencia local;
- ejecución del agente y herramientas.

### Responsabilidad de LEONES

- observar sin modificar silenciosamente la configuración;
- registrar modelo/runtime/backend/quantización/hardware;
- distinguir configuración recomendada de medición observada;
- ejecutar benchmark independiente cuando proceda;
- producir evidencia reutilizable por Atlas.

## 3. Regla de integración

Los subproyectos se mantienen como gitlinks fijados a commits concretos. LEONES no copia ni modifica su código fuente. Los adaptadores y contratos viven en LEONES y apuntan a la interfaz pública/documentada de cada subproyecto.

## 4. Próxima fase

1. Fijar el gitlink de Magnitude al repositorio oficial `magnitudedev/magnitude`.
2. Crear contratos de preflight/health/evidence para ODS.
3. Crear contratos equivalentes para Magnitude.
4. Añadir adaptadores mínimos.
5. Añadir tests sin exigir que el runtime completo esté instalado en CI.
6. Reservar E2E con hardware/runtime real para una fase separada.
