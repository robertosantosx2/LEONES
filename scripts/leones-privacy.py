#!/usr/bin/env python3
"""LEONES privacy gate for a report.

ANTES: responde «¿qué datos sospechosos contiene este fichero antes de compartirlo?».
No borra ni publica nada automáticamente.

DURANTE: analiza texto local con patrones conservadores.

DESPUÉS: muestra hallazgos y límites. «OK» significa «no encontré patrones
conocidos», nunca «se ha demostrado que sea anónimo».
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
PATTERNS={
 "private_key":r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
 "email":r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
 "token":r"(?i)\b(?:ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]+",
 "secret_field":r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s`]+",
 "home_path":r"(?:/(?:home|Users)/[^\s`]+|[A-Za-z]:\\Users\\[^\s`]+)",
 "mac":r"\b(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}\b",
 "ipv4":r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
}
def main()->int:
 p=argparse.ArgumentParser(description="Revisión local de privacidad antes de compartir un resultado LEONES")
 p.add_argument("report"); p.add_argument("--explain",action="store_true")
 a=p.parse_args(); text=Path(a.report).read_text(encoding="utf-8",errors="replace")
 if a.explain: print("🦁 LEONES · Puerta de privacidad\nEsto NO publica nada. Busca patrones frecuentes de datos personales o secretos antes de compartir.\n")
 findings=[name for name,pattern in PATTERNS.items() if re.search(pattern,text)]
 out={"tool":"leones-privacy","tool_version":"1.0","status":"blocked" if findings else "clear","findings":findings,"limits":["pattern-based check only","manual review still required"]}
 print(json.dumps(out,indent=2,ensure_ascii=False)); return 2 if findings else 0
if __name__=="__main__": raise SystemExit(main())
