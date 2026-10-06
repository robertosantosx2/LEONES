# LEONES + ODS — Inference Configuration Discovery (ICD)

**Fecha:** 2026-10-06  
**Estado:** EVOLUCIÓN / INVESTIGACIÓN  
**Ámbito:** arquitectura de ejecución LEONES + ODS

## Conclusión

LEONES + ODS debe evolucionar desde la selección de modelo/backend hacia **Inference Configuration Discovery (ICD)**.

La pregunta deja de ser «¿qué modelo puede ejecutar esta GPU?» y pasa a ser:

> **¿Qué configuración de inferencia produce la mejor capacidad real en este hardware, para esta carga de trabajo y este objetivo?**

La configuración completa incluye modelo, cuantización, motor, colocación GPU/CPU/RAM/SSD, contexto, KV-cache, caché de expertos, prefetch, offload, speculative decoding/MTP, flags del runtime y mediciones.

## Por qué Strata es evidencia relevante

La investigación sobre el repositorio original de **Strata (Niko1221/Strata)** muestra una vía distinta para ejecutar modelos MoE grandes: el número total de parámetros no determina por sí solo la utilidad de un modelo en una GPU de consumo.

Los datos publicados que motivan esta investigación describen Qwen3.8-Flash-Next, de 125B parámetros, con colocación heterogénea y gestión adaptativa de expertos. Entre las cifras externas comunicadas aparecen aproximadamente:

| Hardware | Rendimiento comunicado | Estado |
|---|---:|---|
| RTX 5070 12 GB | ~94 tok/s | evidencia externa |
| RX 9070 XT 16 GB | ~60 tok/s | evidencia externa |
| GPUs de 24 GB | ~100–140 tok/s | evidencia externa |

También se comunica una configuración de referencia de GPU de 12 GB o más, 32 GB o más de RAM y unos 80 GB de disco, manteniendo partes calientes del modelo en GPU y otras en memoria del sistema con compresión de pocos bits.

**Estas cifras no son mediciones LEONES.** Son evidencia externa que justifica investigar ICD y deben reproducirse antes de entrar en la capa de evidencia medida de LEONES.

## Cambio arquitectónico

El enfoque clásico es: VRAM suficiente → FIT.

ICD propone: modelo + hardware + almacenamiento + capacidades del runtime + estrategia → configuraciones candidatas → benchmark → capacidad real medida.

Para MoE son relevantes parámetros activos, número de expertos, expertos por token, comportamiento del routing, residencia de expertos, caché, niveles de memoria y costes de transferencia.

## Strata dentro de ODS

Strata debe incorporarse como **proveedor experimental de ejecución / perfil de capacidades**, no simplemente como otro backend.

Capacidades de interés para el registro de ODS:

- ejecución sparse-MoE;
- colocación heterogénea GPU + CPU/RAM;
- asistencia/paging desde SSD;
- caché adaptativa de expertos;
- cuantización de pocos bits;
- ejecución de modelos cuyo peso total supera la VRAM;
- API local compatible con OpenAI;
- API compatible con Anthropic;
- capacidades de gestión mediante MCP;
- soporte multi-GPU cuando corresponda.

El registro debe separar siempre las capacidades del motor de la licencia y disponibilidad de los pesos del modelo.

## ICD en la metodología LEONES

La secuencia existente se amplía:

**DISCOVERY → PROFILE → CANDIDATES → CHOICE + CONSENT → INSTALL → PHYSICAL VERIFICATION → INFERENCE CONFIGURATION DISCOVERY → BENCHMARK → MEASUREMENT → EVIDENCE**

ICD descubre y compara configuraciones de ejecución; no convierte automáticamente una afirmación externa en una medición.

## Dimensiones de una configuración

ODS debe poder comparar, por ejemplo:

- mismo modelo + Q4 + llama-server;
- mismo modelo + offload CPU/RAM;
- cuantización Q3 + caché adaptativa de expertos;
- expertos calientes en GPU y fríos en RAM;
- paging de expertos mediante NVMe;
- speculative decoding;
- configuración híbrida/remota como fallback.

La mejor configuración depende del objetivo: latencia interactiva, throughput, calidad, contexto, privacidad, energía, almacenamiento o coste.

## Arquitectura evolucionada

La cadena pasa a ser:

**Usuario/carga → perfil hardware/workload → Capability Registry → ICD → búsqueda de configuraciones → benchmark controlado → evidencia → mejor configuración real**

En esta arquitectura:

- **FATE** aporta predicción de expertos.
- **Edge0** aporta prefetch/streaming.
- **HOBBIT** aporta caché adaptativa y precisión.
- **HybriMoE** aporta colaboración CPU/GPU.
- **Strata** aporta ejecución MoE heterogénea.
- **WARP** aporta una estrategia especializada de paging/NVMe.
- **TensorFold** aporta un runtime especializado de alto rendimiento.

Estas piezas no tienen que convertirse en backends independientes: sus capacidades pueden participar en la composición y descubrimiento de configuraciones.

## Evidencia y estado

LEONES mantiene la separación:

- **REPORTED** → afirmación del proyecto o comunidad.
- **ESTIMATED** → predicción/modelado.
- **OBSERVED** → estado/configuración observada físicamente.
- **MEASURED** → benchmark controlado de LEONES.

Por tanto, las cifras de Strata siguen siendo **REPORTED / EXTERNAL** hasta reproducirse.

## Impacto sobre fit

La recomendación futura debe distinguir:

**MODEL FIT → CONFIGURATION FIT → PERFORMANCE FIT → TASK FIT → PRIVACY/COST FIT**

Un modelo que arranca pero ofrece una latencia inútil no constituye una buena recomendación. Del mismo modo, que el peso total supere la VRAM no implica automáticamente que el modelo sea inviable si existe una configuración heterogénea que entregue capacidad útil.

## Evolución prevista

1. Definir un esquema canónico de **Inference Profile**.
2. Extender el Capability Registry de ODS con capacidades de ejecución.
3. Representar explícitamente VRAM → RAM → NVMe → remoto.
4. Incorporar propiedades específicas de MoE.
5. Generar configuraciones candidatas, no solo candidatos de modelo/runtime.
6. Ejecutar benchmarks comparables de LEONES.
7. Guardar configuraciones medidas como evidencia reutilizable.
8. Alimentar futuras búsquedas con configuraciones que hayan funcionado.
9. Considerar el proveedor remoto como otra configuración, con privacidad y coste explícitos.

## Decisión

**ICD pasa a ser un concepto de primera clase en la evolución LEONES+ODS.**

Strata queda incorporado como evidencia experimental externa y como candidato a proveedor de ejecución MoE heterogénea. Sus cifras publicadas no se consideran mediciones LEONES hasta su reproducción.

La evolución estratégica queda resumida así:

> **LEONES descubre qué es posible; ODS descubre cómo ejecutarlo mejor.**

El objetivo deja de ser únicamente ampliar la lista de modelos soportados y pasa a construir evidencia reutilizable de:

**modelo + hardware + configuración de inferencia → capacidad real**

## Fuente primaria

Strata — repositorio original: https://github.com/Niko1221/Strata