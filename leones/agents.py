"""Agent orchestration boundary for LEONES.

Agents express intent and tools; model inference is delegated to Leones Router.
"""

from dataclasses import dataclass, field
from typing import Any

from .core.contracts import TaskRequirements


@dataclass
class AgentContext:
    task: TaskRequirements
    memory: dict[str, Any] = field(default_factory=dict)
    tools: tuple[str, ...] = ()


class LeonesAgent:
    """Small orchestration boundary for the first implementation."""

    def __init__(self, context: AgentContext) -> None:
        self.context = context

    def required_capabilities(self) -> tuple[str, ...]:
        return self.context.task.required_tools
