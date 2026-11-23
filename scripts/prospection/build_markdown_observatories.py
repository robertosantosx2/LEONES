#!/usr/bin/env python3
"""Generate all public LEONES observatory pages as Markdown.

JSON/NDJSON remain internal pipeline interchange under data/; publication is Markdown only.
"""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/observatory"
WEB = ROOT / "web"

def load(path):
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def esc(value):
    return str("—" if value is None else value).replace("|", "\\|").replace("\n", " ").strip()

def link(label, url):
    return f"[{esc(label)}]({url})" if url and str(url).startswith(("https://", "http://")) else esc(label)

def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(esc(v) for v in row) + " |" for row in rows]
    return "\n".join(out)

def discovery_page(feed):
    items = feed.get("items", [])
    groups = defaultdict(list)
    for x in items:
        groups[str(x.get("type") or "Sin clasificar")].append(x)
    lines = ["# LEONES — Discovery Atlas", "", f"> Generado: {feed.get('generated_at', 'sin fecha')} · {len(items)} hallazgos",
             "", "**Descubierto ≠ aprobado ≠ recomendado ≠ ejecutado ≠ medido.** Los metadatos y licencias son declaraciones de las fuentes; requieren revisión independiente.",
             "", "Catálogo de software, modelos, runtimes, hardware y publicaciones procedentes de la prospección federada.", ""]
    for category in sorted(groups, key=str.casefold):
        lines += [f"## {category}", "", table(["Proyecto", "Descripción", "Licencia declarada", "Fuente", "Estado"], [
            (link(x.get("name") or x.get("repository") or "Sin nombre", x.get("url")),
             x.get("description"), x.get("license"), x.get("source"), x.get("status") or "pending")
            for x in groups[category]
        ]), ""]
    lines += ["## Gobernanza", "", "- Los resultados automáticos permanecen pendientes de revisión.",
              "- No se ejecuta, instala, recomienda ni integra software descubierto.",
              "- Una licencia detectada no equivale a auditoría legal.",
              "- Las cifras de terceros no son mediciones LEONES.",
              "", "Fuentes: [workflow diario](../.github/workflows/daily-prospection.yml) · [política de prospección](../docs/PROSPECTION_LICENSE_POLICY.md)."]
    return "\n".join(lines) + "\n"

def agent_page(feed):
    items = feed.get("items", [])
    lines = ["# LEONES — Agent Use Case Observatory", "", f"> Generado: {feed.get('generated_at', 'sin fecha')} · {len(items)} candidatos", "",
             "**Descubierto ≠ aprobado.** La puntuación heurística y la presencia de README/ejemplos son señales de triaje, no validación funcional.", ""]
    groups = defaultdict(list)
    for x in items: groups[str(x.get("category") or "Agent")].append(x)
    for category in sorted(groups, key=str.casefold):
        lines += [f"## {category}", "", table(["Repositorio", "Descripción", "Licencia", "Stars", "Último push", "Reproducibilidad (heurística)", "Revisión"], [
            (link(x.get("name") or "Sin nombre", x.get("url")), x.get("description"), x.get("license"),
             x.get("stars"), x.get("pushed_at"), x.get("reproducibility_score"), x.get("review_status") or "pending")
            for x in groups[category]
        ]), ""]
    lines += ["## Criterios de lectura", "", "- pending/discovered: no revisado o no reproducido.",
              "- La licencia es metadato declarado por GitHub, no dictamen jurídico.",
              "- reproducibility_score es una heurística basada en señales textuales; no es resultado de ejecución.",
              "- Ningún candidato recibe verified por automatización.", ""]
    return "\n".join(lines) + "\n"

def mobile_page(feed):
    items = feed.get("items", [])
    lines = ["# Mobile-LLMs-ARM — observatorio", "", f"> Generado: {feed.get('generated_at', 'sin fecha')} · {len(items)} entradas", "",
             "Investigación de LLMs e IA local en Android, Linux móvil, ARM64 y sistemas embebidos. Los resultados comunitarios son pistas, no evidencia experimental.", ""]
    groups = defaultdict(list)
    for x in items: groups[str(x.get("category") or "Sin clasificar")].append(x)
    for category in sorted(groups, key=str.casefold):
        lines += [f"## {category}", "", table(["Proyecto / fuente", "Descripción", "Plataformas", "Licencia", "Actividad", "Estado"], [
            (link(x.get("name") or "Sin nombre", x.get("url")), x.get("description"),
             ", ".join(x.get("platforms") or []), x.get("license"), x.get("pushed_at") or x.get("created_utc"),
             x.get("status") or "pending_review")
            for x in groups[category]
        ]), ""]
    lines += ["## Búsquedas comunitarias", ""]
    for x in feed.get("social_searches", []): lines.append(f"- {link(x.get('label') or 'Búsqueda', x.get('url'))}")
    lines += ["", "## Gobernanza", "", "- Las APIs pueden fallar o devolver resultados parciales; el informe de ejecución conserva esos errores.",
              "- X se representa mediante enlaces de búsqueda, no mediante scraping no autorizado.",
              "- No se aprueban, recomiendan, instalan ni ejecutan candidatos automáticamente.",
              "- Para estado measured se exige dispositivo, protocolo, versión, modelo/hash y artefactos."]
    return "\n".join(lines) + "\n"

def research_page(feed):
    items = feed.get("items", [])
    groups = defaultdict(list)
    for x in items: groups[str(x.get("category") or "Investigación")].append(x)
    lines = ["# LEONES — Observatorio de investigación", "",
             f"> Generado: {feed.get('generated_at', 'sin fecha')} · {len(items)} líneas · {feed.get('repository', {}).get('tracked_files', '—')} archivos versionados · {feed.get('repository', {}).get('research_readmes', '—')} README de investigación", "",
             "El índice curado Markdown es la fuente de autoridad. Este catálogo se genera a partir de él y de un recorrido recursivo del árbol Git; no altera prioridades ni acepta proyectos.", ""]
    for category in sorted(groups, key=str.casefold):
        lines += [f"## {category}", "", table(["Línea", "Descripción", "Potencial", "Estado documental"], [
            (link(x.get("name") or "Sin nombre", x.get("url")), x.get("description"), x.get("potential"), x.get("status"))
            for x in groups[category]
        ]), ""]
    pending = feed.get("unclassified_readmes", [])
    lines += ["## README detectados pendientes de clasificar", ""]
    lines += [f"- {link(x.get('path'), x.get('url'))}" for x in pending] if pending else ["- Ninguno."]
    lines += ["", "## Fuente y gobernanza", "", "- Fuente curada: [RESEARCH-PROJECTS-INDEX.md](../docs/research/RESEARCH-PROJECTS-INDEX.md).",
              "- La detección recursiva no crea prioridades, no promueve candidatos y no modifica INDEX maestros.",
              "- Descubrimiento documental no equivale a revisión, integración ni validación."]
    return "\n".join(lines) + "\n"

def main():
    feeds = {
        "discovery-atlas.md": (load("data/observatory/prospeccion.json"), discovery_page),
        "agent-use-cases.md": (load("data/observatory/agent-use-cases.json"), agent_page),
        "mobile-llms-arm.md": (load("data/observatory/mobile-llms-arm.json"), mobile_page),
        "investigacion.md": (load("data/observatory/research-projects.json"), research_page),
    }
    WEB.mkdir(parents=True, exist_ok=True)
    for filename, (feed, render) in feeds.items():
        if not feed:
            raise SystemExit(f"Missing observatory source data for {filename}")
        content = render(feed)
        if not content.startswith("# ") or "<html" in content.lower():
            raise SystemExit(f"Invalid Markdown publication: {filename}")
        (WEB / filename).write_text(content, encoding="utf-8")
    generated = max(str(feed.get("generated_at") or "") for feed, _ in feeds.values())
    index = ["# LEONES — Observatorios (Markdown)", "",
        "Publicación canónica en Markdown. GitHub renderiza estos documentos directamente; no se generan páginas HTML autocontenidas ni feeds JSON públicos.", "",
        "- [Prospección](prospeccion.md) — novedades de fuentes y criterios de entrada.",
        "- [Discovery Atlas](discovery-atlas.md) — descubrimientos federados.",
        "- [Agent Use Case Observatory](agent-use-cases.md) — agentes, skills, prompts, MCP y workflows.",
        "- [Mobile-LLMs-ARM](mobile-llms-arm.md) — LLMs móviles y ARM.",
        "- [Investigación LEONES](investigacion.md) — catálogo curado y detección recursiva.",
        "", "## Contrato editorial", "",
        "- Markdown es el único formato de publicación del observatorio.",
        "- JSON/NDJSON se reservan para intercambio interno del pipeline bajo data/.",
        "- Ningún descubrimiento se promociona automáticamente a aprobado, recomendado o medido.",
        "- Las mediciones LEONES deben enlazar protocolo y artefactos reproducibles.",
        "", f"Actualizado: {generated}"]
    (WEB / "observatory.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    prospection = [
        "# LEONES — Prospección",
        "",
        "La prospección descubre repositorios, modelos, runtimes, agentes, técnicas y hardware. La licencia SPDX y las señales automáticas sirven para filtrar y priorizar la revisión; no equivalen a aprobación técnica ni jurídica.",
        "",
        "- [Discovery Atlas](discovery-atlas.md) — catálogo federado y deduplicado.",
        "- [Hallazgos OSI/Copyleft](../research/copyleft-discoveries.md) — candidatos que superan el filtro OSI.",
        "- [Política de licencias](../docs/PROSPECTION_LICENSE_POLICY.md).",
        "- [Workflow diario](../.github/workflows/daily-prospection.yml).",
        "",
        "## Estados",
        "",
        "- Descubierto: hallazgo automático, pendiente de revisión.",
        "- Revisado: inspección humana de fuente, licencia, mantenimiento y dependencias.",
        "- Verificado: ejecución reproducible con versión, hardware y artefactos.",
        "- Medido: benchmark LEONES con protocolo y resultados conservados.",
        "",
        "**Descubrimiento no es recomendación.** No se instalan ni ejecutan candidatos automáticamente.",
    ]
    (WEB / "prospeccion.md").write_text("\n".join(prospection) + "\n", encoding="utf-8")
    print("Generated Markdown observatories:", ", ".join(feeds))
if __name__ == "__main__":
    main()
