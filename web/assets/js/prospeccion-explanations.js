/* LEONES · Prospección: explicación funcional en español de los hallazgos */
(() => {
    "use strict";
    if (!/prospeccion\.html$/.test(window.location.pathname)) return;

    const known = {
        "sharksurfauto-byte/ARES-v2": "Framework que se coloca sobre un LLM ya entrenado para construir aplicaciones o flujos basados en ese modelo.",
        "JeremyMaille/rag-aero": "Proyecto de evaluación de RAG sobre documentación normativa aeronáutica; estudia las distintas etapas de recuperación y analiza fallos y regresiones.",
        "Francis1998/nexus-llm-router": "Router de múltiples LLM que selecciona modelos según la tarea y puede aplicar estrategias de coste y controles para uso en producción.",
        "YogendraChukka01/AdaptiveAgent": "Plataforma de RAG agéntico basada en un flujo LangGraph de varios nodos, con varios proveedores de LLM y evaluación mediante otro modelo.",
        "GabrielCpp/stablemate": "Herramienta para ejecutar agentes mediante una máquina de estados Python con checkpoints, de forma que los trabajos puedan recuperarse tras interrupciones.",
        "official-eswaran/DataWhisper": "Asistente local para consultar datos mediante lenguaje natural y convertir las preguntas en SQL, mostrando resultados como tablas y gráficos sin enviar los datos a la nube.",
        "GEMISIS/leviath": "Runtime estructurado para agentes LLM que organiza el contexto y los flujos de varias etapas y los ejecuta como una aplicación única.",
        "vllm-project/vllm": "Motor de inferencia y serving de alto rendimiento para ejecutar y ofrecer modelos de lenguaje, especialmente cuando se necesita eficiencia y concurrencia.",
        "ggml-org/llama.cpp": "Runtime de inferencia en C/C++ para ejecutar modelos de lenguaje localmente, con especial importancia para equipos con recursos limitados.",
        "huggingface/transformers": "Framework que proporciona las definiciones y herramientas para entrenar y ejecutar modelos modernos de texto, visión, audio y multimodales.",
        "NVIDIA/TensorRT-LLM": "Stack de NVIDIA para optimizar y ejecutar LLM de forma eficiente en GPU NVIDIA, incluyendo runtimes Python y C++ para la ejecución.",
        "NVIDIA/Model-Optimizer": "Biblioteca de optimización que reúne técnicas como cuantización, destilación, poda y speculative decoding para preparar modelos para runtimes de inferencia.",
        "vllm-project/semantic-router": "Router programable que decide qué modelo utilizar dentro de un conjunto heterogéneo de modelos de lenguaje.",
        "francium619/llmscope": "Herramienta de instrumentación para observar, trazar y reproducir ejecuciones de inferencia local de modelos Transformer desde el terminal.",
        "cklxx/arle": "Runtime de LLM escrito en Rust que sirve modelos, ejecuta agentes y puede trabajar con procesos de destilación sin Python en la ruta crítica.",
        "Classevelabs/rai": "Motor de inferencia de LLM para CPU escrito en Rust, orientado a modelos cuantizados y ejecución local sin GPU ni runtime Python.",
        "rammsguns/llm-rig": "Conjunto de scripts que detecta automáticamente GPU, VRAM, RAM y núcleos y construye una configuración ajustada de llama.cpp para uso local.",
        "townsendmerino/goinfer": "Runtime local de inferencia escrito en Go que permite ejecutar modelos como Gemma, Qwen o Llama desde un binario único.",
        "ishpatel/llm-bench-lab": "Harness de benchmarking local para medir tiempo hasta el primer token, rendimiento, arranque en frío y memoria ocupada en distintas plataformas.",
        "lablup/mlxcel": "Runtime y servidor de inferencia para LLM y VLM optimizado para Apple Silicon y GPU NVIDIA.",
        "llm-d/llm-d": "Infraestructura para obtener alto rendimiento de inferencia de LLM sobre aceleradores modernos gestionados con Kubernetes.",
        "wisent-ai/brama": "Router de LLM con varios proveedores que automatiza detección, cadenas de fallback y gestión de inferencia local.",
        "OpenHands": "Agente de desarrollo que utiliza modelos de lenguaje y herramientas del entorno para realizar tareas de programación.",
        "langchain-ai/langchain": "Plataforma para construir y desplegar agentes y flujos de aplicaciones basados en modelos de lenguaje.",
        "elizaOS/eliza": "Sistema operativo de código abierto orientado a construir agentes capaces de mantener estado, utilizar herramientas e interactuar con distintos entornos.",
        "vercel/eve": "Framework abierto para construir agentes de IA y organizar sus componentes y flujos de ejecución.",
        "BuilderIO/agent-native": "Framework para construir aplicaciones diseñadas para ser utilizadas y operadas por agentes de IA.",
        "kongusen/deepstrike": "Microkernel para runtimes de agentes que proporciona una base común para ejecutar agentes desarrollados en distintos lenguajes.",
        "lazynet/lazy-harness": "Harness multiplataforma para agentes de programación que organiza perfiles, memoria de trabajo y ciclos de desarrollo con disciplina de pruebas.",
        "eunomia-bpf/bpf-benchmark": "Framework y benchmark para evaluar optimizaciones realizadas por agentes de IA sobre programas eBPF.",
        "nevenincs/vaultspec-core": "Harness basado en especificaciones para estructurar y controlar tareas de agentes de programación.",
        "graemeconradie/agent-lightning": "Framework orientado al entrenamiento y optimización de agentes de IA mediante ciclos de aprendizaje y evaluación.",
        "ctietze/agent-mail": "Conjunto de scripts para permitir que varios agentes LLM se envíen mensajes entre sí mediante buzones Maildir.",
        "psyb0t/aigate": "Plataforma de IA autoalojada que reúne inferencia, herramientas, automatización web, generación multimedia y ejecución de código de agentes detrás de una API compatible con OpenAI.",
        "Fastiraz/akio": "Agente autónomo de IA escrito en Rust que incorpora la inferencia dentro del propio binario.",
        "StillDeadcode/affinity": "Motor de inferencia especializado en ejecutar DeepSeek V4 Flash sobre GPU AMD con arquitectura RDNA4.",
        "goodman-b/affinity": "Motor de inferencia especializado en ejecutar DeepSeek V4 Flash sobre GPU AMD con arquitectura RDNA4.",
        "castle-greybeard/affinity": "Motor de inferencia especializado en ejecutar DeepSeek V4 Flash sobre GPU AMD con arquitectura RDNA4.",
        "Jubiloso/affinity": "Motor de inferencia especializado en ejecutar DeepSeek V4 Flash sobre GPU AMD con arquitectura RDNA4.",
        "aicore/aicore-gemma4-mtp": "Paquete preparado para ejecutar speculative decoding con drafters MTP de Gemma 4, tanto en CPU como en GPU y mediante Python, vLLM o Docker.",
        "grokmeme/petals": "Sistema de inferencia distribuida que permite repartir modelos de lenguaje grandes entre varios equipos, facilitando ejecutar modelos que no caben completos en un solo ordenador.",
        "nalamk/pollen-node": "Aplicación de escritorio para participar como nodo en una red distribuida de inferencia de modelos.",
        "BrikerMan/openinference": "Instrumentación basada en OpenTelemetry para observar y obtener trazas de aplicaciones de IA.",
        "Aelian/AI-Brain": "Base de conocimiento tipo wiki que combina Obsidian y LLM para organizar materiales originales, conocimiento estructurado y notas.",
        "elvizakos/assistant.el": "Integración para utilizar modelos de lenguaje desde Emacs, tanto como ayuda para programar como para conversar.",
        "TheKalu/TPU-Assistant": "Asistente que detecta preguntas sin respuesta en un foro y genera respuestas mediante modelos de IA, incorporando límites y mecanismos de control.",
        "bossm0n5t3r/acw": "CLI que genera mensajes de commit a partir de los cambios de Git usando modelos de lenguaje locales o servicios externos.",
        "2na3k/aeri-chan": "Interfaz única para acceder a un gateway de modelos de lenguaje desde una aplicación común.",
        "digital-codes/agent": "Framework para construir agentes intentando reducir el número de llamadas necesarias al modelo de lenguaje.",
        "Embeded-Focus/ai-inference-lab": "Proyecto de experimentación relacionado con inferencia de modelos de IA; la prospección no aporta todavía suficiente detalle funcional para una descripción más precisa.",
        "aice-lab/devlog": "Generador de registros de desarrollo que transforma el historial Git en diarios legibles y puede usar LLM locales o servicios externos para resumirlo.",
        "EdgarOrtegaRamirez/llm-budget-manager": "Herramienta para controlar y gestionar presupuestos de aplicaciones que utilizan modelos de lenguaje.",
        "babysea/adaptive-island": "Motor que selecciona proveedores de inferencia priorizando la reutilización de caché en cargas con varios proveedores.",
        "luziyao1995/vllm-deletion_scheduled-82779494": "Copia de vLLM orientada a inferencia y serving eficiente de modelos de lenguaje; aparece en prospección como una entrada separada y debe verificarse antes de tratarla como proyecto independiente.",
        "dapa/oc-mlops-projet-3": "Aplicación que combina un LLM, RAG y un agente SQL para consultar y trabajar con información estructurada mediante un modelo de lenguaje.",
        "dapa/oc-mlops-projet-3-docker": "Despliegue mediante Docker de una aplicación que combina LLM, RAG y un agente SQL y que utiliza la API de Mistral.",
        "Isilin/lm-webui": "Interfaz web para interactuar con LLM que incorpora reconocimiento y síntesis de voz.",
        "sanchemba/lobe-chat": "Interfaz de chat autoalojable para trabajar con distintos proveedores de modelos, modalidades y plugins desde una única aplicación.",
        "LaughingBubba/zeeflow-claw": "Gateway compatible con OpenAI que conecta PicoClaw con inferencia local proporcionada por Lemonade.",
        "cip-playground/cip-llm-gateway": "Configuración Terraform para desplegar una máquina GPU destinada a ejecutar inferencia con llama.cpp u otros motores similares.",
        "a3ilab-llm-uncertainty/gemma4_12B_zhtw_6144_lr1e-6_ep5_64_128_256_v6_methodA2_1_2_llamafactory_oringal_train": "Modelo derivado de Gemma 4 entrenado mediante LLaMA-Factory; la prospección no aporta todavía información suficiente para determinar con precisión su finalidad concreta.",
    };

    function generic(item) {
        const d = String(item.description || "").toLowerCase();
        if (!d) return "La fuente ha descubierto esta pieza, pero todavía no proporciona una descripción funcional suficiente. Requiere revisión antes de incorporarla como conocimiento consolidado.";
        const c = String(item.category || item.type || "software").toLowerCase();
        let base = c.includes("model") ? "Modelo de IA descubierto" : c.includes("paper") ? "Trabajo de investigación descubierto" : "Proyecto de software descubierto";
        const hints = [
            [/inference|serving|runtime/, "orientado a ejecutar o servir modelos de IA"],
            [/agent|autonomous/, "orientado a construir o ejecutar agentes de IA"],
            [/benchmark|evaluation|eval/, "orientado a evaluar, comparar o medir sistemas de IA"],
            [/rag|retrieval|knowledge/, "orientado a recuperación de información y uso de conocimiento con modelos de lenguaje"],
            [/router|routing|gateway/, "orientado a enrutar peticiones entre modelos o proveedores"],
            [/coding|code|software engineering/, "orientado a programación y tareas de ingeniería de software"],
            [/training|fine.?tun|distill/, "orientado al entrenamiento, adaptación u optimización de modelos"],
            [/observability|tracing|instrument/, "orientado a observar, instrumentar o trazar sistemas de IA"],
            [/memory|context/, "orientado a gestionar memoria o contexto de agentes y modelos"],
            [/quantiz/, "orientado a reducir el coste de memoria o cómputo mediante cuantización"],
            [/voice|speech|audio/, "orientado al procesamiento de voz o audio mediante IA"],
            [/image|video|vision/, "orientado al procesamiento o generación de imágenes y vídeo mediante IA"],
        ];
        const hit = hints.find(([re]) => re.test(d));
        return hit ? `${base} ${hit[1]}.` : `${base} cuya finalidad concreta debe confirmarse en la fuente original antes de promoverlo en LEONES.`;
    }

    function apply() {
        const table = document.querySelector(".data-table");
        if (!table) return;
        const head = table.tHead?.rows[0];
        if (!head || [...head.cells].some((c) => c.dataset.esFunctionality === "1")) return;
        const descIndex = [...head.cells].findIndex((c) => c.textContent.trim() === "Descripción");
        if (descIndex < 0) return;
        const th = document.createElement("th");
        th.dataset.esFunctionality = "1";
        th.textContent = "Qué es / para qué sirve (ES)";
        head.insertBefore(th, head.cells[descIndex]);
        [...table.tBodies[0].rows].forEach((row) => {
            const link = row.querySelector("td:nth-child(3) a");
            const name = link?.textContent.trim() || "";
            const original = row.cells[descIndex + 1]?.textContent.trim() || "";
            const sourceItem = { name, repository: name, description: original, category: row.cells[1]?.textContent || "software" };
            const td = document.createElement("td");
            td.className = "desc functionality-es";
            td.innerHTML = `<strong>${escapeHtml(known[name] || generic(sourceItem))}</strong><details><summary>Descripción original de la fuente</summary><span>${escapeHtml(original || "No disponible")}</span></details>`;
            row.insertBefore(td, row.cells[descIndex]);
        });
    }
    function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (m) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m])); }
    const style = document.createElement("style");
    style.textContent = ".functionality-es{min-width:330px;max-width:480px}.functionality-es strong{display:block;color:#173f66;line-height:1.45}.functionality-es details{margin-top:7px;font-size:.78rem;color:#637482}.functionality-es summary{cursor:pointer;font-weight:700}.functionality-es details span{display:block;margin-top:5px}.data-table{min-width:1250px}";
    document.head.appendChild(style);
    const observer = new MutationObserver(apply);
    observer.observe(document.getElementById("findings") || document.body, { childList: true, subtree: true });
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply); else apply();
})();
