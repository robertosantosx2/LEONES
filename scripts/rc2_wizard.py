#!/usr/bin/env python3
"""RC2 beta wizard: presentation and explicit decisions only.

The wizard is intentionally side-effect free. Real hardware, installation and
benchmark adapters are invoked only by later integration layers after gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from scripts.rc2_beta_session import BetaSession


BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    L E O N E S                              ║
║                     B E T A  ·  R C 2                      ║
╚══════════════════════════════════════════════════════════════╝
"""


@dataclass
class WizardIO:
    input_fn: Callable[[str], str] = input
    output_fn: Callable[[str], None] = print

    def ask(self, prompt: str) -> str:
        return self.input_fn(prompt)

    def show(self, text: str = "") -> None:
        self.output_fn(text)


def _choose(io: WizardIO, title: str, options: tuple[str, ...]) -> str:
    io.show(f"\n┌─ {title} " + "─" * max(1, 54 - len(title)) + "┐")
    for i, option in enumerate(options, 1):
        io.show(f"│  [{i}] {option}")
    io.show("└" + "─" * 58 + "┘")
    while True:
        answer = io.ask("LEONES> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        io.show("  ! Opción no válida. Elige una de las opciones mostradas.")


def run_wizard(io: WizardIO | None = None) -> BetaSession:
    io = io or WizardIO()
    session = BetaSession()
    io.show(BANNER)
    io.show("Tu equipo. Tus decisiones. Evidencia real.\n")

    session.advance("HARDWARE_READY", hardware={"source": "adapter-pending"})
    io.show("[✓] Hardware: preparado para perfilado")
    io.show("[i] En la integración real, LLMFit proporcionará el perfil y los candidatos.")

    model = _choose(io, "MODELO", ("Elegir modelo recomendado", "Revisar candidatos"))
    session.advance("MODEL_SELECTED", model_choice=model)
    io.show(f"[✓] Modelo: {model}")

    stack = _choose(io, "STACK · conoce antes de elegir", ("ODS — stack local", "Magnitude — agente/asistente"))
    session.advance("STACK_SELECTED", stack=stack)
    io.show(f"[✓] Stack: {stack}")

    session.advance("READY_FOR_INSTALL", installation={"status": "plan_pending"})
    io.show("\n[✓] Plan de instalación preparado.")
    io.show("[!] La instalación real requiere consentimiento explícito y se ejecutará fuera de este wizard.")
    return session


if __name__ == "__main__":
    run_wizard()
