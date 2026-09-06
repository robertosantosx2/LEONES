#!/usr/bin/env python3
"""RC4 — install/uninstall pairing contract for optional components."""
from __future__ import annotations

from typing import Iterable

INSTALLABLE_COMPONENTS: tuple[str, ...] = (
    "fitllm",
    "hermes",
    "omh",
    "magnitude",
    "ods",
)


def assert_install_uninstall_pair(component_id: str) -> None:
    if component_id not in INSTALLABLE_COMPONENTS:
        raise ValueError(
            f"{component_id} is not a declared installable component; "
            "add it to INSTALLABLE_COMPONENTS with uninstall path"
        )


def all_installable() -> tuple[str, ...]:
    return INSTALLABLE_COMPONENTS


def post_stack_fitllm_uninstall_offer(*, stack: str) -> dict:
    """After Magnitude/ODS install, offer FitLLM removal (opt-in)."""
    stack_l = stack.lower().strip()
    if stack_l not in {"magnitude", "ods", "both"}:
        raise ValueError("stack must be magnitude|ods|both")
    return {
        "schema": "leones.rc4.post_stack_fitllm_uninstall_offer.v1",
        "stack": stack_l,
        "offer_uninstall": "fitllm",
        "opt_in_required": True,
        "silent_uninstall_forbidden": True,
        "preserves_leones_evidence": True,
        "message_es": (
            "FitLLM ya no es necesario para el camino de ejecución. "
            "¿Desinstalar FitLLM ahora? [s/N]"
        ),
    }


def components_with_lifecycle() -> Iterable[str]:
    return INSTALLABLE_COMPONENTS
