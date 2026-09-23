"""EvoEval: Measuring Safety Drift and Capability Retention in Self-Evolving Code Agents."""

__version__ = "0.1.0"
__author__ = "EvoEval Research Team"

from evaeval.trajectory.schema import TrajectoryEvent, CostRecord
from evaeval.adapters.base import AgentAdapter, TaskSpec, TaskResult, EvolutionFeedback, EvolutionOutcome

__all__ = [
    "__version__",
    "TrajectoryEvent",
    "CostRecord",
    "AgentAdapter",
    "TaskSpec",
    "TaskResult",
    "EvolutionFeedback",
    "EvolutionOutcome",
]
