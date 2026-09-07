"""RC4 common progress contract for installation and uninstallation operations.

Installers must expose activity continuously.  When a determinate total is
available, callers should provide current/total (and optionally bytes, rate
and ETA).  When it is not available, phase/activity still MUST be emitted;
a silent or apparently frozen operation is not conformant.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OperationPhase(str, Enum):
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    REMOVING = "removing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class OperationProgress:
    """A renderable, transport-neutral progress snapshot."""

    operation: str
    phase: OperationPhase
    current: Optional[int] = None
    total: Optional[int] = None
    current_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    rate_bytes_per_second: Optional[float] = None
    eta_seconds: Optional[float] = None
    detail: Optional[str] = None

    def __post_init__(self) -> None:
        if self.current is not None and self.current < 0:
            raise ValueError("current must be >= 0")
        if self.total is not None and self.total <= 0:
            raise ValueError("total must be > 0")
        if self.current is not None and self.total is not None and self.current > self.total:
            raise ValueError("current cannot exceed total")
        if self.current_bytes is not None and self.current_bytes < 0:
            raise ValueError("current_bytes must be >= 0")
        if self.total_bytes is not None and self.total_bytes <= 0:
            raise ValueError("total_bytes must be > 0")
        if self.current_bytes is not None and self.total_bytes is not None and self.current_bytes > self.total_bytes:
            raise ValueError("current_bytes cannot exceed total_bytes")

    @property
    def determinate(self) -> bool:
        return (
            self.current is not None
            and self.total is not None
            or self.current_bytes is not None
            and self.total_bytes is not None
        )

    @property
    def percent(self) -> Optional[float]:
        if self.current is not None and self.total:
            return self.current * 100.0 / self.total
        if self.current_bytes is not None and self.total_bytes:
            return self.current_bytes * 100.0 / self.total_bytes
        return None

    @property
    def active(self) -> bool:
        return self.phase not in {OperationPhase.COMPLETED, OperationPhase.FAILED}

    def render(self) -> str:
        """Return the minimum visible status required by the RC4 contract."""
        label = self.phase.value
        if self.percent is not None:
            status = f"{self.percent:5.1f}%"
            if self.current is not None and self.total is not None:
                status += f" ({self.current}/{self.total})"
            elif self.current_bytes is not None and self.total_bytes is not None:
                status += f" ({self.current_bytes}/{self.total_bytes} bytes)"
        else:
            status = "…"  # indeterminate activity indicator
        extras = []
        if self.rate_bytes_per_second is not None:
            extras.append(f"{self.rate_bytes_per_second:.0f} B/s")
        if self.eta_seconds is not None:
            extras.append(f"ETA {self.eta_seconds:.0f}s")
        if self.detail:
            extras.append(self.detail)
        suffix = " — " + " · ".join(extras) if extras else ""
        return f"[{self.operation}] {label} {status}{suffix}"


def terminal_progress(operation: str, success: bool, detail: str | None = None) -> OperationProgress:
    """Build the mandatory explicit terminal state."""
    return OperationProgress(
        operation=operation,
        phase=OperationPhase.COMPLETED if success else OperationPhase.FAILED,
        detail=detail,
    )
