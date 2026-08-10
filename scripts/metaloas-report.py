#!/usr/bin/env python3
"""Generate a privacy-conscious metaLOAS Markdown report.

Collects basic machine/software facts automatically and deliberately avoids
personal identifiers such as username, hostname, MAC/IP, serials and paths.
The resulting Markdown is intended to be reviewed before publication.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout)
        return p.stdout.strip()
    except Exception:
        return ""


def first_line(s: str) -> str:
    return s.splitlines()[0].strip() if s else ""


def mem_gb() -> str:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        return f"{pages * size / (1024**3):.1f} GB"
    except Exception:
        return "No disponible"


def cpu_model() -> str:
    text = Path("/proc/cpuinfo").read_text(errors="ignore") if Path("/proc/cpuinfo").exists() else ""
    for line in text.splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "No disponible"


def os_info() -> tuple[str, str]:
    pretty = ""
    version = ""
    if Path("/etc/os-release").exists():
        data = {}
        for line in Path("/etc/os-release").read_text(errors="ignore").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k] = v.strip().strip('"')
        pretty = data.get("PRETTY_NAME", data.get("NAME", ""))
        version = data.get("VERSION_ID", "")
    return pretty or platform.system(), version


def gpu_info() -> list[str]:
    out = []
    nvidia = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    if nvidia:
        for line in nvidia.splitlines():
            out.append(f"NVIDIA: {line.strip()}")
    lspci = run(["lspci"])
    for line in lspci.splitlines():
        if re.search(r"VGA compatible controller|3D controller|Display controller", line, re.I):
            # Strip PCI bus/address to avoid unnecessary machine fingerprinting.
            out.append(re.sub(r"^[0-9a-f:. -]+(?:VGA compatible controller|3D controller|Display controller):\s*", "", line, flags=re.I).strip())
    return list(dict.fromkeys(out)) or ["No GPU detectada / no disponible"]


def git_rev(path: str) -> str:
    if not Path(path).exists():
        return "No disponible"
    value = run(["git", "-C", path, "rev-parse", "HEAD"])
    return value[:12] if value else "No disponible"


def command_version(cmd: list[str]) -> str:
    return first_line(run(cmd)) or "No disponible"


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera un informe metaLOAS sin datos personales")
    ap.add_argument("--output", default="results/metaLOAS/auto-report.md")
    ap.add_argument("--llama-cpp", default="llama.cpp")
    ap.add_argument("--buddy", default="buddy")
    ap.add_argument("--model", default="", help="Ruta al modelo; solo se registra nombre y SHA-256")
    args = ap.parse_args()

    os_name, os_version = os_info()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    llama_rev = git_rev(args.llama_cpp)
    buddy_rev = git_rev(args.buddy)
    llama_server = Path(args.llama_cpp) / "build/bin/llama-server"
    llama_bench = Path(args.llama_cpp) / "build/bin/llama-bench"

    model_name = Path(args.model).name if args.model else "No indicado"
    model_sha = "No indicado"
    if args.model and Path(args.model).is_file():
        import hashlib
        h = hashlib.sha256()
        with open(args.model, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        model_sha = h.hexdigest()

    gpu = gpu_info()
    lines = [
        "# metaLOAS — Informe automático", "",
        "> Generado automáticamente. **Revisar antes de publicar.** Este informe está diseñado para excluir datos personales.", "",
        f"- Fecha de captura: {now}",
        "- Perfil LOAS: pendiente de clasificar (H0/H1/H2/H3)",
        f"- Sistema: {os_name} {os_version}".strip(),
        f"- Kernel: {platform.release()}",
        f"- Arquitectura: {platform.machine()}",
        f"- CPU: {cpu_model()}",
        f"- RAM: {mem_gb()}",
        "- GPU: " + "; ".join(gpu),
        "",
        "## Software", "",
        f"- Python: {platform.python_version()}",
        f"- Git: {command_version(['git', '--version'])}",
        f"- llama.cpp commit: `{llama_rev}`",
        f"- llama-server presente: {'sí' if llama_server.is_file() else 'no'}",
        f"- llama-bench presente: {'sí' if llama_bench.is_file() else 'no'}",
        f"- Buddy commit: `{buddy_rev}`",
        "",
        "## Modelo", "",
        f"- Fichero/modelo: `{model_name}`",
        f"- SHA-256: `{model_sha}`",
        "- Cuantización: completar si no está indicada en el nombre del modelo",
        "",
        "## LOTB", "",
        "- B01: pendiente",
        "- B02: pendiente",
        "- B03: pendiente",
        "- B04: pendiente",
        "- B05: pendiente",
        "- Resultado agentivo: pendiente",
        "",
        "## metaLOAS — revisión humana", "",
        "- ¿Se han eliminado rutas, nombres de usuario, hostname, seriales, UUID, MAC/IP y otros identificadores? Sí / No",
        "- ¿Se ha verificado el modelo y SHA-256? Sí / No",
        "- ¿Se han anotado los commits exactos utilizados? Sí / No",
        "- Observaciones: ",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Informe metaLOAS creado: {out}")
    print("IMPORTANTE: revisa el Markdown antes de publicarlo.")


if __name__ == "__main__":
    main()
