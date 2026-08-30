#!/usr/bin/env python3
"""🦁 LEONES privacy gate — revisión local antes de compartir.

ANTES: explica que va a inspeccionar un fichero y qué NO puede garantizar.
DURANTE: busca patrones frecuentes de secretos, identificadores y rutas.
DESPUÉS: devuelve clear/blocked y los hallazgos. No modifica, borra ni publica.

Importante: «clear» solo significa «no encontré patrones conocidos». Siempre
requiere revisión humana antes de publicar.
"""

from __future__ import annotations
import argparse, json, re
from pathlib import Path

PATTERNS = {
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "token": r"(?i)\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]+",
    "secret_field": r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s`]+",
    "home_path": r"(?:/(?:home|Users)/[^\s`]+|[A-Za-z]:\\Users\\[^\s`]+)",
    "mac": r"\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b",
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "windows_username": r"(?i)\b(?:C:)?\\Users\\[^\\\s]+",
}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Revisa un resultado LEONES antes de compartirlo"
    )
    p.add_argument("report")
    p.add_argument("--explain", action="store_true")
    a = p.parse_args()
    if a.explain or True:
        print(
            "🦁 LEONES · Puerta de privacidad\nVoy a buscar patrones habituales de datos personales, identificadores y secretos. No modificaré ni publicaré el fichero.\nUn OK no demuestra anonimato: todavía debes revisar el documento.\n"
        )
    try:
        text = Path(a.report).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"No se pudo leer el fichero: {exc}")
        return 2
    findings = [name for name, pattern in PATTERNS.items() if re.search(pattern, text)]
    status = "blocked" if findings else "clear"
    out = {
        "schema_version": "1.0",
        "tool": "leones-privacy",
        "tool_version": "1.1",
        "status": status,
        "findings": findings,
        "limits": [
            "pattern-based check only",
            "manual review still required",
            "absence of findings is not proof of anonymity",
        ],
        "next_step": "Revisar manualmente y continuar con publish"
        if not findings
        else "Eliminar/revisar los hallazgos antes de compartir",
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if findings:
        print("\n⛔ No publiques todavía. Revisa los hallazgos anteriores.")
        return 2
    print(
        "\n✅ No se detectaron patrones conocidos. Revisa igualmente el contenido completo antes de publicar."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
