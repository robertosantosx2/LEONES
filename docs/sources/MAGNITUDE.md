# Magnitude — agente e inference engine local

- **Proyecto:** Magnitude
- **Repositorio:** https://github.com/magnitudedev/magnitude
- **Tipo:** agente de coding + motor de inferencia para modelos locales.
- **Estado LEONES:** 🟢 fuente activa · 🟡 subproyecto de integración.
- **Revisión:** 2026-08-20

## Qué aporta

Magnitude combina un agente de coding con un motor de inferencia local. Funciona en macOS y Linux y Windows mediante WSL. La instalación del CLI se realiza con `npm install -g @magnitudedev/cli`. citeturn0search1turn0search7

## Selección automática de modelos

Magnitude perfila el hardware y recomienda modelos que la máquina puede ejecutar. Ofrece perfiles como Balanced, Best Quality, Fastest y Lightweight y gestiona descarga y configuración del modelo. citeturn0search1

Para LEONES esto lo convierte en una fuente relevante de **selección y configuración hardware-aware**, complementaria a LLMFit. La recomendación de Magnitude sigue siendo una señal externa hasta reproducirla.

## Motor de inferencia

El motor está escrito en Rust sobre llama.cpp. Incluye configuraciones de modelos verificadas, calcula requisitos de memoria antes de cargar, y ajusta aceleración, placement y batching al hardware. También mantiene contexto en agentes paralelos y permite cambiar de modelo conservando un comportamiento coherente de herramientas. citeturn0search1turn0search7

## Capacidades agentivas

El agente puede inspeccionar y editar archivos, ejecutar comandos, trabajar con imágenes y mantener tareas largas. El runtime local también expone rendimiento de prefill, reutilización de caché y generación dentro de la interfaz del agente. citeturn0search7

## Skills y extensibilidad

Magnitude permite añadir skills reutilizables. Su README identifica usos como navegador, Excel, PowerPoint, PDF y documentos, mediante paquetes de skills externos. Esto resulta relevante para los benchmarks agentivos de LEONES porque permite evaluar tareas completas, no solo generación de texto. citeturn0search7

## Encaje en LEONES

```text
LEONES
  ├── Atlas / conocimiento
  ├── LLMFit → preselección hardware-aware
  ├── Router → tarea + restricciones + evidencia
  ├── Runtime Selector
  │     └── Magnitude → agente + inference engine
  └── Benchmark Agentic → outcome + trajectory + coste/latencia
```

Magnitude debe tratarse como **runtime + harness/agente**, no solo como un servidor de modelos. Esto lo hace especialmente útil para los benchmarks agentivos de LEONES.

## Integración prevista

1. Subproyecto Magnitude dentro del ecosistema LEONES.
2. Adaptador para descubrir perfil hardware, modelo recomendado y configuración.
3. Registro del runtime y versión del CLI.
4. Captura de configuración de inferencia y modelo.
5. Adaptador de trazas para benchmarks agentivos.
6. Comparación con ODS y con los harnesses de referencia DSH/Buddy/Hermes.
7. Benchmark reproducible antes de convertir cualquier estimación en `measured`.

## Reproducibilidad

El manifiesto LEONES debe conservar, como mínimo: versión de Magnitude/CLI, revisión del motor, SO/arquitectura, hardware, modelo, cuantización, contexto, configuración de aceleración/placement/batching y resultado del benchmark. Un pin técnico candidato previamente identificado (`@magnitudedev/cli 0.0.7-alpha.1`) permanece **no VERIFIED** hasta instalación y ejecución local reproducibles.

## Límites

La capacidad de perfilar hardware y recomendar modelos no equivale a una medición LEONES. El benchmark debe comprobar instalación, estabilidad, calidad de la tarea, TTFT, prefill/decode, latencia, memoria y coste operativo cuando corresponda.

## Fuente primaria

urlMagnitude en GitHubhttps://github.com/magnitudedev/magnitude
