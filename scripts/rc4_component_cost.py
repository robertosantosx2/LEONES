#!/usr/bin/env python3
"""RC4/UI — disk / RAM / residency cost disclosure before install.

Figures are ESTIMATED product guidance unless measured on the host.
UNKNOWN is required when a value is not known — never invent numbers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ComponentCost:
    component_id: str
    display_name: str
    disk_approx: str
    ram_when_running_approx: str
    idle_resident: str
    starts_at_login: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = "ESTIMATED_COST"
        return d


COST_CATALOG: dict[str, ComponentCost] = {
    "fitllm": ComponentCost(
        component_id="fitllm",
        display_name="FitLLM / LLMFit",
        disk_approx="UNKNOWN (paquete CLI + deps Python; suele ser cientos de MB)",
        ram_when_running_approx="UNKNOWN (proceso puntual de recomendación; no daemon por defecto)",
        idle_resident="nada residente esperado si no se deja un servicio propio",
        starts_at_login="no",
        notes="Recomendador ESTIMATED. Opcional en RC4. Desinstalable.",
    ),
    "hermes": ComponentCost(
        component_id="hermes",
        display_name="Hermes Agent",
        disk_approx="UNKNOWN (árbol git + deps; a menudo >500 MB)",
        ram_when_running_approx="UNKNOWN (agente en uso; depende modelos/tools)",
        idle_resident="posible estado en ~/.hermes; sin servicio LEONES por defecto",
        starts_at_login="no",
        notes="Opcional. No selector de modelo RC4. Desinstalable.",
    ),
    "omh": ComponentCost(
        component_id="omh",
        display_name="Oh My Hermes (OMH)",
        disk_approx="UNKNOWN",
        ram_when_running_approx="UNKNOWN",
        idle_resident="UNKNOWN (puede coordinar herramientas sobre Hermes)",
        starts_at_login="UNKNOWN",
        notes="Opcional. No selector RC4. Desinstalable.",
    ),
    "magnitude": ComponentCost(
        component_id="magnitude",
        display_name="Magnitude",
        disk_approx="UNKNOWN (CLI npm + releases bajo ~/.magnitude)",
        ram_when_running_approx="UNKNOWN (motor de inferencia + modelo cargado)",
        idle_resident="si el servicio está Up: proceso en background (p. ej. puerto local); distinto de parado",
        starts_at_login="según `magnitude service install` (sí/no)",
        notes="Stack de ejecución. Desinstalable. Servicio puede quedar residente hasta stop/uninstall.",
    ),
    "ods": ComponentCost(
        component_id="ods",
        display_name="ODS",
        disk_approx="UNKNOWN (clon + imágenes Docker; puede ser varios GB)",
        ram_when_running_approx="UNKNOWN (suma de contenedores activos)",
        idle_resident="contenedores Up consumen RAM aunque no haya chat; `docker stop` / `ods down` para reposo real",
        starts_at_login="no por defecto LEONES; depende del host",
        notes="Stack de ejecución. Desinstalable (CLI, compose, volúmenes opcionales).",
    ),
}


def get_cost(component_id: str) -> ComponentCost | None:
    return COST_CATALOG.get(component_id.lower())


def render_cost_block(cost: ComponentCost, *, lang: str = "es") -> str:
    title = {"es": "COSTE", "en": "COST", "zh": "成本", "ja": "コスト"}.get(lang, "COSTE")
    lines = [
        f"┌─ {title} · {cost.display_name} ─────────────────────",
        f"│ Disco (aprox.):     {cost.disk_approx}",
        f"│ RAM en ejecución:   {cost.ram_when_running_approx}",
        f"│ En reposo:          {cost.idle_resident}",
        f"│ Arranque al login:  {cost.starts_at_login}",
    ]
    if cost.notes:
        lines.append(f"│ Nota:               {cost.notes}")
    lines.append("└───────────────────────────────────────────────────")
    return "\n".join(lines)


def install_prompt_lines(component_id: str, *, lang: str = "es") -> list[str]:
    cost = get_cost(component_id)
    if cost is None:
        return [
            f"UNKNOWN cost catalog entry for {component_id}",
            "No se instala hasta declarar disco/RAM/residencia o UNKNOWN explícito.",
        ]
    block = render_cost_block(cost, lang=lang)
    ask = {
        "es": f"¿Instalar {cost.display_name}? [s/N]",
        "en": f"Install {cost.display_name}? [y/N]",
        "zh": f"是否安装 {cost.display_name}? [y/N]",
        "ja": f"{cost.display_name} をインストールしますか? [y/N]",
    }.get(lang, f"¿Instalar {cost.display_name}? [s/N]")
    return [block, ask]


def uninstall_prompt_lines(component_id: str, *, lang: str = "es") -> list[str]:
    cost = get_cost(component_id)
    name = cost.display_name if cost else component_id
    return [
        {
            "es": f"¿Desinstalar {name}? [s/N]  (no borra evidencia LEONES)",
            "en": f"Uninstall {name}? [y/N]  (does not delete LEONES evidence)",
            "zh": f"是否卸载 {name}? [y/N]（不删除 LEONES 证据）",
            "ja": f"{name} をアンインストールしますか? [y/N]（LEONES の証拠は削除しません）",
        }.get(lang, f"¿Desinstalar {name}? [s/N]"),
    ]
