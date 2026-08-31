#!/usr/bin/env python3
"""Presentation-only RC2 beta terminal UI.

The UI is deliberately harmless: it never installs software or starts a
benchmark. It presents the canonical journey and the explicit consent gates.
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
    ("01", "HARDWARE", "Detectar y explicar el equipo"),
    ("02", "LLMFIT", "Construir candidatos de modelo"),
    ("03", "MODELO", "Elección humana del modelo"),
    ("04", "ODS / MAGNITUDE", "Comparar funcionalidades y elegir stack"),
    ("05", "INSTALACIÓN", "Preflight → consentimiento → instalación → verificación"),
    ("06", "BENCHMARK", "Explicar → consentimiento → ejecución → evidencia"),
]


def render() -> str:
    lines = [BANNER.rstrip(), "", "  ┌─ RECORRIDO RC2 ─────────────────────────────────────────┐"]
    for number, title, description in STEPS:
        lines.append(f"  │ {number}  {title:<18} │ {description:<35} │")
        if number != "06":
            lines.append("  │      │                                                 │")
            lines.append("  │      ▼                                                 │")
    lines += [
        "  └─────────────────────────────────────────────────────────┘",
        "",
        "  ╭─ REGLAS ───────────────────────────────────────────────╮",
        "  │ [✓] El usuario decide modelo y stack.                  │",
        "  │ [✓] Instalar NO autoriza el benchmark.                │",
        "  │ [✓] Medir NO significa publicar fuera del host.      │",
        "  │ [✓] estimated ≠ measured.                             │",
        "  │ [✓] Un fallo nunca se presenta como medición válida.  │",
        "  ╰────────────────────────────────────────────────────────╯",
        "",
        "  ► Próxima acción: seleccionar modelo",
        "  ⚠ Esta interfaz es presentación; no ejecuta instalaciones.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render())
