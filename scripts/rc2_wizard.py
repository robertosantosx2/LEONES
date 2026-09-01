#!/usr/bin/env python3
"""RC2 beta wizard: live hardware/candidates -> user decisions -> handoff."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
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
from runtime_selection.llmfit import LLMFitError, run_recommend, run_system, normalise_hardware, normalise_candidates

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    L E O N E S                              ║
║                    B E T A · R C 2                         ║
╚══════════════════════════════════════════════════════════════╝
"""

STACKS = {
    "ODS": {
        "name": "ods", "adapter": "ods.v1", "mode": "local-stack",
        "title_key": "ods_title", "capability_keys": tuple(f"ods_capability_{i}" for i in range(1, 5)),
    },
    "Magnitude": {
        "name": "magnitude", "adapter": "magnitude.v1", "mode": "agent",
        "title_key": "magnitude_title", "capability_keys": tuple(f"magnitude_capability_{i}" for i in range(1, 5)),
    },
}


@dataclass
class WizardIO:
    input_fn: Callable[[str], str] = input
    output_fn: Callable[[str], None] = print

    def ask(self, prompt: str) -> str:
        return self.input_fn(prompt)

    def show(self, text: str = "") -> None:
        self.output_fn(text)


def _show_multiline(io: WizardIO, text: str, prefix: str = "") -> None:
    for line in text.splitlines():
        io.show(f"{prefix}{line}")


def _choose(io: WizardIO, title: str, options: tuple[str, ...]) -> str:
    io.show("")
    _show_multiline(io, title)
    io.show("┌──────────────────────────────────────────────────────────┐")
    for i, option in enumerate(options, 1):
        lines = option.splitlines()
        io.show(f"│  [{i}] {lines[0]}")
        for line in lines[1:]:
            io.show(f"│      {line}")
    io.show("└──────────────────────────────────────────────────────────┘")
    while True:
        answer = io.ask("LEONES> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        _show_multiline(io, tr("invalid_option"), prefix="  ! ")


def _live_inputs(io: WizardIO) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    io.show("")
    _show_multiline(io, tr("detecting_hardware"), prefix="[INFO] ")
    try:
        system = run_system()
        result = run_recommend(limit=5)
    except LLMFitError as exc:
        io.show(f"[!] {tr('llmfit_unavailable').splitlines()[0]}: {exc}")
        raise
    hardware = normalize_hardware(normalise_hardware(system))
    raw_candidates = normalise_candidates(result)
    candidates = normalize_candidates([
        {
            "model_id": item.get("model") or item.get("raw", {}).get("id"),
            "name": item.get("model") or item.get("raw", {}).get("name") or item.get("raw", {}).get("id"),
            "rank": item.get("rank"), "fit": item.get("fit"), "estimated_tps": item.get("estimated_tps"),
            "source": item.get("source", "llmfit"), "source_version": result.version,
            "evidence_level": "estimated", "revision": item.get("raw", {}).get("revision"),
        }
        for item in raw_candidates
    ])
    return hardware, candidates


def _show_stack(io: WizardIO, name: str) -> None:
    stack = STACKS[name]
    io.show("")
    _show_multiline(io, tr(stack["title_key"]))
    for capability_key in stack["capability_keys"]:
        _show_multiline(io, tr(capability_key), prefix="  ✓ ")


def run_wizard(io: WizardIO | None = None) -> BetaSession:
    io = io or WizardIO()
    session = BetaSession()
    io.show(BANNER)
    _show_multiline(io, tr("banner_subtitle"))
    _show_multiline(io, tr("your_team"))
    io.show("")
    try:
        hardware, candidates = _live_inputs(io)
    except LLMFitError:
        session.block("LLMFIT_UNAVAILABLE", tr("live_input_blocked"))
        return session

    session.advance("HARDWARE_READY", hardware=hardware)
    _show_multiline(io, tr("hardware_ready"), prefix="[✓] ")
    _show_multiline(io, tr("estimated_notice"), prefix="[i] ")
    labels = tuple(f"{c['name']} · fit={c['fit']} · ~{c['estimated_tps']} tok/s · {c['source']} · ESTIMATED" for c in candidates)
    if not labels:
        session.block("NO_MODEL_CANDIDATES", tr("no_model_candidates"))
        return session

    chosen_label = _choose(io, tr("choose_model"), labels)
    chosen = candidates[labels.index(chosen_label)]
    session.advance("MODEL_SELECTED", model_choice=chosen)
    for name in STACKS:
        _show_stack(io, name)
    stack_name = _choose(io, tr("choose_stack"), tuple(STACKS))
    stack = STACKS[stack_name]
    plan = to_selection_plan(chosen, hardware, {"name": stack["name"], "adapter": stack["adapter"], "mode": stack["mode"]})
    session.advance("STACK_SELECTED", stack=stack, stack_selection=stack, selection_plan=plan)
    _show_multiline(io, tr("selected"), prefix=f"[✓] {stack_name} / ")
    session.advance("CONSENT_REQUIRED", installation={"status": "plan_ready"})
    install = _choose(io, tr("install_consent"), (tr("authorize"), tr("cancel")))
    if install == tr("cancel"):
        session.block("INSTALL_DECLINED", tr("install_blocked"))
        return session
    session.authorize_installation()
    _show_multiline(io, tr("installation_authorized"), prefix="[✓] ")
    _show_multiline(io, tr("physical_install_notice"), prefix="[INFO] ")
    return session


def _non_interactive_smoke() -> bool:
    """Verify that synthetic installation data cannot cross the physical gate."""
    session = BetaSession()
    session.advance("HARDWARE_READY", hardware={"source": "smoke"})
    session.advance("MODEL_SELECTED", model_choice={"model_id": "smoke-model"})
    session.advance("STACK_SELECTED", stack={"name": "ods", "adapter": "ods.v1", "mode": "local-stack"})
    session.advance("CONSENT_REQUIRED", installation={"status": "plan_ready"})
    session.authorize_installation()
    try:
        session.installation_verified({"status": "fixture_verified", "real_installation": False})
    except RuntimeError:
        return session.state == "INSTALLING"
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEONES RC2 beta wizard")
    parser.add_argument("--non-interactive", action="store_true", help="verify authorization gates without physical side effects")
    args = parser.parse_args(argv)
    if args.non_interactive:
        return 0 if _non_interactive_smoke() else 1
    session = run_wizard()
    return 0 if session.state == "EXECUTION_AUTHORIZED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
