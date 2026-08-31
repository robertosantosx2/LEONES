#!/usr/bin/env python3
"""RC2 beta wizard: trilingual hardware -> model -> stack -> install flow."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import argparse
import json
from pathlib import Path
import sys

# Allow the documented ``python scripts/rc2_wizard.py`` entrypoint to work
# from the repository root without requiring PYTHONPATH configuration.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rc2_beta_session import BetaSession
from scripts.rc2_i18n import tr
from runtime_selection.hardware_profile import normalize_hardware, normalize_candidates
from runtime_selection.rc2_candidates import to_selection_plan

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    L E O N E S                              ║
║              B E T A  ·  R C 2  ·  ES / EN / 中文          ║
╚══════════════════════════════════════════════════════════════╝
"""

STACKS = {
    "ODS": {"name":"ods","adapter":"ods.v1","mode":"local-stack","capabilities":{"es":("Stack local de inferencia","Preparación y validación del plan","Integración con ejecución local","Medición/evidencia mediante pipeline común cuando proceda"),"en":("Local inference stack","Execution-plan preparation and validation","Local execution integration","Measurement/evidence through the common pipeline when applicable"),"zh":("本地推理栈","执行计划准备与验证","本地执行集成","在适用时通过通用流水线进行测量/证据")}},
    "Magnitude": {"name":"magnitude","adapter":"magnitude.v1","mode":"agent","capabilities":{"es":("Integración orientada a agente/asistente","Preparación de metadatos de ejecución","Ejecución separada de la preparación","Reutilización de benchmark/evidencia comunes"),"en":("Agent/assistant-oriented integration","Execution metadata preparation","Execution separated from preparation","Reuse of common benchmark/evidence"),"zh":("面向代理/助手的集成","执行元数据准备","执行与准备分离","复用通用基准测试/证据")}},
}

@dataclass
class WizardIO:
    input_fn: Callable[[str], str] = input
    output_fn: Callable[[str], None] = print
    def ask(self, prompt: str) -> str: return self.input_fn(prompt)
    def show(self, text: str = "") -> None: self.output_fn(text)

def _choose(io: WizardIO, title: str, options: tuple[str,...]) -> str:
    io.show(f"\n┌─ {title} ────────────────────────────────────────────────┐")
    for i, option in enumerate(options,1): io.show(f"│  [{i}] {option}")
    io.show("└──────────────────────────────────────────────────────────┘")
    while True:
        answer=io.ask("LEONES> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options): return options[int(answer)-1]
        io.show("  ! Opción no válida / Invalid option / 无效选项")

def _load_json(path: Path, default: Any) -> Any:
    if not path.exists(): return default
    return json.loads(path.read_text(encoding="utf-8"))

def _show_stack(io: WizardIO, name: str) -> None:
    io.show(f"\n╔══ {name.upper()} ══")
    caps=STACKS[name]["capabilities"]
    for key in ("es","en","zh"):
        io.show(f"║  {('Español','English','中文')[('es','en','zh').index(key)]}")
        for c in caps[key]: io.show(f"║    ✓ {c}")
    io.show("╚═══════════════════════════════════════════════════════════")

def run_wizard(io: WizardIO|None=None, *, examples_root: str = "examples/rc2") -> BetaSession:
    io=io or WizardIO(); session=BetaSession(); root=Path(examples_root); io.show(BANNER); io.show(tr("your_team")); io.show("")
    hardware=normalize_hardware(_load_json(root/"hardware-profile.json", {"source":"fixture"}))
    session.advance("HARDWARE_READY", hardware=hardware); io.show("[✓] Hardware / Hardware / 硬件 ✓")
    candidates=normalize_candidates(_load_json(root/"llmfit-candidates.json", []))
    labels=tuple(f"{c['name']} · fit={c['fit']} · {c['source']}" for c in candidates)
    if not labels:
        session.block("NO_MODEL_CANDIDATES","No candidates / Aucun / 无候选模型")
        return session
    chosen_label=_choose(io,tr("choose_model"),labels); chosen=candidates[labels.index(chosen_label)]
    session.advance("MODEL_SELECTED", model_choice=chosen)
    for name in STACKS: _show_stack(io,name)
    stack_name=_choose(io,tr("choose_stack"),tuple(STACKS)); stack=STACKS[stack_name]
    plan=to_selection_plan(chosen, hardware, {"name":stack["name"],"adapter":stack["adapter"],"mode":stack["mode"]})
    session.advance("STACK_SELECTED", stack_selection=stack, selection_plan=plan)
    io.show(f"[✓] {stack_name} / selected / 已选择")
    session.advance("CONSENT_REQUIRED", installation={"status":"plan_ready"})
    install=_choose(io,tr("install_consent"),("Autorizar / Authorize / 授权","Cancelar / Cancel / 取消"))
    if install.startswith("Cancelar"):
        session.block("INSTALL_DECLINED","Installation not authorized / Instalación no autorizada / 未授权安装"); return session
    session.authorize_installation(); io.show("[✓] Instalación autorizada / Installation authorized / 安装已授权")
    return session

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEONES RC2 beta wizard")
    parser.add_argument("--non-interactive", action="store_true", help="run a deterministic smoke flow without prompts")
    args = parser.parse_args(argv)
    if args.non_interactive:
        answers = iter(("1", "1", "1"))
        session = run_wizard(WizardIO(input_fn=lambda _: next(answers)))
        return 0 if session.state == "READY_FOR_INSTALL" else 1
    session = run_wizard()
    return 0 if session.state == "READY_FOR_INSTALL" else 1

if __name__ == "__main__":
    raise SystemExit(main())
