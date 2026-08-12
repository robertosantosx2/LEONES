"""Print the local hardware profile.

This script has one responsibility: detect basic hardware information and print
it. It does not install software, inspect models, run inference or benchmark.

Optional dependency:
    psutil — used only when available to obtain total RAM.

Example:
    python -m leones.hardware_report
"""

from .hardware import HardwareProfiler


def main() -> None:
    """Detect hardware and print a small human-readable report."""
    snapshot = HardwareProfiler().profile()
    profile = snapshot.profile
    print(f"cpu: {profile.cpu}")
    print(f"architecture: {profile.architecture or 'unknown'}")
    print(f"ram_gb: {profile.ram_gb:g}")
    print(f"cpu_count: {snapshot.cpu_count}")
    print(f"os: {profile.os or 'unknown'}")
    print(f"capabilities: {','.join(profile.capabilities) or 'none'}")


if __name__ == "__main__":
    main()
