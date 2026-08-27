#!/usr/bin/env python3
"""ADIVINO: descubre nuevas fuentes potenciales para LEONES.

ADIVINO no incorpora nada al Atlas por sí mismo. Su trabajo es encontrar
fuentes nuevas (webs, repositorios, datasets, benchmarks, runtimes, skills,
agentes, etc.), eliminar duplicados y producir candidatos para revisión humana.

La aprobación humana es explícita: solo una respuesta "OK LEONES" puede pasar
un candidato aprobado a la siguiente etapa del pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class Discovery:
    """Una fuente candidata descubierta por ADIVINO."""

    name: str
    url: str
    source_type: str
    reason: str
    discovered_at: str
    discovery_id: str
    status: str = "pending_human"


def canonical_url(url: str) -> str:
    """Normaliza una URL para poder detectar la misma fuente con variantes."""
    parts = urlsplit(url.strip())
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", "")
    )


def make_id(url: str) -> str:
    """Crea un identificador estable a partir de la URL canónica."""
    return sha256(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def build_discovery(name: str, url: str, source_type: str, reason: str) -> Discovery:
    """Construye un candidato sin marcarlo como aprobado."""
    return Discovery(
        name=name,
        url=canonical_url(url),
        source_type=source_type,
        reason=reason,
        discovered_at=datetime.now(timezone.utc).isoformat(),
        discovery_id=make_id(url),
    )


def write_staging(discoveries: list[Discovery], output: Path) -> None:
    """Guarda candidatos en staging; nunca escribe directamente en el Atlas."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for discovery in discoveries:
            handle.write(json.dumps(asdict(discovery), ensure_ascii=False) + "\n")


def approved_by_reply(text: str) -> bool:
    """Reconoce únicamente la orden humana exacta 'OK LEONES'."""
    return text.strip().upper() == "OK LEONES"


if __name__ == "__main__":
    raise SystemExit(
        "ADIVINO es una librería/pipeline: úsalo desde el adaptador de descubrimiento."
    )
