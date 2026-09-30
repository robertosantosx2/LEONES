# WARP — fuente de conocimiento para LEONES

- **Proyecto:** WARP (Weight-Aware Runtime and Paging)
- **Repositorio histórico:** https://github.com/sqliteai/waste
- **Repositorio actual:** https://github.com/sqliteai/warp
- **Tipo:** runtime de inferencia local especializado en modelos MoE grandes mediante paging/streaming de pesos.
- **Estado LEONES:** 🟢 fuente activa · 🟡 candidato de integración con ODS · ⏳ pendiente de benchmark propio.
- **Revisión:** 2026-09-30

> **Regla de evidencia:** las cifras, compatibilidades y resultados publicados por WARP son evidencia externa hasta que LEONES los reproduzca. No se convierten automáticamente en measured.

## Qué aporta

WARP intenta ejecutar modelos MoE cuyo conjunto completo de pesos puede superar la memoria disponible. Utiliza almacenamiento rápido para traer los pesos necesarios y RAM como caché. El cuello de botella puede desplazarse hacia ancho de banda NVMe, latencia, routing, contexto y caché.

## Evolución desde WASTE

El repositorio histórico sqliteai/waste se presenta actualmente como WARP. LEONES conserva la referencia histórica porque análisis anteriores pueden usar el nombre WASTE, pero las nuevas fichas utilizan WARP como nombre principal.

## API

El servidor ofrece una interfaz compatible con OpenAI y documenta endpoints como /health, /v1/models, /v1/chat/completions y /v1/completions. Esta es la razón principal para considerarlo integrable en ODS sin acoplar sus aplicaciones al código interno del runtime.

## Modelos

La documentación pública contempla modelos MoE grandes de varias familias, incluidas Kimi, DeepSeek y GLM. Los containers publicados van desde decenas de GB hasta cientos de GB y aproximadamente 1 TB para modelos muy grandes. El tamaño debe registrarse por modelo y revisión concreta.

## Hardware y almacenamiento

Registrar CPU, RAM total/disponible, VRAM, dispositivo de almacenamiento, filesystem, throughput, latencia y límites de cgroup. WARP puede ser interesante cuando no existe suficiente memoria para alojar todos los pesos, pero compatibilidad no equivale a rendimiento útil.

El almacenamiento es parte del runtime. Un benchmark debe registrar dispositivo, interfaz, filesystem, capacidad libre, lectura sostenida, latencia, rendimiento desde el contenedor y bytes leídos.

## Compatibilidad con ODS

El encaje recomendado es como extensión opcional:

```text
ODS
 ├── llama-server
 └── WARP extension
          ↓
     OpenAI API
```

No se recomienda sustituir llama-server. WARP debe seleccionarse cuando modelo, hardware y almacenamiento cumplan los requisitos de paging.

## Compatibilidad con LEONES

```text
modelo + hardware + runtime + storage
                  ↓
       hipótesis de compatibilidad
                  ↓
         ejecución física
                  ↓
             measured
```

Esto evita atribuir al modelo un resultado que procede del runtime o del almacenamiento.

## Evidencia

| Estado | Significado |
|---|---|
| external | Información procedente de WARP. |
| reported | Resultado declarado por una fuente externa identificable. |
| observed | Configuración comprobada durante una ejecución. |
| measured | Resultado reproducido mediante benchmark LEONES. |

La ficha actual no aporta resultados measured de LEONES.

## Benchmark recomendado

- versión de WARP;
- revisión del modelo;
- arquitectura;
- tamaño del container;
- RAM y VRAM;
- NVMe y filesystem;
- throughput;
- tiempo de carga;
- TTFT;
- prefill y decode tok/s;
- RAM/VRAM pico;
- bytes leídos;
- estabilidad;
- contexto.

## Valor estratégico

WARP amplía el espacio de búsqueda de LEONES desde la pregunta «¿cabe el modelo en VRAM/RAM?» hacia «¿puede ejecutarse de forma reproducible mediante paging desde el almacenamiento disponible y con una latencia aceptable para la tarea?».

## Fuentes primarias

- https://github.com/sqliteai/warp
- https://github.com/sqliteai/waste
