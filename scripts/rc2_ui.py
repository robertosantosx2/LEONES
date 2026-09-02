#!/usr/bin/env python3
"""Presentation-only map of the RC2 beta journey.

This module is NOT the operator. The beta tester runs ``./leones``,
which executes ``scripts/rc2_wizard.py``.

``rc2_ui`` only prints an ASCII map of the canonical stages so docs and
humans share one picture of the flow. It never installs software, never
verifies stacks, and never starts a benchmark.
"""
from __future__ import annotations

BANNER = r'''
╔══════════════════════════════════════════════════════════════╗
║   ██╗     ███████╗ ██████╗ ███╗   ██╗███████╗███████╗      ║
║   ██║     ██╔════╝██╔═══██╗████╗  ██║██╔════╝██╔════╝      ║
║   ██║     █████╗  ██║   ██║██╔██╗ ██║█████╗  ███████╗      ║
║   ██║     ██╔══╝  ██║   ██║██║╚██╗██║██╔══╝  ╚════██║      ║
║   ███████╗███████╗╚██████╔╝██║ ╚████║███████╗███████║      ║
║   ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚══════╝      ║
║                    BETA · RC2                               ║
╚══════════════════════════════════════════════════════════════╝
'''

STEPS = [
    ("00", "IDIOMA", "Elegir un idioma de interfaz"),
    ("01", "HARDWARE", "Detectar equipo vía LLMFit"),
    ("02", "MODELO", "Elección humana del modelo"),
    ("03", "STACK", "ODS o Magnitude con descripción"),
    ("04", "INSTALACIÓN", "Consentimiento → instalador → verify física"),
    ("05", "A01", "Explicar → consentimiento → runner RC1"),
]


def render() -> str:
    lines = [BANNER.rstrip(), "", "  ┌─ RECORRIDO RC2 (mapa; no ejecuta) ─────────────────────┐"]
    for number, title, description in STEPS:
        lines.append(f"  │ {number}  {title:<14} │ {description:<37} │")
        if number != "05":
            lines.append("  │      │                                               │")
            lines.append("  │      ▼                                               │")
    lines += [
        "  └─────────────────────────────────────────────────────────┘",
        "",
        "  ╭─ REGLAS ───────────────────────────────────────────────╮",
        "  │ [✓] Un idioma por sesión.                             │",
        "  │ [✓] El usuario decide modelo y stack.                  │",
        "  │ [✓] Instalar NO autoriza el benchmark.                │",
        "  │ [✓] Verificar es observar el host, no confiar en exit0│",
        "  │ [✓] estimated ≠ measured.                             │",
        "  │ [✓] Un fallo nunca se presenta como medición válida.  │",
        "  ╰────────────────────────────────────────────────────────╯",
        "",
        "  ► Operador canónico: ./leones",
        "  ⚠ Esta interfaz es solo mapa; no ejecuta instalaciones.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render())
