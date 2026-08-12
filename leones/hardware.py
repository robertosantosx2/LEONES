"""Hardware Intelligence: detect and normalize the local execution profile."""

from dataclasses import dataclass
import os
import platform

from .core.contracts import HardwareProfile


@dataclass(frozen=True)
class HardwareSnapshot:
    profile: HardwareProfile
    cpu_count: int
    ram_available_gb: float | None = None


class HardwareProfiler:
    """Portable baseline profiler; platform-specific probes plug in later."""

    def profile(self, ram_gb: float | None = None) -> HardwareSnapshot:
        if ram_gb is None:
            ram_gb = self._detect_ram_gb() or 0.0

        profile = HardwareProfile(
            cpu=platform.processor() or platform.machine() or "unknown",
            ram_gb=ram_gb,
            os=platform.system().lower(),
            architecture=platform.machine(),
            capabilities=self._cpu_capabilities(),
        )
        return HardwareSnapshot(profile=profile, cpu_count=os.cpu_count() or 1)

    @staticmethod
    def _detect_ram_gb() -> float | None:
        try:
            import psutil  # optional dependency
            return round(psutil.virtual_memory().total / (1024**3), 2)
        except ImportError:
            return None

    @staticmethod
    def _cpu_capabilities() -> tuple[str, ...]:
        caps: list[str] = []
        if platform.machine():
            caps.append(platform.machine().lower())
        return tuple(caps)
