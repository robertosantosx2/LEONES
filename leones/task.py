"""Task Intelligence baseline: convert user intent into routing requirements."""

import re

from .core.contracts import TaskRequirements


class TaskIntelligence:
    """Small deterministic classifier used until a local classifier is added."""

    def analyze(self, text: str) -> TaskRequirements:
        value = text.lower()
        if re.search(r"\b(cod(e|ing)|python|program|repositorio|tests?)\b", value):
            return TaskRequirements(
                task_type="coding",
                required_tools=("filesystem", "shell"),
                quality_priority=0.7,
            )
        if re.search(r"\b(pdf|documento|document|contrato)\b", value):
            return TaskRequirements(
                task_type="documents",
                required_tools=("filesystem", "rag"),
                quality_priority=0.8,
            )
        if re.search(r"\b(investiga|investig(a|ar)|research|busca|web)\b", value):
            return TaskRequirements(
                task_type="research",
                required_tools=("web", "retrieval"),
                quality_priority=0.9,
            )
        return TaskRequirements(task_type="general", quality_priority=0.5)
