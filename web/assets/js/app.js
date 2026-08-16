/*
 * LEONES application UI.
 *
 * This file owns interaction only. Presentation stays in site.css and
 * the page remains usable as ordinary HTML when JavaScript is unavailable.
 */

const goals = {
    hardware: {
        title: "Saber qué puede hacer mi PC",
        text: "Empieza por identificar hardware, memoria y aceleración disponible.",
        command: "python3 scripts/leones-hardware.py",
    },
    model: {
        title: "Probar un modelo",
        text: "Identifica el modelo, ejecuta una inferencia y conserva el resultado.",
        command: "python3 scripts/leones-model.py && python3 scripts/leones-infer.py",
    },
    agent: {
        title: "Evaluar un agente",
        text: "Ejecuta la evaluación agentiva después de fijar runtime y modelo.",
        command: "python3 scripts/leones-evaluacion.py",
    },
    recommend: {
        title: "Obtener una recomendación",
        text: "Describe tarea y hardware para construir una ruta provisional.",
        command: "python3 scripts/leones-router.py --help",
    },
    research: {
        title: "Investigar cambios",
        text: "La prospección descubre cambios; la revisión decide qué entra en Atlas.",
        command: "python3 scripts/prospection/run_daily_prospection.py --help",
    },
    share: {
        title: "Formar parte de la Manada",
        text: "Mide primero, revisa privacidad y comparte solo lo que decidas publicar.",
        command: "python3 scripts/leones-privacy.py --help",
    },
};

const state = {
    selectedGoal: null,
};

function byId(id) {
    return document.getElementById(id);
}

function selectGoal(goal) {
    const data = goals[goal];
    if (!data) return;

    state.selectedGoal = goal;
    document.querySelectorAll("[data-goal]").forEach((button) => {
        button.classList.toggle("is-selected", button.dataset.goal === goal);
    });

    byId("next-title").textContent = data.title;
    byId("next-text").textContent = data.text;
    byId("command").textContent = data.command;
    byId("progress").style.width = "50%";
    byId("copy").disabled = false;
    byId("done").disabled = false;
    byId("message").textContent = "";
}

async function copyCommand() {
    if (!state.selectedGoal) return;

    const command = goals[state.selectedGoal].command;
    try {
        await navigator.clipboard.writeText(command);
        byId("message").textContent = "Comando copiado.";
    } catch {
        byId("message").textContent = "No se pudo copiar automáticamente. Selecciónalo y cópialo manualmente.";
    }
}

function markDone() {
    if (!state.selectedGoal) return;
    byId("progress").style.width = "100%";
    byId("message").textContent = "Paso marcado como terminado. Continúa con la siguiente medición cuando estés preparado.";
}

function calculateRoute() {
    const task = byId("task").value;
    const ram = Number(byId("ram").value) || 0;
    const vram = Number(byId("vram").value) || 0;
    const runtime = byId("backend").value;

    let recommendation = "Ruta de exploración";
    if (vram >= 8) recommendation = "Prioriza candidatos con aceleración GPU y valida memoria real.";
    else if (ram >= 32) recommendation = "Prioriza modelos cuantizados de tamaño medio y valida latencia.";
    else recommendation = "Prioriza modelos pequeños/cuántizados y ejecución CPU conservadora.";

    byId("route-result").innerHTML = `
        <strong>Ruta provisional</strong>
        <p>${task} → ${ram} GB RAM → ${vram} GB VRAM → ${runtime}</p>
        <p>${recommendation}</p>
        <small>Esto es una orientación inicial, no un benchmark ni una garantía de rendimiento.</small>
    `;
}

function init() {
    document.querySelectorAll("[data-goal]").forEach((button) => {
        button.addEventListener("click", () => selectGoal(button.dataset.goal));
    });

    byId("copy").addEventListener("click", copyCommand);
    byId("done").addEventListener("click", markDone);
    byId("route").addEventListener("click", calculateRoute);
}

document.addEventListener("DOMContentLoaded", init);
