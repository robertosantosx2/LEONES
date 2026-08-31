#!/usr/bin/env python3
"""RC2 trilingual presentation strings: Español / English / 中文."""
from __future__ import annotations

LANGUAGES = ("es", "en", "zh")

TEXT = {
    "banner_subtitle": {
        "es": "BETA · RC2",
        "en": "BETA · RC2",
        "zh": "测试版 · RC2",
    },
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
        "es": "¿QUIERES EJECUTAR EL BENCHMARK?",
        "en": "DO YOU WANT TO RUN THE BENCHMARK?",
        "zh": "是否运行基准测试？",
    },
    "yes": {"es": "Sí", "en": "Yes", "zh": "是"},
    "no": {"es": "No", "en": "No", "zh": "否"},
    "back": {"es": "Volver", "en": "Back", "zh": "返回"},
    "ready": {"es": "Preparado", "en": "Ready", "zh": "已准备"},
    "blocked": {"es": "Bloqueado", "en": "Blocked", "zh": "已阻止"},
    "measured": {"es": "Medido", "en": "Measured", "zh": "已测量"},
}


def validate_catalog() -> None:
    missing = [k for k, values in TEXT.items() if set(values) != set(LANGUAGES)]
    if missing:
        raise ValueError(f"Missing translations: {', '.join(missing)}")


def tr(key: str) -> str:
    """Return all three translations, one per line, in canonical order."""
    validate_catalog()
    values = TEXT[key]
    return "\n".join((values["es"], values["en"], values["zh"]))
