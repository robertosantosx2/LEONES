#!/usr/bin/env python3
"""RC2 beta wizard: user journey up to benchmark authorization.

The wizard orchestrates contracts only. Installation and benchmark execution
remain explicit adapter/runner effects and are never triggered implicitly.
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

STACKS = {
    "ODS": {"runtime_id": "ods", "adapter_id": "ods.v1", "mode": "local-stack", "capabilities": ("Stack local de inferencia", "Preparación y validación del plan de ejecución", "Integración con ejecución local", "Medición/evidencia mediante el pipeline común cuando proceda")},
    "Magnitude": {"runtime_id": "magnitude", "adapter_id": "magnitude.v1", "mode": "agent", "capabilities": ("Integración orientada a agente/asistente", "Preparación de metadatos de ejecución", "Ejecución separada de la preparación", "Reutilización de benchmark/evidencia comunes")},
}

@dataclass
class WizardIO:
    input_fn: Callable[[str], str] = input
    output_fn: Callable[[str], None] = print
    def ask(self, prompt: str) -> str: return self.input_fn(prompt)
    def show(self, text: str = "") -> None: self.output_fn(text)


def _choose(io: WizardIO, title: str, options: tuple[str, ...]) -> str:
    io.show(f"\n┌─ {title} " + "─" * max(1, 54 - len(title)) + "┐")
    for i, option in enumerate(options, 1): io.show(f"│  [{i}] {option}")
    io.show("└" + "─" * 58 + "┘")
    while True:
        answer = io.ask("LEONES> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options): return options[int(answer) - 1]
        io.show("  ! Opción no válida.")


def _show_stack(io: WizardIO, name: str) -> None:
    io.show(f"\n╔══ {name.upper()} · FUNCIONALIDADES DISPONIBLES ══")
    for capability in STACKS[name]["capabilities"]: io.show(f"║  ✓ {capability}")
    io.show("╚═══════════════════════════════════════════════════════════")


def run_wizard(io: WizardIO | None = None) -> BetaSession:
    io = io or WizardIO(); session = BetaSession()
    io.show(BANNER); io.show("Tu equipo. Tus decisiones. Evidencia real.\n")
    session.advance("HARDWARE_READY", hardware={"source": "adapter-pending"})
    io.show("[✓] Hardware: preparado para perfilado")
    io.show("[i] El adaptador de hardware/LLMFit proporcionará el perfil y candidatos.")
    model = _choose(io, "MODELO", ("Elegir modelo recomendado", "Revisar candidatos"))
    session.advance("MODEL_SELECTED", model_choice=model); io.show(f"[✓] Modelo: {model}")
    for name in STACKS: _show_stack(io, name)
    stack = _choose(io, "ELIGE TU STACK", tuple(STACKS)); spec = STACKS[stack]
    session.advance("STACK_SELECTED", stack_selection={"runtime_id": spec["runtime_id"], "adapter_id": spec["adapter_id"], "execution_mode": spec["mode"], "selection_source": "user"})
    io.show(f"[✓] Stack seleccionado: {stack}")
    io.show("[i] Elegir stack no autoriza su instalación ni ningún benchmark.")
    session.advance("READY_FOR_INSTALL", installation={"status": "plan_pending"})
    io.show("\n[✓] Plan de instalación preparado.")
    install = _choose(io, "INSTALACIÓN · CONSENTIMIENTO", ("Autorizar instalación", "Cancelar"))
    if install == "Cancelar":
        session.advance("BLOCKED", installation={"status": "declined"})
        io.show("[i] Instalación cancelada. No se ejecutará ningún benchmark.")
        return session
    session.advance("INSTALLING", installation={"status": "authorized", "effect": "adapter-pending"})
    io.show("[✓] Instalación autorizada. El adaptador ejecutará el plan en la integración física.")
    io.show("[i] Esta versión del wizard no ejecuta efectos laterales automáticamente.")
    return session


if __name__ == "__main__": run_wizard()
