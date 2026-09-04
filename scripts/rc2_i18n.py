#!/usr/bin/env python3
"""RC2 presentation catalog: Español / English / 中文."""
from __future__ import annotations

LANGUAGES = ("es", "en", "zh")
LANGUAGE_LABELS = {"es": "Español", "en": "English", "zh": "中文"}
_active_language = "es"


def _triple(es: str, en: str, zh: str) -> dict[str, str]:
    return {"es": es, "en": en, "zh": zh}

TEXT = {
    "choose_language": _triple("ELIGE EL IDIOMA DE LA INTERFAZ", "CHOOSE THE INTERFACE LANGUAGE", "选择界面语言"),
    "banner_subtitle": _triple("BETA · RC2\nSiguiente: LEONES detectará tu hardware y obtendrá los candidatos de LLMFit.", "BETA · RC2\nNext: LEONES will detect your hardware and obtain LLMFit candidates.", "测试版 · RC2\n下一步：LEONES 将检测你的硬件并获取 LLMFit 候选模型。"),
    "your_team": _triple("Tu equipo. Tus decisiones. Evidencia real.", "Your hardware. Your decisions. Real evidence.", "你的硬件。你的选择。真实证据。"),
    "choose_model": _triple("ELIGE TU MODELO\nSiguiente: elige el candidato que quieres llevar a la siguiente fase.", "CHOOSE YOUR MODEL\nNext: choose the candidate you want to take to the next phase.", "选择你的模型\n下一步：选择要进入下一阶段的候选模型。"),
    "choose_stack": _triple("ELIGE TU STACK\nSiguiente: LEONES preparará el plan de ejecución y te pedirá autorización antes de instalar.", "CHOOSE YOUR STACK\nNext: LEONES will prepare the execution plan and ask for authorization before installing.", "选择你的运行栈\n下一步：LEONES 将准备执行计划，并在安装前请求授权。"),
    "install_consent": _triple("¿AUTORIZAR LA INSTALACIÓN?\nSiguiente: si autorizas, podrás ejecutar el instalador canónico del stack elegido.", "AUTHORIZE INSTALLATION?\nNext: if you authorize it, you can run the canonical installer for the chosen stack.", "是否授权安装？\n下一步：授权后，你可以运行所选运行栈的标准安装程序。"),
    "benchmark_consent": _triple("¿QUIERES EJECUTAR EL BENCHMARK A01?\nSiguiente: solo con tu autorización se ejecutará la medición local.", "DO YOU WANT TO RUN THE A01 BENCHMARK?\nNext: the local measurement runs only with your authorization.", "是否运行 A01 基准测试？\n下一步：只有获得授权后才会执行本地测量。"),
    "yes": _triple("Sí", "Yes", "是"), "no": _triple("No", "No", "否"), "authorize": _triple("Autorizar", "Authorize", "授权"), "cancel": _triple("Cancelar", "Cancel", "取消"), "back": _triple("Volver", "Back", "返回"), "ready": _triple("Preparado", "Ready", "已准备"), "blocked": _triple("Bloqueado", "Blocked", "已阻止"), "measured": _triple("Medido", "Measured", "已测量"),
    "invalid_option": _triple("Opción no válida", "Invalid option", "无效选项"),
    "detecting_hardware": _triple("Detectando hardware y candidatos mediante LLMFit...\nSiguiente: con el hardware observado, LEONES construirá la lista de candidatos.", "Detecting hardware and candidates through LLMFit...\nNext: using the observed hardware, LEONES will build the candidate list.", "正在通过 LLMFit 检测硬件和候选模型……\n下一步：LEONES 将根据观察到的硬件建立候选模型列表。"),
    "llmfit_unavailable": _triple("LLMFit no disponible o inválido", "LLMFit unavailable or invalid", "LLMFit 不可用或无效"),
    "hardware_ready": _triple("Hardware real detectado.\nSiguiente: revisar los candidatos y seleccionar un modelo.", "Live hardware detected.\nNext: review the candidates and select a model.", "已检测到实时硬件。\n下一步：查看候选模型并选择一个模型。"),
    "estimated_notice": _triple("Las cifras de LLMFit son ESTIMACIONES. No son evidencia de ejecución real.\nSiguiente: la selección será declarativa; la ejecución real se comprobará más adelante.", "LLMFit values are ESTIMATES. They are not real execution evidence.\nNext: selection is declarative; real execution will be verified later.", "LLMFit 数值是估算值，不是真实执行证据。\n下一步：当前选择是声明性的；稍后将验证真实执行。"),
    "no_model_candidates": _triple("No hay candidatos reales", "No live candidates", "无实时候选模型"),
    "selected": _triple("seleccionado.\nSiguiente: LEONES preparará el plan de selección y abrirá la puerta de autorización de instalación.", "selected.\nNext: LEONES will prepare the selection plan and open the installation authorization gate.", "已选择。\n下一步：LEONES 将准备选择计划并打开安装授权关卡。"),
    "installation_authorized": _triple("Consentimiento de instalación concedido.\nSiguiente: se ofrecerá ejecutar el instalador canónico.", "Installation consent granted.\nNext: you will be offered the canonical installer.", "已授予安装授权。\n下一步：系统将提供运行标准安装程序的选项。"),
    "not_installed_yet": _triple("Aún NO se ha instalado nada en tu equipo.", "Nothing has been installed on your machine yet.", "尚未在你的设备上安装任何内容。"),
    "what_was_decided": _triple("RESUMEN DE DECISIONES", "DECISION SUMMARY", "决策摘要"),
    "label_model": _triple("Modelo", "Model", "模型"), "label_stack": _triple("Stack", "Stack", "运行栈"), "label_status": _triple("Estado", "Status", "状态"),
    "status_authorized_not_installed": _triple("autorizado · instalación física pendiente", "authorized · physical install pending", "已授权 · 实际安装待完成"),
    "next_step_title": _triple("SIGUIENTE PASO", "NEXT STEP", "下一步"),
    "next_step_ods": _triple("Instalar ODS con el instalador canónico de LEONES:", "Install ODS with the canonical LEONES installer:", "使用 LEONES 标准安装程序安装 ODS："),
    "next_step_magnitude": _triple("Instalar Magnitude con el instalador canónico de LEONES:", "Install Magnitude with the canonical LEONES installer:", "使用 LEONES 标准安装程序安装 Magnitude："),
    "next_step_after_install": _triple("Cuando termine la instalación, verifica el stack. Solo entonces podrás autorizar un benchmark. Instalar ≠ medir.", "When installation finishes, verify the stack. Only then can you authorize a benchmark. Install ≠ measure.", "安装完成后请验证运行栈。只有在那之后才能授权基准测试。安装 ≠ 测量。"),
    "offer_run_installer": _triple("¿Ejecutar ahora el instalador canónico del stack elegido?", "Run the canonical installer for the chosen stack now?", "现在运行所选运行栈的标准安装程序吗？"),
    "run_installer_yes": _triple("Sí, ejecutar el instalador ahora", "Yes, run the installer now", "是，现在运行安装程序"),
    "run_installer_no": _triple("No, lo haré yo más tarde", "No, I will do it later", "否，我稍后再做"),
    "installer_launching": _triple("Lanzando instalador canónico...\nSiguiente: cuando termine, LEONES comprobará físicamente el host.", "Launching canonical installer...\nNext: when it finishes, LEONES will physically verify the host.", "正在启动标准安装程序……\n下一步：完成后，LEONES 将对主机进行物理验证。"),
    "installer_finished_ok": _triple("El instalador terminó. Eso no es verificación LEONES; ahora comprobamos el host.\nSiguiente: necesitamos PASS de verificación física antes de medir.", "Installer finished. That is not LEONES verification; now we check the host.\nNext: physical verification must PASS before measuring.", "安装程序已结束。这不是 LEONES 验证；现在检查主机。\n下一步：物理验证必须通过后才能测量。"),
    "installer_finished_fail": _triple("El instalador falló o se canceló. Conserva el mensaje original; no se ha marcado como verificado.\nSiguiente: corrige o completa la instalación y vuelve a verificar.", "Installer failed or was cancelled. Keep the original message; nothing was marked verified.\nNext: fix or complete the installation and verify again.", "安装程序失败或已取消。请保留原始信息；未标记为已验证。\n下一步：修复或完成安装后再次验证。"),
    "installer_deferred": _triple("Instalador no ejecutado. Aun así puedes verificar si el stack ya está en el equipo.\nSiguiente: LEONES comprobará físicamente si el stack está disponible.", "Installer not run. You can still verify if the stack is already on the host.\nNext: LEONES will physically check whether the stack is available.", "未运行安装程序。如果运行栈已在主机上，仍可验证。\n下一步：LEONES 将物理检查运行栈是否可用。"),
    "verify_title": _triple("VERIFICACIÓN FÍSICA", "PHYSICAL VERIFICATION", "物理验证"),
    "verify_running": _triple("Comprobando en este equipo si el stack está realmente instalado...\nSiguiente: el resultado decidirá si se abre la puerta del benchmark.", "Checking this host for a real stack installation...\nNext: the result will decide whether the benchmark gate opens.", "正在检查此主机是否真正安装了运行栈……\n下一步：验证结果将决定是否打开基准测试关卡。"),
    "verify_pass": _triple("Verificación física: PASS. El stack se observó en este equipo.", "Physical verification: PASS. The stack was observed on this host.", "物理验证：通过。已在此主机上观察到运行栈。"),
    "verify_fail": _triple("Verificación física: FAIL. El stack no está verificado en este equipo.", "Physical verification: FAIL. The stack is not verified on this host.", "物理验证：失败。此主机上的运行栈未通过验证。"),
    "verify_missing": _triple("Faltan o fallan estas comprobaciones:", "These checks are missing or failed:", "缺少或失败的检查："), "verify_observed": _triple("Observado:", "Observed:", "观察到："),
    "verify_next_fail": _triple("Instala o repara el stack y vuelve a verificar. Sin PASS no hay benchmark.\nSiguiente: conseguir PASS; no se ejecutará ninguna medición antes.", "Install or repair the stack and verify again. No PASS means no benchmark.\nNext: obtain PASS; no measurement will run before that.", "请安装或修复运行栈后再次验证。未通过则不能进行基准测试。\n下一步：先获得通过状态；此前不会进行任何测量。"),
    "verify_next_pass": _triple("Stack verificado. Siguiente puerta: consentimiento de benchmark A01.", "Stack verified. Next gate: A01 benchmark consent.", "运行栈已验证。下一关：A01 基准测试授权。"),
    "offer_verify_again": _triple("¿Reintentar la verificación física?", "Retry physical verification?", "是否重试物理验证？"), "verify_again_yes": _triple("Sí, verificar de nuevo", "Yes, verify again", "是，再次验证"), "verify_again_no": _triple("No, salir sin verificar", "No, exit without verification", "否，在未验证的情况下退出"),
    "a01_title": _triple("BENCHMARK A01 (LEONES-Agentic)", "A01 BENCHMARK (LEONES-Agentic)", "A01 基准测试（LEONES-Agentic）"),
    "a01_what": _triple("Tarea agentic local: el modelo debe emitir exactamente dos tool calls (lookup_model → write_report).", "Local agentic task: the model must emit exactly two tool calls (lookup_model → write_report).", "本地代理任务：模型必须恰好发出两次工具调用（lookup_model → write_report）。"),
    "a01_metrics": _triple("Se medirá: wall_seconds, measured_tps y grader_pass. ESTIMATED de LLMFit no cuenta como medición.", "Measured: wall_seconds, measured_tps and grader_pass. LLMFit ESTIMATED values are not measurements.", "将测量：wall_seconds、measured_tps 和 grader_pass。LLMFit 估算值不算测量。"),
    "a01_runtime": _triple("Runner RC1 canónico vía Ollama o llama.cpp cuando el runtime y el artefacto estén disponibles.", "Canonical RC1 runner via Ollama or llama.cpp when runtime and artifact are available.", "在运行时和产物可用时，通过 Ollama 或 llama.cpp 使用标准 RC1 运行器。"),
    "a01_privacy": _triple("La evidencia se guarda en el host. Cancelar no invalida la instalación.", "Evidence stays on the host. Declining does not invalidate the installation.", "证据保存在主机上。拒绝不会使安装失效。"),
    "benchmark_run_yes": _triple("Sí, ejecutar A01 ahora", "Yes, run A01 now", "是，现在运行 A01"), "benchmark_run_no": _triple("No, no medir ahora", "No, do not measure now", "否，现在不测量"),
    "benchmark_declined": _triple("Benchmark declinado. Instalación intacta; no se ha medido nada.\nSiguiente: puedes volver a ejecutar el wizard cuando quieras medir.", "Benchmark declined. Installation intact; nothing was measured.\nNext: you can run the wizard again whenever you want to measure.", "已拒绝基准测试。安装保持不变；未进行任何测量。\n下一步：需要测量时可以再次运行向导。"),
    "benchmark_authorized": _triple("Benchmark autorizado. Handoff RC1 activo.\nSiguiente: se ejecutará A01 y se generará evidencia de ejecución.", "Benchmark authorized. RC1 handoff active.\nNext: A01 will run and execution evidence will be generated.", "已授权基准测试。RC1 交接已激活。\n下一步：将运行 A01 并生成执行证据。"),
    "benchmark_running": _triple("Ejecutando A01 (runner RC1)...\nSiguiente: al finalizar se comprobará si la salida es una medición válida.", "Running A01 (RC1 runner)...\nNext: when it finishes, the output will be checked for a valid measurement.", "正在运行 A01（RC1 运行器）……\n下一步：完成后将检查输出是否为有效测量。"),
    "benchmark_need_ollama": _triple("No se puede ejecutar A01: hace falta Ollama local en PATH y un modelo disponible.\nSiguiente: prepara el runtime/modelo y vuelve a ejecutar la fase de benchmark.", "Cannot run A01: local Ollama on PATH and an available model are required.\nNext: prepare the runtime/model and rerun the benchmark phase.", "无法运行 A01：需要 PATH 中的本地 Ollama 和可用模型。\n下一步：准备运行时和模型后重新执行基准测试阶段。"),
    "benchmark_need_llamacpp": _triple("No se puede ejecutar A01: hace falta llama.cpp en PATH (llama-cli o llama).\nSiguiente: instala llama.cpp y vuelve a la fase de benchmark.", "Cannot run A01: llama.cpp must be on PATH (llama-cli or llama).\nNext: install llama.cpp and return to the benchmark phase.", "无法运行 A01：PATH 中需要 llama.cpp（llama-cli 或 llama）。\n下一步：安装 llama.cpp 后返回基准测试阶段。"),
    "runtime_unresolved": _triple("No se puede abrir A01: el modelo seleccionado no tiene un runtime ejecutable resuelto.\nSiguiente: elige un candidato con runtime conocido (Ollama o GGUF/llama.cpp) o prepara el artefacto.", "Cannot open A01: the selected model has no resolved executable runtime.\nNext: choose a candidate with a known runtime (Ollama or GGUF/llama.cpp) or prepare the artifact.", "无法打开 A01：所选模型没有已解析的可执行运行时。\n下一步：选择具有已知运行时的候选（Ollama 或 GGUF/llama.cpp），或准备产物。"),
    "runtime_adapter_pending": _triple("El runtime está resuelto, pero A01 aún no tiene adaptador ejecutable para él.\nSiguiente: usa Ollama o llama.cpp, o espera el adaptador correspondiente.", "The runtime is resolved, but A01 has no executable adapter for it yet.\nNext: use Ollama or llama.cpp, or wait for the matching adapter.", "运行时已解析，但 A01 尚无对应的可执行适配器。\n下一步：使用 Ollama 或 llama.cpp，或等待匹配的适配器。"),
    "benchmark_failed": _triple("A01 falló o no produjo medición válida. No se publica como MEASURED.\nSiguiente: conservar el diagnóstico, corregir el runtime y volver a medir.", "A01 failed or did not produce a valid measurement. Not published as MEASURED.\nNext: keep the diagnosis, fix the runtime and measure again.", "A01 失败或未产生有效测量。不会发布为 MEASURED。\n下一步：保留诊断信息，修复运行时后再次测量。"),
    "benchmark_completed": _triple("A01 completado. Evidencia guardada en el host.\nSiguiente: la evidencia medida queda disponible para el flujo de recomendación de LEONES.", "A01 completed. Evidence saved on the host.\nNext: the measured evidence is now available to LEONES' recommendation flow.", "A01 已完成。证据已保存在主机上。\n下一步：测量证据现在可供 LEONES 推荐流程使用。"),
    "ods_title": _triple("STACK LOCAL ODS", "ODS LOCAL STACK", "ODS 本地运行栈"), "ods_summary": _triple("ODS — stack local de inferencia (modelos, UI y servicios en tu máquina)", "ODS — local inference stack (models, UI and services on your machine)", "ODS — 本地推理栈（在你的机器上运行模型、界面和服务）"),
    "ods_capability_1": _triple("Stack local de inferencia", "Local inference stack", "本地推理栈"), "ods_capability_2": _triple("Preparación y validación del plan", "Execution-plan preparation and validation", "执行计划准备与验证"), "ods_capability_3": _triple("Integración con ejecución local", "Local execution integration", "本地执行集成"), "ods_capability_4": _triple("Medición/evidencia mediante pipeline común cuando proceda", "Measurement/evidence through the common pipeline when applicable", "在适用时通过通用流水线进行测量/证据"),
    "magnitude_title": _triple("INTEGRACIÓN MAGNITUDE", "MAGNITUDE INTEGRATION", "MAGNITUDE 集成"), "magnitude_summary": _triple("Magnitude — agente/asistente local orientado a tareas con el modelo elegido", "Magnitude — local agent/assistant oriented to tasks with the chosen model", "Magnitude — 面向任务的本地代理/助手，配合所选模型"), "magnitude_capability_1": _triple("Integración orientada a agente/asistente", "Agent/assistant-oriented integration", "面向代理/助手的集成"), "magnitude_capability_2": _triple("Preparación de metadatos de ejecución", "Execution metadata preparation", "执行元数据准备"), "magnitude_capability_3": _triple("Ejecución separada de la preparación", "Execution separated from preparation", "执行与准备分离"), "magnitude_capability_4": _triple("Reutilización de benchmark/evidencia comunes", "Reuse of common benchmark/evidence", "复用通用基准测试/证据"),
    "install_blocked": _triple("Instalación no autorizada", "Installation not authorized", "未授权安装"), "live_input_blocked": _triple("No se pudo obtener entrada real de LLMFit", "Live LLMFit input unavailable", "无法获取 LLMFit 实时输入"),
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
    return "\n".join(f"{LANGUAGE_LABELS[language]} │ {values[language]}" for language in LANGUAGES)
