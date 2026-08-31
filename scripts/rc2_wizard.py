#!/usr/bin/env python3
"""RC2 beta wizard: trilingual user journey up to installation consent."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from scripts.rc2_beta_session import BetaSession
from scripts.rc2_i18n import tr

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    L E O N E S                              ║
║              B E T A  ·  R C 2  ·  ES / EN / 中文          ║
╚══════════════════════════════════════════════════════════════╝
"""

STACKS = {
    "ODS": {"runtime_id":"ods","adapter_id":"ods.v1","mode":"local-stack","capabilities":{"es":("Stack local de inferencia","Preparación y validación del plan","Integración con ejecución local","Medición/evidencia mediante pipeline común cuando proceda"),"en":("Local inference stack","Execution-plan preparation and validation","Local execution integration","Measurement/evidence through the common pipeline when applicable"),"zh":("本地推理栈","执行计划准备与验证","本地执行集成","在适用时通过通用流水线进行测量/证据")}},
    "Magnitude": {"runtime_id":"magnitude","adapter_id":"magnitude.v1","mode":"agent","capabilities":{"es":("Integración orientada a agente/asistente","Preparación de metadatos de ejecución","Ejecución separada de la preparación","Reutilización de benchmark/evidencia comunes"),"en":("Agent/assistant-oriented integration","Execution metadata preparation","Execution separated from preparation","Reuse of common benchmark/evidence"),"zh":("面向智能体/助手的集成","执行元数据准备","执行与准备分离","复用通用基准测试/证据机制")}},
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

def _show_stack(io: WizardIO, name: str) -> None:
    io.show(f"\n╔══ {name.upper()} ══")
    caps=STACKS[name]["capabilities"]
    for key in ("es","en","zh"):
        io.show(f"║  {tr('choose_stack').splitlines()[{'es':0,'en':1,'zh':2}[key]]}")
        for c in caps[key]: io.show(f"║    ✓ {c}")
    io.show("╚═══════════════════════════════════════════════════════════")

def run_wizard(io: WizardIO|None=None) -> BetaSession:
    io=io or WizardIO(); session=BetaSession(); io.show(BANNER)
    io.show(tr("your_team")); io.show("")
    session.advance("HARDWARE_READY", hardware={"source":"adapter-pending"})
    io.show("[✓] Hardware preparado / Hardware ready / 硬件已准备")
    model=_choose(io,"MODELO / MODEL / 模型",("Elegir modelo recomendado / Choose recommended model / 选择推荐模型","Revisar candidatos / Review candidates / 查看候选模型"))
    session.advance("MODEL_SELECTED",model_choice=model)
    for name in STACKS: _show_stack(io,name)
    stack=_choose(io,"ELIGE TU STACK / CHOOSE YOUR STACK / 选择运行栈",tuple(STACKS)); spec=STACKS[stack]
    session.advance("STACK_SELECTED",stack_selection={"runtime_id":spec["runtime_id"],"adapter_id":spec["adapter_id"],"execution_mode":spec["mode"],"selection_source":"user"})
    io.show(f"[✓] {stack} seleccionado / selected / 已选择")
    session.advance("READY_FOR_INSTALL",installation={"status":"plan_pending"})
    install=_choose(io,"INSTALACIÓN · INSTALLATION · 安装",("Autorizar / Authorize / 授权","Cancelar / Cancel / 取消"))
    if install.startswith("Cancelar"):
        session.block("INSTALL_DECLINED","Instalación no autorizada / Installation not authorized / 未授权安装")
        return session
    session.advance("INSTALLING",installation={"status":"authorized","effect":"adapter-pending"})
    io.show("[✓] Instalación autorizada / Installation authorized / 安装已授权")
    return session

if __name__ == "__main__": run_wizard()
