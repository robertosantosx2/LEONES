#!/usr/bin/env python3
"""RC2 canonical presentation catalog: Español / English / 中文."""
from __future__ import annotations

LANGUAGES = ("es", "en", "zh")
LANGUAGE_LABELS = {"es": "ES", "en": "EN", "zh": "ZH"}

TEXT = {
    "banner_subtitle": {"es": "BETA · RC2", "en": "BETA · RC2", "zh": "测试版 · RC2"},
    "your_team": {"es": "Tu equipo. Tus decisiones. Evidencia real.", "en": "Your hardware. Your decisions. Real evidence.", "zh": "你的硬件。你的选择。真实证据。"},
    "choose_model": {"es": "ELIGE TU MODELO", "en": "CHOOSE YOUR MODEL", "zh": "选择你的模型"},
    "choose_stack": {"es": "ELIGE TU STACK", "en": "CHOOSE YOUR STACK", "zh": "选择你的运行栈"},
    "install_consent": {"es": "¿AUTORIZAR LA INSTALACIÓN?", "en": "AUTHORIZE INSTALLATION?", "zh": "是否授权安装？"},
    "benchmark_consent": {"es": "¿QUIERES EJECUTAR EL BENCHMARK?", "en": "DO YOU WANT TO RUN THE BENCHMARK?", "zh": "是否运行基准测试？"},
    "yes": {"es": "Sí", "en": "Yes", "zh": "是"},
    "no": {"es": "No", "en": "No", "zh": "否"},
    "authorize": {"es": "Autorizar", "en": "Authorize", "zh": "授权"},
    "cancel": {"es": "Cancelar", "en": "Cancel", "zh": "取消"},
    "back": {"es": "Volver", "en": "Back", "zh": "返回"},
    "ready": {"es": "Preparado", "en": "Ready", "zh": "已准备"},
    "blocked": {"es": "Bloqueado", "en": "Blocked", "zh": "已阻止"},
    "measured": {"es": "Medido", "en": "Measured", "zh": "已测量"},
    "invalid_option": {"es": "Opción no válida", "en": "Invalid option", "zh": "无效选项"},
    "detecting_hardware": {"es": "Detectando hardware y candidatos mediante LLMFit...", "en": "Detecting hardware and candidates through LLMFit...", "zh": "正在通过 LLMFit 检测硬件和候选模型……"},
    "llmfit_unavailable": {"es": "LLMFit no disponible o inválido", "en": "LLMFit unavailable or invalid", "zh": "LLMFit 不可用或无效"},
    "hardware_ready": {"es": "Hardware real", "en": "Live hardware", "zh": "实时硬件"},
    "estimated_notice": {"es": "Las cifras de LLMFit son ESTIMACIONES. No son evidencia de ejecución real.", "en": "LLMFit values are ESTIMATES. They are not real execution evidence.", "zh": "LLMFit 数值是估算值，不是真实执行证据。"},
    "no_model_candidates": {"es": "No hay candidatos reales", "en": "No live candidates", "zh": "无实时候选模型"},
    "selected": {"es": "seleccionado", "en": "selected", "zh": "已选择"},
    "installation_authorized": {"es": "Instalación autorizada", "en": "Installation authorized", "zh": "安装已授权"},
    "physical_install_notice": {"es": "La instalación/verificación física se realiza según el manual RC2 antes de autorizar el benchmark.", "en": "Physical installation/verification follows the RC2 manual before benchmark authorization.", "zh": "在授权基准测试前，须按照 RC2 手册完成实际安装/验证。"},
    "ods_title": {"es": "STACK LOCAL ODS", "en": "ODS LOCAL STACK", "zh": "ODS 本地运行栈"},
    "ods_capability_1": {"es": "Stack local de inferencia", "en": "Local inference stack", "zh": "本地推理栈"},
    "ods_capability_2": {"es": "Preparación y validación del plan", "en": "Execution-plan preparation and validation", "zh": "执行计划准备与验证"},
    "ods_capability_3": {"es": "Integración con ejecución local", "en": "Local execution integration", "zh": "本地执行集成"},
    "ods_capability_4": {"es": "Medición/evidencia mediante pipeline común cuando proceda", "en": "Measurement/evidence through the common pipeline when applicable", "zh": "在适用时通过通用流水线进行测量/证据"},
    "magnitude_title": {"es": "INTEGRACIÓN MAGNITUDE", "en": "MAGNITUDE INTEGRATION", "zh": "MAGNITUDE 集成"},
    "magnitude_capability_1": {"es": "Integración orientada a agente/asistente", "en": "Agent/assistant-oriented integration", "zh": "面向代理/助手的集成"},
    "magnitude_capability_2": {"es": "Preparación de metadatos de ejecución", "en": "Execution metadata preparation", "zh": "执行元数据准备"},
    "magnitude_capability_3": {"es": "Ejecución separada de la preparación", "en": "Execution separated from preparation", "zh": "执行与准备分离"},
    "magnitude_capability_4": {"es": "Reutilización de benchmark/evidencia comunes", "en": "Reuse of common benchmark/evidence", "zh": "复用通用基准测试/证据"},
    "install_blocked": {"es": "Instalación no autorizada", "en": "Installation not authorized", "zh": "未授权安装"},
    "live_input_blocked": {"es": "No se pudo obtener entrada real de LLMFit", "en": "Live LLMFit input unavailable", "zh": "无法获取 LLMFit 实时输入"},
}


def validate_catalog() -> None:
    missing = [k for k, values in TEXT.items() if set(values) != set(LANGUAGES)]
    if missing:
        raise ValueError(f"Missing translations: {', '.join(missing)}")


def tr(key: str) -> str:
    """Return one aligned ES/EN/ZH presentation block."""
    validate_catalog()
    values = TEXT[key]
    width = max(len(label) for label in LANGUAGE_LABELS.values())
    return "\n".join(
        f"{LANGUAGE_LABELS[language]:<{width}} │ {values[language]}"
        for language in LANGUAGES
    )
