# Odysseus

## Identidad

**Proyecto:** Odysseus

**Repositorio:** https://github.com/odysseus-dev/odysseus

**Sitio:** https://odysseus-dev.github.io/odysseus/

**Licencia:** AGPL-3.0-or-later.

## Qué es

Odysseus es un **workspace de IA self-hosted** que reúne en una sola aplicación chat, agentes, herramientas, MCP, archivos, shell, memoria, investigación, documentos, correo, notas, tareas, calendario y flujos de modelos locales.

No es principalmente un runtime de inferencia. Su papel está por encima de la capa de ejecución: proporciona una interfaz y un entorno operativo para trabajar con modelos y servicios LLM locales o remotos.

## Por qué entra en el conocimiento de LEONES

Odysseus es relevante porque muestra otra capa que el recomendador de LEONES debe distinguir de los runtimes: **la experiencia de uso y el workload agentivo**.

El proyecto incorpora un Cookbook con recomendaciones de modelos conscientes del hardware, descarga y serving de modelos, y declara un catálogo de más de 270 modelos. También integra agentes, herramientas y MCP, por lo que puede servir como referencia para estudiar cómo un runtime recomendado termina formando parte de un stack de usuario real.

La fuente oficial describe explícitamente el objetivo de ser local-first, privacy-first y sin telemetría, aunque esas propiedades deben comprobarse siempre en la configuración concreta de despliegue.

## Funcionalidades relevantes

### Chat y agentes

Permite conversaciones multi-turn y agentes autónomos capaces de planificar, llamar herramientas y ejecutar tareas.

### Tools y MCP

Integra herramientas locales para bash, archivos, web y memoria, además de servidores MCP conectables.

### Cookbook hardware-aware

Incluye recomendaciones de modelos, descargas y serving orientados al hardware. Para LEONES esto es interesante como **referencia de capa de recomendación/aplicación**, no como autoridad para sustituir LLMFit o los benchmarks propios.

### Investigación profunda

Incluye workflows de investigación web multi-paso, lectura de fuentes y generación de informes. Esto conecta directamente con la dimensión de workload que LEONES necesita describir antes de comparar runtimes.

### Documentos, correo y productividad

La aplicación integra editor documental, operaciones de correo IMAP/SMTP, notas, tareas y calendario. Estas funciones convierten al modelo en parte de un sistema completo y permiten estudiar cargas de trabajo reales en lugar de medir solamente generación de texto.

## Arquitectura conceptual para LEONES

Odysseus debe situarse **por encima** del runtime:

```text
modelo / pesos
      ↓
runtime de inferencia
      ↓
API / endpoint local
      ↓
Odysseus
      ↓
chat · agents · tools · MCP · research · documents · memory
      ↓
workload real
      ↓
evaluación LEONES
```

Esto permite separar tres preguntas:

1. **¿Qué modelo conviene?** → Atlas / selector.
2. **¿Con qué runtime debe ejecutarse?** → `runtime-selection.v1`.
3. **¿Cómo se convierte en una herramienta útil para el usuario?** → harness/workspace como Odysseus.

## Relación con FreeToken

Odysseus y FreeToken no compiten en la misma capa.

- **FreeToken:** motor de serving edge-native especializado en MoE.
- **Odysseus:** workspace de usuario y agentes que puede consumir endpoints de modelos locales.

Por tanto, LEONES puede estudiar una combinación del tipo:

```text
LEONES selector
    ↓
FreeToken
    ↓
OpenAI/Anthropic-compatible endpoint
    ↓
Odysseus
    ↓
agent workload
    ↓
LEONES benchmark + grader
```

Esta combinación es especialmente interesante para comprobar si las ventajas de un runtime especializado sobreviven cuando el modelo se utiliza en una carga agentiva real.

## Evidencia primaria revisada

El repositorio oficial declara chat + agents, tools/MCP, Cookbook, Deep Research, documentos, correo, notas/tareas/calendario y otros componentes. También publica instrucciones de despliegue mediante Docker Compose y advierte de mantener la autenticación activada y no exponer directamente los puertos de servicios de modelos.

El archivo `.env.example` muestra además que Odysseus puede trabajar con hosts LLM locales y endpoints adicionales, incluyendo Ollama, LM Studio y endpoints compatibles con OpenAI.

## Qué puede aprender LEONES de Odysseus

### 1. El workload importa

Medir únicamente tokens/s no representa una aplicación agentiva completa. Odysseus proporciona ejemplos de workloads con herramientas, memoria, investigación y edición de documentos.

### 2. El endpoint es una frontera útil

LEONES puede mantener el runtime debajo de una interfaz estándar y evaluar diferentes motores con el mismo workload superior.

### 3. La recomendación debe ser de stack

Una recomendación útil puede ser:

`modelo + cuantización + runtime + configuración + interfaz/harness + workload`

no solamente `modelo`.

### 4. MCP y tools deben formar parte del benchmark

Cuando el usuario utiliza herramientas, la latencia del modelo no es la única variable. También importan llamadas a herramientas, recuperación, errores, reintentos y finalización correcta de la tarea.

## Papel en la web de conocimiento

**Clasificación:** `workspace-reference`

**Capa:** aplicación / harness / workspace agentivo.

**No es:** benchmark LEONES ni runtime canónico.

**Valor:** referencia arquitectónica para conectar inferencia local con workloads reales.

**Prioridad:** alta como fuente de inspiración y comparación de experiencia agentiva.

## Siguiente integración prevista

Odysseus debe permanecer inicialmente en la **fuente de conocimiento y descubrimiento**, sin convertir sus recomendaciones de modelos en verdad del selector.

Cuando el pipeline agentivo de LEONES esté preparado, puede incorporarse como uno de los harness/workspaces de prueba para evaluar:

- tool calling;
- multi-turn;
- memoria;
- investigación;
- edición de documentos;
- recuperación ante errores;
- latencia extremo a extremo;
- coste de tokens;
- estabilidad del runtime;
- calidad final de la tarea.

## Conclusión

Odysseus aporta a LEONES una pieza que faltaba separar con claridad: **la capa de aplicación agentiva que consume el runtime**. Su principal utilidad no es decir qué modelo o runtime es mejor, sino proporcionar un entorno realista para comprobar si una combinación recomendada por LEONES funciona cuando deja de ser una demo de generación y se convierte en una herramienta de trabajo.
