"""Prepare external estimates for human review before Atlas promotion.

One responsibility: copy an external estimate into an explicit review queue.
It never promotes an item to Atlas and never changes its evidence status.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalEstimate:
    model_id: str
    metric: str
    value: str
    source: str
    evidence_type: str = "estimated"
    source_type: str = "other"
    status: str = "external-unvalidated"


def prepare_for_review(item: ExternalEstimate) -> dict[str, str]:
    """Return a review record without promoting the external claim."""
    return {
        "model_id": item.model_id,
        "metric": item.metric,
        "value": item.value,
        "source": item.source,
        "evidence_type": item.evidence_type,
        "source_type": item.source_type,
        "status": "external-unvalidated",
    }
