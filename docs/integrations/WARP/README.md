# WARP ↔ ODS ↔ LEONES
**Perfil:** runtime experimental para inferencia de modelos Mixture-of-Experts grandes mediante weight-aware paging y streaming desde NVMe.

**Estado LEONES:** 🟢 fuente activa · 🟡 candidato de integración con ODS · ⏳ pendiente de benchmark LEONES propio.

## 1. Resumen ejecutivo

WARP (Weight-Aware Runtime and Paging), anteriormente publicado bajo el repositorio sqliteai/waste, es un runtime especializado en ejecutar modelos MoE cuyo conjunto completo de pesos puede superar la memoria disponible. Mantiene en memoria el estado necesario y utiliza almacenamiento rápido para cargar expertos según el routing.

Para ODS, WARP no debe sustituir a llama-server. El encaje recomendado es como backend opcional y especializado para modelos MoE grandes.

```text
ODS
 ├── llama-server → modelos convencionales
 └── WARP         → MoE grandes / paging NVMe
                         ↓
                  API OpenAI-compatible
```

## 2. Qué aporta a ODS

- Ejecución de MoE cuyo conjunto completo de pesos no cabe en RAM/VRAM.
- Uso activo de NVMe como parte del sistema de memoria de inferencia.
- Servidor compatible con API OpenAI.
- Separación limpia entre runtime y aplicaciones consumidoras.
- Posibilidad de ampliar el catálogo de modelos ejecutables de ODS.

## 3. Encaje arquitectónico

La primera integración debería ser una extensión opcional, siguiendo el patrón de servicios de ODS:

```text
extensions/services/warp/
├── manifest.yaml
├── compose.yaml
├── Dockerfile
└── README.md
```

El servicio WARP debería exponer un endpoint interno y registrarse en LiteLLM u otra capa de enrutamiento de ODS. Los endpoints documentados incluyen /health, /v1/models, /v1/chat/completions y /v1/completions.

## 4. Por qué no sustituir llama-server

WARP está deliberadamente especializado. Su principal ventaja aparece cuando el modelo es un MoE grande y la memoria es el cuello de botella. Para modelos convencionales o suficientemente pequeños, el backend normal de ODS sigue siendo el camino general.

```text
modelo convencional → llama-server
MoE grande          → WARP
```

## 5. Storage: requisito de primer orden

WARP cambia la importancia del almacenamiento. Los containers publicados pueden ocupar desde decenas de GB hasta cientos de GB y, para modelos muy grandes, aproximadamente 1 TB. El rendimiento depende fuertemente del almacenamiento rápido y sostenido.

Antes de instalar un modelo WARP, ODS/LEONES debería comprobar:

- espacio libre;
- dispositivo y tipo de interfaz;
- NVMe interno cuando sea posible;
- throughput sostenido;
- latencia;
- filesystem;
- acceso desde el contenedor;
- comportamiento de acceso directo cuando corresponda;
- margen para cachés y otros modelos.

No debe tratarse un modelo WARP como si fuera un GGUF convencional.

## 6. Docker y ODS

La contenerización necesita validación específica porque WARP depende mucho del rendimiento del almacenamiento. La primera implementación debería utilizar un bind mount dedicado y medir el rendimiento desde dentro del contenedor.

Debe verificarse: visibilidad del NVMe, permisos, filesystem, acceso directo, límites de memoria de cgroup, throughput y estabilidad durante sesiones largas.

## 7. Modelos y hardware

La documentación pública contempla familias MoE grandes de Kimi, DeepSeek y GLM, entre otras. Las cifras de tamaño y rendimiento son evidencia externa hasta su reproducción por LEONES.

El preflight debe registrar CPU, RAM, RAM disponible, VRAM, almacenamiento, filesystem, throughput y límites de cgroup. Una cifra externa de RAM mínima no garantiza ejecución útil.

En el equipo ODS documentado actualmente (i7-12650H, 14–16 GB RAM, RTX 3050 Laptop 4 GB), Kimi K3 no es un objetivo práctico según los requisitos publicados. Los modelos WARP más pequeños pueden ser candidatos experimentales, pero deben medirse físicamente.

## 8. Integración con LEONES

```text
HARDWARE
   ↓
LLMFit / Atlas
   ↓
candidatos
   ↓
Runtime Selector
 ├── llama-server
 └── WARP
      ↓
RAM + NVMe + modelo
      ↓
preflight → consentimiento → instalación → benchmark
                                           ↓
                                        MEASURED
```

LEONES debe conservar la separación: evidencia externa → reported/estimated; configuración observada → observed; benchmark propio → measured.

## 9. Contrato de datos recomendado

Registrar cuando estén disponibles: runtime_id=warp, versión, modelo y revisión, arquitectura, tamaño del container, contexto, RAM/VRAM, dispositivo de almacenamiento, filesystem, capacidad libre, throughput, bytes leídos, latencia, tiempo de carga, TTFT, prefill tok/s, decode tok/s, tokens/s sostenidos y estabilidad. Los datos no observados permanecen unknown/null.

## 10. Benchmark mínimo

1. Fijar versión de WARP.
2. Fijar revisión del modelo.
3. Registrar hardware y límites de cgroup.
4. Registrar almacenamiento.
5. Medir carga inicial.
6. Medir TTFT, prefill y decode.
7. Medir RAM/VRAM pico.
8. Registrar I/O y bytes leídos.
9. Repetir con contextos crecientes.
10. Comprobar sesiones largas y estabilidad.

## 11. Licencia y privacidad

El runtime se publica bajo Apache-2.0 según el repositorio primario. Las licencias de pesos deben revisarse por separado. La integración debe seguir las reglas locales de ODS/LEONES: sin recopilar prompts ni conversaciones y sin publicar resultados sin consentimiento.

## 12. Propuesta de implementación

### Fase 1 — prueba aislada
Validar runtime → modelo → health → API OpenAI → benchmark.

### Fase 2 — extensión ODS
Crear extensions/services/warp/ con manifest, Compose, Dockerfile y documentación.

### Fase 3 — backend opcional
Registrar WARP sin alterar el backend por defecto.

### Fase 4 — routing
Seleccionar WARP únicamente para modelos declarados compatibles.

### Fase 5 — LEONES
Añadir preflight específico de RAM, NVMe, storage throughput y tamaño del modelo, seguido de benchmark MEASURED.

## 13. Veredicto

| Área | Evaluación |
|---|---|
| Backend opcional ODS | 🟢 Alto encaje |
| Sustitución de llama-server | 🔴 No |
| MoE grandes | 🟢 Muy favorable |
| API OpenAI | 🟢 Favorable |
| Dependencia NVMe | 🟡 Crítica |
| Docker/Compose | 🟡 Requiere validación |
| Integración LEONES | 🟢 Alta |
| Benchmark propio | ⏳ Pendiente |

**Clasificación final:** Experimental backend candidate — high integration value, strongly storage- and hardware-constrained.

## Fuentes primarias

- https://github.com/sqliteai/warp
- https://github.com/sqliteai/waste
- https://github.com/Osmantic/ODS
