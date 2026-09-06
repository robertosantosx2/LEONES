#!/usr/bin/env python3
"""RC4 — install/uninstall pairing for optional components.

Problem
    Optional components (FitLLM, Magnitude, ODS) must always expose a matched
    uninstall path so RC4 never leaves silent permanent residents.

Inputs
    component_id in {fitllm, magnitude, ods}
    stack label for the post-install FitLLM removal offer

Outputs
    assert_install_uninstall_pair() raises if the component is undeclared
    post_stack_fitllm_uninstall_offer() returns an opt-in offer payload

What this module does NOT do
    Perform install/uninstall. It only encodes the contract: every installable
    component has a removal path; FitLLM removal after Magnitude/ODS is opt-in.
"""
from __future__ import annotations

from typing import Iterable

INSTALLABLE_COMPONENTS: tuple[str, ...] = (
    "fitllm",
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
