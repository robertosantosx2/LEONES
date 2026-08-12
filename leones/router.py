"""Initial backend-independent Leones Router.

This is intentionally conservative: it provides deterministic routing rules
before Atlas-backed scoring is introduced.
"""

from .core.contracts import HardwareProfile, ModelCandidate, RouteDecision, TaskRequirements


class LeonesRouter:
    """Select a model/backend/device from explicit requirements."""

    def route(
        self,
        task: TaskRequirements,
        hardware: HardwareProfile,
        candidates: list[ModelCandidate],
    ) -> RouteDecision:
        if not candidates:
            raise ValueError("No model candidates available")

        candidate = self._select_candidate(task, hardware, candidates)
        backend = self._select_backend(hardware, candidate)
        device = self._select_device(hardware)

        return RouteDecision(
            model_id=candidate.model_id,
            quantization=candidate.quantization,
            backend=backend,
            device=device,
            rationale=(
                f"task={task.task_type}",
                f"ram={hardware.ram_gb:g}GB",
                f"gpu={hardware.gpu or 'none'}",
                f"backend={backend}",
            ),
        )

    @staticmethod
    def _select_candidate(
        task: TaskRequirements,
        hardware: HardwareProfile,
        candidates: list[ModelCandidate],
    ) -> ModelCandidate:
        def score(candidate: ModelCandidate) -> tuple[int, int]:
            capability_match = len(set(task.required_tools) & set(candidate.capabilities))
            coding_bonus = int(task.task_type == "coding" and "coding" in candidate.capabilities)
            return capability_match + coding_bonus, -len(candidate.model_id)

        return max(candidates, key=score)

    @staticmethod
    def _select_device(hardware: HardwareProfile) -> str:
        if hardware.gpu and (hardware.vram_gb or 0) > 0:
            return "gpu"
        if hardware.npu:
            return "npu"
        return "cpu"

    @staticmethod
    def _select_backend(hardware: HardwareProfile, candidate: ModelCandidate) -> str:
        # llama.cpp is the reference local backend; other backends plug in later.
        if "GGUF" in {fmt.upper() for fmt in candidate.formats}:
            return "llama.cpp"
        return "auto"
