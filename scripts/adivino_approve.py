#!/usr/bin/env python3
"""Aplica la aprobación humana de ADIVINO.

La entrada es un candidato en staging y el texto de una respuesta de correo.
Solo ``OK LEONES`` cambia el estado a ``approved``. El script no extrae ni
publica conocimiento: únicamente registra la decisión humana.
"""

from __future__ import annotations

import json
from pathlib import Path

from adivino import approved_by_reply


def approve_staged(input_path: Path, reply_text: str, output_path: Path) -> int:
    """Aprueba las líneas cuyo candidato sigue pendiente y devuelve su número."""
    if not approved_by_reply(reply_text):
        return 0

    approved = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        input_path.open(encoding="utf-8") as source,
        output_path.open("w", encoding="utf-8") as target,
    ):
        for line in source:
            item = json.loads(line)
            if item.get("status") == "pending_human":
                item["status"] = "approved"
                approved += 1
            target.write(json.dumps(item, ensure_ascii=False) + "\n")
    return approved
