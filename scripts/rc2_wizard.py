#!/usr/bin/env python3
"""RC2 beta wizard: live hardware/candidates -> decisions -> runtime resolution -> A01.

This is the only operator path for beta testers (`./leones`). It never invents
PASS for physical verification or MEASURED for benchmarks. A01 reuses the RC1
runner; RC2 only orchestrates consent and preflight.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rc2_beta_session import BetaSession
from scripts.rc2_i18n import LANGUAGES, LANGUAGE_LABELS, set_language, tr
from scripts.integrations.verify_physical import verify_stack
from scripts.a01_runtime_preflight import check_ollama_model
from runtime_selection.hardware_profile import normalize_hardware, normalize_candidates
from runtime_selection.rc2_candidates import to_selection_plan
from runtime_selection.llmfit import (
    LLMFitError,
    run_recommend,
    run_system,
    normalise_hardware,
    normalise_candidates,
)
from runtime_selection.model_runtime_resolver import resolve_model_runtime

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    L E O N E S                              ║
║                    B E T A · R C 2                         ║
╚══════════════════════════════════════════════════════════════╝
"""

STACKS = {
    "ODS": {
        "name": "ods",
        "adapter": "ods.v1",
        "mode": "local-stack",
        "title_key": "ods_title",
        "summary_key": "ods_summary",
        "next_step_key": "next_step_ods",
        "install_script": "scripts/integrations/install_ods.sh",
        "capability_keys": tuple(f"ods_capability_{i}" for i in range(1, 5)),
    },
    "Magnitude": {
        "name": "magnitude",
        "adapter": "magnitude.v1",
        "mode": "agent",
        "title_key": "magnitude_title",
        "summary_key": "magnitude_summary",
        "next_step_key": "next_step_magnitude",
        "install_script": "scripts/integrations/install_magnitude.sh",
        "capability_keys": tuple(f"magnitude_capability_{i}" for i in range(1, 5)),
    },
}

A01_BENCHMARK = {
    "id": "LEONES-Agentic",
    "version": "1.0",
    "task": "A01",
    "task_version": "1.0",
    "prompt": "Execute A01. Return only JSONL tool calls.",
    "metrics": ["wall_seconds", "measured_tps", "grader_pass"],
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


def _choose_language(io: WizardIO) -> str:
    labels = tuple(LANGUAGE_LABELS[code] for code in LANGUAGES)
    io.show("")
    io.show("ELIGE EL IDIOMA / CHOOSE LANGUAGE / 选择语言")
    io.show("┌──────────────────────────────────────────────────────────┐")
    for i, label in enumerate(labels, 1):
        io.show(f"│  [{i}] {label}")
    io.show("└──────────────────────────────────────────────────────────┘")
    while True:
        answer = io.ask("LEONES> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(LANGUAGES):
            return set_language(LANGUAGES[int(answer) - 1])
        io.show("  ! Invalid option / Opción no válida / 无效选项")


def _live_inputs(io: WizardIO) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    io.show("")
    _show_multiline(io, tr("detecting_hardware"), prefix="[INFO] ")
    try:
        system = run_system()
        result = run_recommend(limit=5)
    except LLMFitError as exc:
        io.show(f"[!] {tr('llmfit_unavailable')}: {exc}")
        raise
    hardware = normalize_hardware(normalise_hardware(system))
    raw_candidates = normalise_candidates(result)
    candidates = normalize_candidates(
        [
            {
                "model_id": item.get("model") or item.get("raw", {}).get("id"),
                "name": item.get("model")
                or item.get("raw", {}).get("name")
                or item.get("raw", {}).get("id"),
                "rank": item.get("rank"),
                "fit": item.get("fit"),
                "estimated_tps": item.get("estimated_tps"),
                "source": item.get("source", "llmfit"),
                "source_version": result.version,
                "evidence_level": "estimated",
                "revision": item.get("raw", {}).get("revision"),
            }
            for item in raw_candidates
        ]
    )
    return hardware, candidates


def _show_stack(io: WizardIO, name: str) -> None:
    stack = STACKS[name]
    io.show("")
    _show_multiline(io, tr(stack["title_key"]))
    _show_multiline(io, tr(stack["summary_key"]), prefix="  → ")
    for capability_key in stack["capability_keys"]:
        _show_multiline(io, tr(capability_key), prefix="  ✓ ")


def _stack_choice_labels() -> tuple[str, ...]:
    return tuple(tr(STACKS[name]["summary_key"]) for name in STACKS)


def _show_decision_summary(
    io: WizardIO,
    *,
    model_name: str,
    stack_name: str,
    stack: dict[str, Any],
) -> None:
    script = stack["install_script"]
    io.show("")
    io.show("═" * 60)
    _show_multiline(io, tr("what_was_decided"))
    io.show("═" * 60)
    io.show(f"  {tr('label_model')}: {model_name}")
    io.show(f"  {tr('label_stack')}: {stack_name} ({stack['name']})")
    io.show(f"  {tr('label_status')}: {tr('status_authorized_not_installed')}")
    io.show("")
    _show_multiline(io, tr("installation_authorized"), prefix="[✓] ")
    _show_multiline(io, tr("not_installed_yet"), prefix="[!] ")
    io.show("")
    _show_multiline(io, tr("next_step_title"))
    _show_multiline(io, tr(stack["next_step_key"]), prefix="  ")
    io.show(f"  $ bash {script}")
    io.show("")
    _show_multiline(io, tr("next_step_after_install"), prefix="[i] ")


def _maybe_run_installer(io: WizardIO, stack: dict[str, Any]) -> dict[str, Any]:
    script = REPO_ROOT / stack["install_script"]
    choice = _choose(
        io,
        tr("offer_run_installer"),
        (tr("run_installer_yes"), tr("run_installer_no")),
    )
    if choice == tr("run_installer_no"):
        _show_multiline(io, tr("installer_deferred"), prefix="[i] ")
        return {
            "status": "deferred",
            "script": str(script.relative_to(REPO_ROOT)),
            "real_installation": False,
        }

    _show_multiline(io, tr("installer_launching"), prefix="[INFO] ")
    io.show(f"[INFO] $ bash {script.relative_to(REPO_ROOT)}")
    try:
        rc = subprocess.run(["bash", str(script)], cwd=str(REPO_ROOT), check=False).returncode
    except OSError as exc:
        io.show(f"[!] {exc}")
        rc = 1

    if rc == 0:
        _show_multiline(io, tr("installer_finished_ok"), prefix="[✓] ")
        return {
            "status": "installer_exited_0",
            "script": str(script.relative_to(REPO_ROOT)),
            "returncode": rc,
            "real_installation": False,
        }

    _show_multiline(io, tr("installer_finished_fail"), prefix="[!] ")
    return {
        "status": "installer_failed_or_cancelled",
        "script": str(script.relative_to(REPO_ROOT)),
        "returncode": rc,
        "real_installation": False,
    }


def _show_verification(io: WizardIO, result: dict[str, Any]) -> None:
    io.show("")
    io.show("═" * 60)
    _show_multiline(io, tr("verify_title"))
    io.show("═" * 60)
    if result.get("status") == "PASS" and result.get("real_installation") is True:
        _show_multiline(io, tr("verify_pass"), prefix="[✓] ")
    else:
        _show_multiline(io, tr("verify_fail"), prefix="[!] ")
    if result.get("observed"):
        io.show(f"  {tr('verify_observed')}")
        for key, value in result["observed"].items():
            io.show(f"    - {key}: {value}")
    if result.get("missing"):
        io.show(f"  {tr('verify_missing')}")
        for item in result["missing"]:
            io.show(f"    - {item}")
    if result.get("message"):
        io.show(f"  [i] {result['message']}")


def _run_physical_verification(io: WizardIO, stack_name: str) -> dict[str, Any]:
    while True:
        io.show("")
        _show_multiline(io, tr("verify_running"), prefix="[INFO] ")
        result = verify_stack(stack_name).to_dict()
        _show_verification(io, result)
        if result.get("status") == "PASS" and result.get("real_installation") is True:
            _show_multiline(io, tr("verify_next_pass"), prefix="[✓] ")
            return result
        _show_multiline(io, tr("verify_next_fail"), prefix="[!] ")
        again = _choose(
            io,
            tr("offer_verify_again"),
            (tr("verify_again_yes"), tr("verify_again_no")),
        )
        if again == tr("verify_again_no"):
            return result


def _show_a01_explanation(io: WizardIO, model_id: str) -> None:
    io.show("")
    io.show("═" * 60)
    _show_multiline(io, tr("a01_title"))
    io.show("═" * 60)
    _show_multiline(io, tr("a01_what"), prefix="  • ")
    _show_multiline(io, tr("a01_metrics"), prefix="  • ")
    _show_multiline(io, tr("a01_runtime"), prefix="  • ")
    _show_multiline(io, tr("a01_privacy"), prefix="  • ")
    io.show(f"  • model_id: {model_id}")
    io.show(f"  • task: {A01_BENCHMARK['task']} / {A01_BENCHMARK['id']} {A01_BENCHMARK['version']}")


def _build_a01_selection(
    model_choice: dict[str, Any],
    hardware: dict[str, Any],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    model_id = str(model_choice.get("model_id") or model_choice.get("name") or "")
    name = str(model_choice.get("name") or model_id)
    quant = str(
        model_choice.get("quantization")
        or ("Q4_1" if resolution.get("model_format") == "GGUF" else "unknown")
    )
    return {
        "candidates": [
            {
                "selection_status": "TOP_N",
                "rank": model_choice.get("rank") or 1,
                "fit_score": model_choice.get("fit"),
                "evidence_level": model_choice.get("evidence_level", "estimated"),
                "model_id": model_id,
                "model_name": name,
                "model": {
                    "id": model_id,
                    "name": name,
                    "revision": model_choice.get("revision"),
                },
                "runtime": resolution["runtime_id"],
                "runtime_version": "local",
                "quantization": quant,
                "model_format": resolution["model_format"],
                "runtime_model_ref": resolution.get("runtime_model_ref"),
                "optimization_families": [],
                "hardware": hardware or {},
                "workload": {},
                "llmfit": {"estimated_tps": model_choice.get("estimated_tps")},
            }
        ]
    }


def _build_runtime_commands(resolution: dict[str, Any], model_id: str) -> dict[str, list[str]]:
    runtime_id = resolution.get("runtime_id")
    if runtime_id == "ollama":
        bridge = REPO_ROOT / "scripts" / "ollama_a01_runtime.py"
        return {"ollama": [sys.executable, str(bridge), "--model", model_id]}
    if runtime_id == "llama.cpp":
        bridge = REPO_ROOT / "scripts" / "llama_cpp_a01_runtime.py"
        ref = resolution.get("runtime_model_ref")
        if not ref:
            raise RuntimeError("llama.cpp resolution has no executable model reference")
        return {"llama.cpp": [sys.executable, str(bridge), "--model-ref", str(ref)]}
    return {}


def _resolve_for_benchmark(model_choice: dict[str, Any]) -> dict[str, Any]:
    return resolve_model_runtime(model_choice).to_dict()


def _llama_available() -> tuple[bool, str]:
    if shutil.which("llama-cli"):
        return True, "llama-cli"
    if shutil.which("llama"):
        return True, "llama cli"
    return False, "llama.cpp CLI not found (expected llama-cli or llama)"


def _run_a01(
    io: WizardIO,
    *,
    model_choice: dict[str, Any],
    hardware: dict[str, Any],
    resolution: dict[str, Any],
) -> dict[str, Any]:
    model_id = str(model_choice.get("model_id") or model_choice.get("name") or "")
    runtime_id = resolution.get("runtime_id")
    if runtime_id not in {"ollama", "llama.cpp"}:
        return {
            "status": "benchmark_blocked",
            "reason": f"runtime {runtime_id or 'unknown'} has no RC2 A01 executable adapter yet",
            "measured": False,
            "resolution": resolution,
        }
    if runtime_id == "ollama":
        preflight = check_ollama_model(model_id)
        if not preflight.available or not preflight.model_available:
            return {
                "status": "benchmark_blocked",
                "reason": preflight.reason,
                "model_id": model_id,
                "installed_models": list(preflight.installed_models),
                "measured": False,
                "resolution": resolution,
            }

    work = REPO_ROOT / ".leones" / "rc2-a01"
    work.mkdir(parents=True, exist_ok=True)
    selection_path = work / "selection.json"
    runtime_commands_path = work / "runtime-commands.json"
    out_path = work / "a01-runtime-benchmark.v1.json"
    workspace = work / "workspace"

    selection = _build_a01_selection(model_choice, hardware, resolution)
    runtime_commands = _build_runtime_commands(resolution, model_id)
    selection_path.write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    runtime_commands_path.write_text(
        json.dumps(runtime_commands, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    _show_multiline(io, tr("benchmark_running"), prefix="[INFO] ")
    io.show(f"[INFO] model_id={model_id}")
    io.show(f"[INFO] runtime={runtime_id}")
    io.show(f"[INFO] model_ref={resolution.get('runtime_model_ref')}")
    io.show(f"[INFO] out={out_path.relative_to(REPO_ROOT)}")
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "a01_runtime_benchmark.py"),
        "--selection",
        str(selection_path),
        "--runtime-commands",
        str(runtime_commands_path),
        "--workspace",
        str(workspace),
        "--prompt",
        A01_BENCHMARK["prompt"],
        "--out",
        str(out_path),
        "--timeout",
        "180",
    ]
    try:
        rc = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False).returncode
    except OSError as exc:
        io.show(f"[!] {exc}")
        return {
            "status": "benchmark_failed",
            "reason": str(exc),
            "measured": False,
            "resolution": resolution,
        }

    if rc != 0 or not out_path.exists():
        _show_multiline(io, tr("benchmark_failed"), prefix="[!] ")
        return {
            "status": "benchmark_failed",
            "returncode": rc,
            "out": str(out_path.relative_to(REPO_ROOT)),
            "measured": False,
            "resolution": resolution,
        }

    try:
        payload = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _show_multiline(io, tr("benchmark_failed"), prefix="[!] ")
        return {
            "status": "benchmark_failed",
            "reason": str(exc),
            "measured": False,
            "resolution": resolution,
        }

    evidence = payload.get("evidence") or {}
    rb = evidence.get("runtime_benchmark") or {}
    execution_id = rb.get("execution_id")
    measured = rb.get("measurement_status") == "measured"
    io.show("")
    _show_multiline(io, tr("benchmark_completed"), prefix="[✓] ")
    if execution_id:
        io.show(f"  execution_id: {execution_id}")
    if rb.get("wall_seconds") is not None:
        io.show(f"  wall_seconds: {rb.get('wall_seconds')}")
    if rb.get("measured_tps") is not None:
        io.show(f"  measured_tps: {rb.get('measured_tps')}")
    if rb.get("grader_pass") is not None:
        io.show(f"  grader_pass: {rb.get('grader_pass')}")
    io.show(f"  evidence: {out_path.relative_to(REPO_ROOT)}")
    return {
        "status": "benchmark_completed" if measured else "benchmark_failed",
        "returncode": rc,
        "out": str(out_path.relative_to(REPO_ROOT)),
        "execution_id": execution_id,
        "runtime_benchmark": rb,
        "measured": measured,
        "resolution": resolution,
    }


def _benchmark_gate(
    io: WizardIO,
    session: BetaSession,
    *,
    model_choice: dict[str, Any],
    hardware: dict[str, Any],
) -> None:
    model_id = str(model_choice.get("model_id") or model_choice.get("name") or "unknown")
    _show_a01_explanation(io, model_id)
    resolution = _resolve_for_benchmark(model_choice)
    session.data["model_runtime_resolution"] = resolution

    if resolution["status"] != "RESOLVED":
        _show_multiline(io, tr("runtime_unresolved"), prefix="[!] ")
        if resolution.get("reason"):
            io.show(f"  [i] {resolution['reason']}")
        session.block(
            "MODEL_RUNTIME_UNRESOLVED",
            resolution.get("reason") or "model_runtime_unresolved",
        )
        return

    runtime_id = resolution["runtime_id"]
    io.show(f"  • resolved_runtime: {runtime_id}")
    io.show(f"  • model_format: {resolution.get('model_format')}")
    io.show(f"  • runtime_model_ref: {resolution.get('runtime_model_ref')}")

    if runtime_id == "llama.cpp":
        available, detail = _llama_available()
        session.data["benchmark_preflight"] = {
            "runtime": "llama.cpp",
            "available": available,
            "model_id": model_id,
            "model_available": available,
            "reason": None if available else detail,
            "runtime_command": detail,
        }
        if not available:
            _show_multiline(io, tr("benchmark_need_llamacpp"), prefix="[!] ")
            io.show(f"  [i] {detail}")
            session.block("A01_RUNTIME_UNAVAILABLE", detail)
            return
    elif runtime_id == "ollama":
        preflight = check_ollama_model(model_id)
        session.data["benchmark_preflight"] = {
            "runtime": preflight.runtime,
            "available": preflight.available,
            "model_id": preflight.model_id,
            "model_available": preflight.model_available,
            "reason": preflight.reason,
            "installed_models": list(preflight.installed_models),
        }
        if not preflight.available or not preflight.model_available:
            _show_multiline(io, tr("benchmark_need_ollama"), prefix="[!] ")
            if preflight.reason:
                io.show(f"  [i] {preflight.reason}")
            session.block(
                "A01_RUNTIME_UNAVAILABLE",
                preflight.reason or "model_not_available",
            )
            return
    else:
        reason = (
            f"runtime {runtime_id} is resolved for this model, "
            "but A01 has no executable adapter yet"
        )
        _show_multiline(io, tr("runtime_adapter_pending"), prefix="[!] ")
        io.show(f"  [i] {reason}")
        session.block("A01_RUNTIME_ADAPTER_PENDING", reason)
        return

    choice = _choose(
        io,
        tr("benchmark_consent"),
        (tr("benchmark_run_yes"), tr("benchmark_run_no")),
    )
    session.request_benchmark_consent(dict(A01_BENCHMARK, model_id=model_id))
    if choice == tr("benchmark_run_no"):
        session.decline_benchmark()
        _show_multiline(io, tr("benchmark_declined"), prefix="[i] ")
        return

    session.authorize_benchmark()
    _show_multiline(io, tr("benchmark_authorized"), prefix="[✓] ")
    result = _run_a01(
        io,
        model_choice=model_choice,
        hardware=hardware,
        resolution=resolution,
    )
    session.data["benchmark_result"] = result
    if result.get("measured") and result.get("execution_id"):
        session.complete(str(result["execution_id"]))
    elif result.get("status") == "benchmark_blocked":
        session.block(
            "A01_RUNTIME_UNAVAILABLE",
            result.get("reason") or tr("benchmark_need_ollama"),
        )
    else:
        session.block("A01_FAILED", result.get("reason") or tr("benchmark_failed"))


def run_wizard(io: WizardIO | None = None) -> BetaSession:
    io = io or WizardIO()
    session = BetaSession()
    io.show(BANNER)
    language = _choose_language(io)
    session.data["ui_language"] = language
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
    labels = tuple(
        f"{c['name']} · fit={c['fit']} · ~{c['estimated_tps']} tok/s · {c['source']} · ESTIMATED"
        for c in candidates
    )
    if not labels:
        session.block("NO_MODEL_CANDIDATES", tr("no_model_candidates"))
        return session

    chosen_label = _choose(io, tr("choose_model"), labels)
    chosen = candidates[labels.index(chosen_label)]
    session.advance("MODEL_SELECTED", model_choice=chosen)
    for name in STACKS:
        _show_stack(io, name)
    stack_labels = _stack_choice_labels()
    chosen_stack_label = _choose(io, tr("choose_stack"), stack_labels)
    stack_name = list(STACKS.keys())[stack_labels.index(chosen_stack_label)]
    stack = STACKS[stack_name]
    plan = to_selection_plan(
        chosen,
        hardware,
        {"name": stack["name"], "adapter": stack["adapter"], "mode": stack["mode"]},
    )
    session.advance(
        "STACK_SELECTED",
        stack=stack,
        stack_selection=stack,
        selection_plan=plan,
    )
    _show_multiline(io, tr("selected"), prefix=f"[✓] {stack_name} / ")
    session.advance("CONSENT_REQUIRED", installation={"status": "plan_ready"})
    install = _choose(io, tr("install_consent"), (tr("authorize"), tr("cancel")))
    if install == tr("cancel"):
        session.block("INSTALL_DECLINED", tr("install_blocked"))
        return session
    session.authorize_installation()

    model_name = str(chosen.get("name") or chosen.get("model_id") or "unknown")
    _show_decision_summary(
        io,
        model_name=model_name,
        stack_name=stack_name,
        stack=stack,
    )
    install_result = _maybe_run_installer(io, stack)
    session.data["installation"] = {
        "status": "INSTALLING",
        "consent": "granted",
        "stack": stack["name"],
        "installer": install_result,
    }

    verification = _run_physical_verification(io, stack["name"])
    session.data["installation"]["verification"] = verification
    if verification.get("real_installation") is not True:
        session.block(
            "PHYSICAL_VERIFY_FAILED",
            verification.get("message") or tr("verify_fail"),
        )
        return session

    session.installation_verified(
        {
            "status": verification.get("status"),
            "real_installation": True,
            "stack": stack["name"],
            "checks": verification.get("checks"),
            "observed": verification.get("observed"),
            "message": verification.get("message"),
        }
    )
    _benchmark_gate(io, session, model_choice=chosen, hardware=hardware)
    return session


def _non_interactive_smoke() -> bool:
    session = BetaSession()
    session.advance("HARDWARE_READY", hardware={"source": "smoke"})
    session.advance("MODEL_SELECTED", model_choice={"model_id": "smoke-model"})
    session.advance(
        "STACK_SELECTED",
        stack={"name": "ods", "adapter": "ods.v1", "mode": "local-stack"},
    )
    session.advance("CONSENT_REQUIRED", installation={"status": "plan_ready"})
    session.authorize_installation()
    try:
        session.installation_verified(
            {"status": "fixture_verified", "real_installation": False}
        )
    except RuntimeError:
        return session.state == "INSTALLING"
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEONES RC2 beta wizard")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="verify authorization gates without physical side effects",
    )
    args = parser.parse_args(argv)
    if args.non_interactive:
        return 0 if _non_interactive_smoke() else 1
    session = run_wizard()
    return 0 if session.state in {"READY_FOR_BENCHMARK", "COMPLETE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
