"""V1.1 runtime registry and capability contract."""

from .registry import RuntimeDescriptor, RuntimeRegistry, build_default_registry
from .contract import RuntimeSelectionRequest, RuntimeSelectionPlan, CapabilityMatch

__all__ = [
    "CapabilityMatch",
    "RuntimeDescriptor",
    "RuntimeRegistry",
    "RuntimeSelectionPlan",
    "RuntimeSelectionRequest",
    "build_default_registry",
]
