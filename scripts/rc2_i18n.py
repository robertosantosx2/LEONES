#!/usr/bin/env python3
"""RC2 presentation catalog: Español / English / 中文."""
from __future__ import annotations

LANGUAGES = ("es", "en", "zh")
LANGUAGE_LABELS = {
    "es": "Español",
    "en": "English",
    "zh": "中文",
}

_active_language = "es"

TEXT = {
    "choose_language": {
        "es": "ELIGE EL IDIOMA DE LA INTERFAZ",
        "en": "CHOOSE THE INTERFACE LANGUAGE",
        "zh": "选择界面语言",
    },
    "banner_subtitle": {"es": "BETA · RC2", "en": "BETA · RC2", "zh": "测试版 · RC2"},
    "your_team": {
        "es": "Tu equipo. Tus decisiones. Evidencia real.",
        "en": "Your hardware. Your decisions. Real evidence.",
        "zh": "你的硬件。你的选择。真实证据。",
    },
    "choose_model": {
        "es": "ELIGE TU MODELO",
        "en": "CHOOSE YOUR MODEL",
        "zh": "选择你的模型",
    },
    "choose_stack": {
        "es": "ELIGE TU STACK",
        "en": "CHOOSE YOUR STACK",
        "zh": "选择你的运行栈",
    },
    "install_consent": {
        "es": "¿AUTORIZAR LA INSTALACIÓN?",
        "en": "AUTHORIZE INSTALLATION?",
        "zh": "是否授权安装？",
    },
    "benchmark_consent": {
        "es": "¿QUIERES EJECUTAR EL BENCHMARK A01?",
        "en": "DO YOU WANT TO RUN THE A01 BENCHMARK?",
        "zh": "是否运行 A01 基准测试？",
    },
    "yes": {"es": "Sí", "en": "Yes", "zh": "是"},
    "no": {"es": "No", "en": "No", "zh": "否"},
    "authorize": {"es": "Autorizar", "en": "Authorize", "zh": "授权"},
    "cancel": {"es": "Cancelar", "en": "Cancel", "zh": "取消"},
    "back": {"es": "Volver", "en": "Back", "zh": "返回"},
    "ready": {"es": "Preparado", "en": "Ready", "zh": "已准备"},
    "blocked": {"es": "Bloqueado", "en": "Blocked", "zh": "已阻止"},
    "measured": {"es": "Medido", "en": "Measured", "zh": "已测量"},
    "invalid_option": {
        "es": "Opción no válida",
        "en": "Invalid option",
        "zh": "无效选项",
    },
    "detecting_hardware": {
        "es": "Detectando hardware y candidatos mediante LLMFit...",
        "en": "Detecting hardware and candidates through LLMFit...",
        "zh": "正在通过 LLMFit 检测硬件和候选模型……",
    },
    "llmfit_unavailable": {
        "es": "LLMFit no disponible o inválido",
        "en": "LLMFit unavailable or invalid",
        "zh": "LLMFit 不可用或无效",
    },
    "hardware_ready": {
        "es": "Hardware real",
        "en": "Live hardware",
        "zh": "实时硬件",
    },
    "estimated_notice": {
        "es": "Las cifras de LLMFit son ESTIMACIONES. No son evidencia de ejecución real.",
        "en": "LLMFit values are ESTIMATES. They are not real execution evidence.",
        "zh": "LLMFit 数值是估算值，不是真实执行证据。",
    },
    "no_model_candidates": {
        "es": "No hay candidatos reales",
        "en": "No live candidates",
        "zh": "无实时候选模型",
    },
    "selected": {"es": "seleccionado", "en": "selected", "zh": "已选择"},
    "installation_authorized": {
        "es": "Consentimiento de instalación concedido.",
        "en": "Installation consent granted.",
        "zh": "已授予安装授权。",
    },
    "not_installed_yet": {
        "es": "Aún NO se ha instalado nada en tu equipo.",
        "en": "Nothing has been installed on your machine yet.",
        "zh": "尚未在你的设备上安装任何内容。",
    },
    "what_was_decided": {
        "es": "RESUMEN DE DECISIONES",
        "en": "DECISION SUMMARY",
        "zh": "决策摘要",
    },
    "label_model": {"es": "Modelo", "en": "Model", "zh": "模型"},
    "label_stack": {"es": "Stack", "en": "Stack", "zh": "运行栈"},
    "label_status": {"es": "Estado", "en": "Status", "zh": "状态"},
    "status_authorized_not_installed": {
        "es": "autorizado · instalación física pendiente",
        "en": "authorized · physical install pending",
        "zh": "已授权 · 实际安装待完成",
    },
    "next_step_title": {
        "es": "SIGUIENTE PASO",
        "en": "NEXT STEP",
        "zh": "下一步",
    },
    "next_step_ods": {
        "es": "Instalar ODS con el instalador canónico de LEONES:",
        "en": "Install ODS with the canonical LEONES installer:",
        "zh": "使用 LEONES 标准安装程序安装 ODS：",
    },
    "next_step_magnitude": {
        "es": "Instalar Magnitude con el instalador canónico de LEONES:",
        "en": "Install Magnitude with the canonical LEONES installer:",
        "zh": "使用 LEONES 标准安装程序安装 Magnitude：",
    },
    "next_step_after_install": {
        "es": "Cuando termine la instalación, verifica el stack. Solo entonces podrás autorizar un benchmark. Instalar ≠ medir.",
        "en": "When installation finishes, verify the stack. Only then can you authorize a benchmark. Install ≠ measure.",
        "zh": "安装完成后请验证运行栈。只有在那之后才能授权基准测试。安装 ≠ 测量。",
    },
    "offer_run_installer": {
        "es": "¿Ejecutar ahora el instalador canónico del stack elegido?",
        "en": "Run the canonical installer for the chosen stack now?",
        "zh": "现在运行所选运行栈的标准安装程序吗？",
    },
    "run_installer_yes": {
        "es": "Sí, ejecutar el instalador ahora",
        "en": "Yes, run the installer now",
        "zh": "是，现在运行安装程序",
    },
    "run_installer_no": {
        "es": "No, lo haré yo más tarde",
        "en": "No, I will do it later",
        "zh": "否，我稍后再做",
    },
    "installer_launching": {
        "es": "Lanzando instalador canónico...",
        "en": "Launching canonical installer...",
        "zh": "正在启动标准安装程序……",
    },
    "installer_finished_ok": {
        "es": "El instalador terminó. Eso no es verificación LEONES; ahora comprobamos el host.",
        "en": "Installer finished. That is not LEONES verification; now we check the host.",
        "zh": "安装程序已结束。这不是 LEONES 验证；现在检查主机。",
    },
    "installer_finished_fail": {
        "es": "El instalador falló o se canceló. Conserva el mensaje original; no se ha marcado como verificado.",
        "en": "Installer failed or was cancelled. Keep the original message; nothing was marked verified.",
        "zh": "安装程序失败或已取消。请保留原始信息；未标记为已验证。",
    },
    "installer_deferred": {
        "es": "Instalador no ejecutado. Aun así puedes verificar si el stack ya está en el equipo.",
        "en": "Installer not run. You can still verify if the stack is already on the host.",
        "zh": "未运行安装程序。如果运行栈已在主机上，仍可验证。",
    },
    "verify_title": {
        "es": "VERIFICACIÓN FÍSICA",
        "en": "PHYSICAL VERIFICATION",
        "zh": "物理验证",
    },
    "verify_running": {
        "es": "Comprobando en este equipo si el stack está realmente instalado...",
        "en": "Checking this host for a real stack installation...",
        "zh": "正在检查此主机是否真正安装了运行栈……",
    },
    "verify_pass": {
        "es": "Verificación física: PASS. El stack se observó en este equipo.",
        "en": "Physical verification: PASS. The stack was observed on this host.",
        "zh": "物理验证：通过。已在此主机上观察到运行栈。",
    },
    "verify_fail": {
        "es": "Verificación física: FAIL. El stack no está verificado en este equipo.",
        "en": "Physical verification: FAIL. The stack is not verified on this host.",
        "zh": "物理验证：失败。此主机上的运行栈未通过验证。",
    },
    "verify_missing": {
        "es": "Faltan o fallan estas comprobaciones:",
        "en": "These checks are missing or failed:",
        "zh": "缺少或失败的检查：",
    },
    "verify_observed": {
        "es": "Observado:",
        "en": "Observed:",
        "zh": "观察到：",
    },
    "verify_next_fail": {
        "es": "Instala o repara el stack y vuelve a verificar. Sin PASS no hay benchmark.",
        "en": "Install or repair the stack and verify again. No PASS means no benchmark.",
        "zh": "请安装或修复运行栈后再次验证。未通过则不能进行基准测试。",
    },
    "verify_next_pass": {
        "es": "Stack verificado. Siguiente puerta: consentimiento de benchmark A01.",
        "en": "Stack verified. Next gate: A01 benchmark consent.",
        "zh": "运行栈已验证。下一关：A01 基准测试授权。",
    },
    "offer_verify_again": {
        "es": "¿Reintentar la verificación física?",
        "en": "Retry physical verification?",
        "zh": "是否重试物理验证？",
    },
    "verify_again_yes": {
        "es": "Sí, verificar de nuevo",
        "en": "Yes, verify again",
        "zh": "是，再次验证",
    },
    "verify_again_no": {
        "es": "No, salir sin verificar",
        "en": "No, exit without verification",
        "zh": "否，在未验证的情况下退出",
    },
    "a01_title": {
        "es": "BENCHMARK A01 (LEONES-Agentic)",
        "en": "A01 BENCHMARK (LEONES-Agentic)",
        "zh": "A01 基准测试（LEONES-Agentic）",
    },
    "a01_what": {
        "es": "Tarea agentic local: el modelo debe emitir exactamente dos tool calls (lookup_model → write_report).",
        "en": "Local agentic task: the model must emit exactly two tool calls (lookup_model → write_report).",
        "zh": "本地代理任务：模型必须恰好发出两次工具调用（lookup_model → write_report）。",
    },
    "a01_metrics": {
        "es": "Se medirá: wall_seconds, measured_tps y grader_pass. ESTIMATED de LLMFit no cuenta como medición.",
        "en": "Measured: wall_seconds, measured_tps and grader_pass. LLMFit ESTIMATED values are not measurements.",
        "zh": "将测量：wall_seconds、measured_tps 和 grader_pass。LLMFit 估算值不算测量。",
    },
    "a01_runtime": {
        "es": "Runner RC1 canónico vía Ollama local cuando esté disponible (scripts/ollama_a01_runtime.py).",
        "en": "Canonical RC1 runner via local Ollama when available (scripts/ollama_a01_runtime.py).",
        "zh": "在可用时通过本地 Ollama 使用标准 RC1 运行器（scripts/ollama_a01_runtime.py）。",
    },
    "a01_privacy": {
        "es": "La evidencia se guarda en el host. Cancelar no invalida la instalación.",
        "en": "Evidence stays on the host. Declining does not invalidate the installation.",
        "zh": "证据保存在主机上。拒绝不会使安装失效。",
    },
    "benchmark_run_yes": {
        "es": "Sí, ejecutar A01 ahora",
        "en": "Yes, run A01 now",
        "zh": "是，现在运行 A01",
    },
    "benchmark_run_no": {
        "es": "No, no medir ahora",
        "en": "No, do not measure now",
        "zh": "否，现在不测量",
    },
    "benchmark_declined": {
        "es": "Benchmark declinado. Instalación intacta; no se ha medido nada.",
        "en": "Benchmark declined. Installation intact; nothing was measured.",
        "zh": "已拒绝基准测试。安装保持不变；未进行任何测量。",
    },
    "benchmark_authorized": {
        "es": "Benchmark autorizado. Handoff RC1 activo.",
        "en": "Benchmark authorized. RC1 handoff active.",
        "zh": "已授权基准测试。RC1 交接已激活。",
    },
    "benchmark_running": {
        "es": "Ejecutando A01 (runner RC1)...",
        "en": "Running A01 (RC1 runner)...",
        "zh": "正在运行 A01（RC1 运行器）……",
    },
    "benchmark_need_ollama": {
        "es": "No se puede ejecutar A01: hace falta Ollama local en PATH y un modelo disponible.",
        "en": "Cannot run A01: local Ollama on PATH and an available model are required.",
        "zh": "无法运行 A01：需要 PATH 中的本地 Ollama 和可用模型。",
    },
    "benchmark_failed": {
        "es": "A01 falló o no produjo medición válida. No se publica como MEASURED.",
        "en": "A01 failed or did not produce a valid measurement. Not published as MEASURED.",
        "zh": "A01 失败或未产生有效测量。不会发布为 MEASURED。",
    },
    "benchmark_completed": {
        "es": "A01 completado. Evidencia guardada en el host.",
        "en": "A01 completed. Evidence saved on the host.",
        "zh": "A01 已完成。证据已保存在主机上。",
    },
    "ods_title": {
        "es": "STACK LOCAL ODS",
        "en": "ODS LOCAL STACK",
        "zh": "ODS 本地运行栈",
    },
    "ods_summary": {
        "es": "ODS — stack local de inferencia (modelos, UI y servicios en tu máquina)",
        "en": "ODS — local inference stack (models, UI and services on your machine)",
        "zh": "ODS — 本地推理栈（在你的机器上运行模型、界面和服务）",
    },
    "ods_capability_1": {
        "es": "Stack local de inferencia",
        "en": "Local inference stack",
        "zh": "本地推理栈",
    },
    "ods_capability_2": {
        "es": "Preparación y validación del plan",
        "en": "Execution-plan preparation and validation",
        "zh": "执行计划准备与验证",
    },
    "ods_capability_3": {
        "es": "Integración con ejecución local",
        "en": "Local execution integration",
        "zh": "本地执行集成",
    },
    "ods_capability_4": {
        "es": "Medición/evidencia mediante pipeline común cuando proceda",
        "en": "Measurement/evidence through the common pipeline when applicable",
        "zh": "在适用时通过通用流水线进行测量/证据",
    },
    "magnitude_title": {
        "es": "INTEGRACIÓN MAGNITUDE",
        "en": "MAGNITUDE INTEGRATION",
        "zh": "MAGNITUDE 集成",
    },
    "magnitude_summary": {
        "es": "Magnitude — agente/asistente local orientado a tareas con el modelo elegido",
        "en": "Magnitude — local agent/assistant oriented to tasks with the chosen model",
        "zh": "Magnitude — 面向任务的本地代理/助手，配合所选模型",
    },
    "magnitude_capability_1": {
        "es": "Integración orientada a agente/asistente",
        "en": "Agent/assistant-oriented integration",
        "zh": "面向代理/助手的集成",
    },
    "magnitude_capability_2": {
        "es": "Preparación de metadatos de ejecución",
        "en": "Execution metadata preparation",
        "zh": "执行元数据准备",
    },
    "magnitude_capability_3": {
        "es": "Ejecución separada de la preparación",
        "en": "Execution separated from preparation",
        "zh": "执行与准备分离",
    },
    "magnitude_capability_4": {
        "es": "Reutilización de benchmark/evidencia comunes",
        "en": "Reuse of common benchmark/evidence",
        "zh": "复用通用基准测试/证据",
    },
    "install_blocked": {
        "es": "Instalación no autorizada",
        "en": "Installation not authorized",
        "zh": "未授权安装",
    },
    "live_input_blocked": {
        "es": "No se pudo obtener entrada real de LLMFit",
        "en": "Live LLMFit input unavailable",
        "zh": "无法获取 LLMFit 实时输入",
    },
}


def validate_catalog() -> None:
    missing = [k for k, values in TEXT.items() if set(values) != set(LANGUAGES)]
    if missing:
        raise ValueError(f"Missing translations: {', '.join(missing)}")


def get_language() -> str:
    return _active_language


def set_language(language: str) -> str:
    if language not in LANGUAGES:
        raise ValueError(f"unsupported UI language: {language}")
    global _active_language
    _active_language = language
    return _active_language


def tr(key: str, language: str | None = None) -> str:
    validate_catalog()
    lang = language or _active_language
    if lang not in LANGUAGES:
        raise ValueError(f"unsupported UI language: {lang}")
    return TEXT[key][lang]


def tr_all(key: str) -> str:
    validate_catalog()
    values = TEXT[key]
    width = max(len(LANGUAGE_LABELS[language]) for language in LANGUAGES)
    return "\n".join(
        f"{LANGUAGE_LABELS[language]:<{width}} │ {values[language]}"
        for language in LANGUAGES
    )
