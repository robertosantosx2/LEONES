"""Autonomous decision pipeline skeleton for LEONES."""

from dataclasses import dataclass

from .atlas import Atlas
from .core.contracts import HardwareProfile, RouteDecision
from .router import LeonesRouter
from .task import TaskIntelligence


@dataclass
class Decision:
    task_type: str
    hardware: HardwareProfile
    route: RouteDecision


class LeonesEngine:
    """Connect Task Intelligence, Atlas and Router without a backend dependency."""

    def __init__(self, atlas: Atlas, router: LeonesRouter | None = None) -> None:
        self.atlas = atlas
        self.router = router or LeonesRouter()
        self.tasks = TaskIntelligence()

    def decide(self, request: str, hardware: HardwareProfile) -> Decision:
        task = self.tasks.analyze(request)
        candidates = self.atlas.candidates(hardware)
        route = self.router.route(task, hardware, candidates)
        return Decision(task_type=task.task_type, hardware=hardware, route=route)
