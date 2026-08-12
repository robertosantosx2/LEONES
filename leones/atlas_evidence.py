"""Small evidence-state helper for Leones Atlas.

One responsibility: define the explicit transition from external information
to Atlas evidence. It never decides whether evidence is true.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    source: str
    evidence_type: str
    source_type: str
    status: str = "external-unvalidated"


def validate_for_atlas(evidence: Evidence, reviewer: str) -> Evidence:
    """Mark an externally reviewed item as Atlas evidence.

    This function requires an explicit reviewer and does not perform automatic
    validation. The caller is responsible for the actual evidence review.
    """
    if not reviewer.strip():
        raise ValueError("A reviewer is required")
    if evidence.status != "external-unvalidated":
        raise ValueError("Only external-unvalidated evidence can enter review")
    return Evidence(
        source=evidence.source,
        evidence_type=evidence.evidence_type,
        source_type=evidence.source_type,
        status="atlas-evidence",
    )
