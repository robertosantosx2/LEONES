# Procedimiento de descubrimiento de nuevas fuentes para LEONES

## 1. Objetivo

Descubrir de forma continua **nuevas fuentes de proyectos, modelos, runtimes, agentes, skills, harnesses, hardware, datasets y papers de IA** que todavía no estén en `sources_registry.json`.

El procedimiento es de **descubrimiento**, no de activación. Encontrar una web, una cuenta de X o un repositorio no implica convertirlo automáticamente en fuente oficial.

La regla es:

```text
DESCUBRIR → NORMALIZAR → DEDUPLICAR → OBTENER EVIDENCIA → PROPONER → VALIDAR → INCORPORAR
```

## 2. Fuentes que se consultan

### Prioridad crítica / diaria

- X.com: anuncios, desarrolladores, laboratorios, lanzamientos y enlaces hacia la fuente primaria.
- GitHub: Trending, Search, releases y repositorios nuevos.
- Hugging Face: models, datasets, Spaces y Papers.
- Reddit r/LocalLLaMA: modelos locales, runtimes, cuantización, proyectos y lanzamientos.
- arXiv: investigación reciente que pueda conducir a modelos, código o datasets.

### Prioridad alta / semanal

- Hacker News.
- Reddit r/MachineLearning.
- OpenReview.
- Papers With Code y directorios de benchmarks.
- Blogs de laboratorios y desarrolladores.
- Awesome lists y directorios comunitarios.

### Prioridad media / exploratoria

- Lobsters.
- Newsletters de IA.
- Comunidades Discord/Slack cuando exista acceso público o feed/exportación legítima.
- Directorios y forjas alternativas que aparezcan durante la prospección.

El registro operativo está en `new_source_discovery_registry.json`.

## 3. X.com no es la fuente primaria

X es especialmente útil para **descubrir** proyectos porque los lanzamientos aparecen a menudo antes de que sean visibles en directorios agregados. Sin embargo, X no debe utilizarse como evidencia suficiente de licencia, autoría o existencia del proyecto.

Para cada candidato descubierto en X se debe intentar localizar:

1. repositorio oficial;
2. modelo oficial en Hugging Face u otro hub;
3. página oficial del proyecto;
4. paper o preprint;
5. documentación;
6. licencia o términos de uso.

Si solo existe el post de X, el candidato queda en `needs_evidence`.

## 4. Consultas iniciales

Las consultas se mantienen deliberadamente amplias y se combinan con vocabulario de descubrimiento:

```text
"open source" LLM
"open weights" model
new LLM release
new local AI project
new inference engine
new coding agent
new AI agent framework
MCP server new
LLM runtime
LLM quantization
CPU inference
consumer hardware AI
small language model
vision language model
speech model open source
multimodal open weights
agent skills
agent harness
AI benchmark open source
```

En X y buscadores se añaden filtros de dominio cuando proceda:

```text
site:x.com
site:github.com
site:huggingface.co
site:reddit.com/r/LocalLLaMA
site:news.ycombinator.com
```

## 5. Qué se considera una nueva fuente

Una **fuente** es un lugar estable desde el que LEONES puede descubrir elementos nuevos de forma reproducible.

Ejemplos:

- una nueva forja;
- una instancia pública de Forgejo/Gitea;
- un hub de modelos;
- un catálogo de datasets;
- una API de papers;
- un directorio de agentes;
- una comunidad con feed público estable;
- un índice especializado de proyectos IA.

Un repositorio individual descubierto no es automáticamente una nueva fuente: normalmente es un **descubrimiento procedente de una fuente existente**.

## 6. Pipeline automático

```text
┌───────────────────────────────┐
│ X / GitHub / HF / Reddit / HN │
│ arXiv / OpenReview / blogs... │
└───────────────┬───────────────┘
                ↓
       candidatos brutos
                ↓
       normalización URL
                ↓
          deduplicación
                ↓
       resolver fuente primaria
                ↓
       comprobar accesibilidad
                ↓
       comprobar mecanismo
       público de búsqueda
                ↓
      comprobar reproducibilidad
                ↓
        puntuar candidato
                ↓
      ┌─────────┴─────────┐
      ↓                   ↓
  descartado          needs_review
                          ↓
                    validación
                          ↓
                 sources_registry
```

## 7. Evidencia mínima antes de incorporar

Una fuente candidata debe proporcionar, como mínimo:

- URL estable;
- identidad inequívoca del servicio/instancia;
- mecanismo reproducible de consulta o extracción;
- respuesta observable;
- procedencia conservada;
- método de deduplicación;
- comportamiento ante errores;
- indicación de si requiere autenticación.

La licencia de los proyectos descubiertos se valida después mediante el **License Gate**. No se debe confundir "fuente válida" con "proyecto publicable".

## 8. Puntuación

El candidato obtiene puntos por:

| Evidencia | Puntos |
|---|---:|
| Enlace a fuente primaria | +4 |
| Repositorio/hub oficial | +3 |
| Actividad reciente | +2 |
| Menciones independientes | +2 |
| Identidad clara | +2 |
| Licencia/términos visibles | +2 |
| Duplicado | -5 |

- **6 puntos:** pasa a revisión.
- **10 puntos:** revisión prioritaria.
- Menos de 6: permanece como candidato sin incorporar.

## 9. Frecuencia

El descubrimiento se divide en dos ciclos:

### Descubrimiento diario ligero

X, GitHub, Hugging Face, r/LocalLLaMA, Hacker News y arXiv.

Objetivo: detectar novedades recientes y evitar que un lanzamiento importante espere una semana.

### Descubrimiento semanal profundo

Reddit r/MachineLearning, OpenReview, Papers With Code, blogs, newsletters, Awesome lists, Lobsters y nuevas instancias/forjas.

Objetivo: descubrir fuentes nuevas, no solo proyectos nuevos.

## 10. No bloquear la prospección

El descubrimiento de fuentes debe ser completamente independiente del pipeline principal.

Una fuente externa que falle:

```text
TIMEOUT / 401 / 403 / 404 / API caída
```

se registra como incidente y **no bloquea las demás**.

Cada fuente tiene:

- timeout propio;
- límite de resultados;
- número máximo de consultas;
- estado (`candidate`, `active`, `degraded`, `unavailable`, `review`);
- última ejecución;
- último resultado correcto.

## 11. Incorporación automática controlada

El descubrimiento puede crear una propuesta en:

`data/prospection/new_source_candidates.ndjson`

pero **no debe modificar automáticamente** `sources_registry.json` cuando la evidencia sea insuficiente.

Cuando el candidato alcanza el umbral de revisión, el sistema puede preparar un patch para incorporar:

- `id`;
- nombre;
- URL;
- tipo;
- adaptador;
- prioridad;
- cadencia;
- timeout;
- requisitos de autenticación.

La activación definitiva sigue separada del descubrimiento.

## 12. Métricas

El informe semanal debe incluir:

- candidatos encontrados;
- candidatos nuevos;
- duplicados;
- candidatos descartados;
- candidatos con evidencia suficiente;
- nuevas fuentes propuestas;
- nuevas fuentes activadas;
- fuentes que dejaron de responder;
- fuentes que requieren token;
- descubrimientos generados por cada canal;
- tiempo empleado por canal;
- tasa de falsos positivos.

## 13. Principio rector

El objetivo no es tener muchas fuentes. El objetivo es tener una **red creciente, reproducible y auditable de fuentes de descubrimiento**.

Por eso LEONES debe preferir:

> **una fuente estable y consultable que aporta descubrimientos nuevos**
>
> frente a
>
> **diez webs que solamente parecen relacionadas con IA.**

## 14. Aplicación al sistema actual

Este procedimiento complementa la extracción semanal ya creada. La extracción semanal procesa las fuentes conocidas; este procedimiento busca **las fuentes que todavía no conocemos**.

El ciclo completo queda:

```text
FUENTES CONOCIDAS
      ↓
EXTRACCIÓN SEMANAL
      ↓
DESCUBRIMIENTOS
      ↓
──────────────────────────────
DESCUBRIMIENTO DE NUEVAS FUENTES
X / GitHub / HF / Reddit / HN /
arXiv / OpenReview / blogs...
      ↓
CANDIDATOS DE FUENTE
      ↓
VALIDACIÓN
      ↓
REGISTRO DE FUENTES
      ↓
SIGUIENTE CICLO
```

De esta forma el ecosistema de prospección de LEONES puede crecer continuamente sin que cada incorporación requiera rediseñar el workflow.
