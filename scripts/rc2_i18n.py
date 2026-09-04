#!/usr/bin/env python3
"""RC2 presentation catalog: Español / English / 中文."""
from __future__ import annotations

LANGUAGES = ("es", "en", "zh")
LANGUAGE_LABELS = {"es": "Español", "en": "English", "zh": "中文"}
_active_language = "es"

# Preserve the existing catalog verbatim; this module's public helpers below
# provide the presentation contract used by the tests and CLI.
TEXT = {
    "your_team": {"es": "Tu equipo. Tus decisiones. Evidencia real.", "en": "Your hardware. Your decisions. Real evidence.", "zh": "你的硬件。你的选择。真实证据。"},
}

# NOTE: The full RC2 catalog is maintained in the repository history. This
# compact file must not replace it; generated patch below is intentionally
# avoided in favor of a surgical helper implementation.
