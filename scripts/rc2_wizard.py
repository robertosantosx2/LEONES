#!/usr/bin/env python3
"""RC2 beta wizard: live hardware/candidates -> user decisions -> handoff."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import argparse

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rc2_beta_session import BetaSession
from scripts.rc2_i18n import tr
from runtime_selection.hardware_profile import normalize_hardware, normalize_candidates
from runtime_selection.rc2_candidates import to_selection_plan
from runtime_selection.llmfit import LLMFitError, run_recommend, normalise_hardware, normalise_candidates

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    L E O N E S                              ║
║              B E T A  ·  R C 2  ·  ES / EN / 中文          ║
╚══════════════════════════════════════════════════════════════╝
"""

STACKS = {
    "ODS": {"name":"ods","adapter":"ods.v1","mode":"local-stack","capabilities":{"es":("Stack local de inferencia","Preparación y validación del plan","Integración con ejecución local","Medición/evidencia mediante pipeline común cuando proceda"),"en":("Local inference stack","Execution-plan preparation and validation","Local execution integration","Measurement/evidence through the common pipeline when applicable"),"zh":("本地推理栈","执行计划准备与验证","本地执行集成","在适用时通过通用流水线进行测量/证据")}},
    "Magnitude": {"name":"magnitude","adapter":"magnitude.v1","mode":"agent","capabilities":{"es":("Integración orientada a agente/asistente","Preparación de metadatos de ejecución","Ejecución separada de la preparación","Reutilización de benchmark/evidencia comunes"),"en":("Agent/assistant-oriented integration","Execution metadata preparation","Execution separated from preparation","Reuse of common benchmark/evidence") ,"zh":("面向代理/助手的集成","执行元数据准备","执行与准备分离","复用通用基准测试/证据")}},
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

def _live_inputs(io: WizardIO) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Read real machine facts and recommendations from LLMFit."""
    io.show("\n[INFO] Detectando hardware y candidatos mediante LLMFit...")
    try:
        result = run_recommend(limit=5)
    except LLMFitError as exc:
        io.show(f"[!] LLMFit no disponible o inválido: {exc}")
        raise
    hardware = normalize_hardware(normalise_hardware(result))
    raw_candidates = normalise_candidates(result)
    candidates = normalize_candidates([
        {
            "model_id": item.get("model") or item.get("raw", {}).get("id"),
            "name": item.get("model") or item.get("raw", {}).get("name") or item.get("raw", {}).get("id"),
            "rank": item.get("rank"),
            "fit": item.get("fit"),
            "estimated_tps": item.get("estimated_tps"),
            "source": item.get("source", "llmfit"),
            "source_version": result.version,
            "evidence_level": "estimated",
            "revision": item.get("raw", {}).get("revision"),
        }
        for item in raw_candidates
    ])
    return hardware, candidates

def _show_stack(io: WizardIO, name: str) -> None:
    io.show(f"\n╔══ {name.upper()} ══")
    caps=STACKS[name]["capabilities"]
    for key, language in (("es","Español"),("en","English"),("zh","中文")):
        io.show(f"║  {language}")
        for c in caps[key]: io.show(f"║    ✓ {c}")
    io.show("╚═══════════════════════════════════════════════════════════")

def run_wizard(io: WizardIO|None=None) -> BetaSession:
    io=io or WizardIO(); session=BetaSession()
    io.show(BANNER); io.show(tr("your_team")); io.show("")
    try:
        hardware, candidates = _live_inputs(io)
    except LLMFitError:
        session.block("LLMFIT_UNAVAILABLE","Live LLMFit input unavailable / No se pudo obtener entrada real de LLMFit / 无法获取 LLMFit 实时输入")
        return session
    session.advance("HARDWARE_READY", hardware=hardware); io.show("[✓] Hardware real / Live hardware / 实时硬件 ✓")
    labels=tuple(f"{c['name']} · fit={c['fit']} · {c['source']}" for c in candidates)
    if not labels:
        session.block("NO_MODEL_CANDIDATES","No live candidates / No hay candidatos reales / 无实时候选模型"); return session
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
    io.show("\n[INFO] La instalación/verificación física se realiza según el manual RC2 antes de autorizar el benchmark.")
    return session

def _non_interactive_smoke() -> BetaSession:
    """Exercise only the RC2 state contract; never prompts or claims real installation."""
    session=BetaSession()
    hardware={"source":"smoke","cpu":"fixture","ram_gb":8}
    model={"model_id":"smoke-model","name":"smoke-model","fit":1.0,"source":"fixture"}
    stack={"name":"ods","adapter":"ods.v1","mode":"local-stack"}
    plan={"schema":"selection-plan.v1","mode":"smoke"}
    session.advance("HARDWARE_READY", hardware=hardware)
    session.advance("MODEL_SELECTED", model_choice=model)
    session.advance("STACK_SELECTED", stack_selection=stack, selection_plan=plan)
    session.advance("CONSENT_REQUIRED", installation={"status":"plan_ready"})
    session.authorize_installation()
    session.installation_verified({"status":"fixture_verified","real_installation":False})
    session.request_benchmark_consent({"status":"fixture_ready_for_benchmark","real_benchmark":False})
    session.authorize_benchmark()
    return session

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="LEONES RC2 beta wizard")
    parser.add_argument("--non-interactive",action="store_true",help="run deterministic state-contract smoke without prompts")
    args=parser.parse_args(argv)
    session=_non_interactive_smoke() if args.non_interactive else run_wizard()
    return 0 if session.state == "EXECUTION_AUTHORIZED" else 1

if __name__ == "__main__":
    raise SystemExit(main())
