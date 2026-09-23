"""Base contracts and abstract class for Agent Adapters."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    """Specification of task provided to the agent adapter."""
    task_id: str
    task_type: str
    repo_name: str
    prompt: str
    entrypoint: Optional[str] = None
    protected_files: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    """Record of a tool call executed during a task."""
    tool_name: str
    arguments: Dict[str, Any]
    output: str
    exit_code: int = 0
    duration_ms: int = 0


class TaskResult(BaseModel):
    """Outcome returned by an agent after attempting a task."""
    task_id: str
    success: bool
    status: str = "completed"
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    submission: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    wall_time_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Serialized internal state of an agent (prompt, memory, code)."""
    version: str = "agent_v0"
    group: str
    system_prompt: str
    memory: Dict[str, Any] = Field(default_factory=dict)
    patches: Dict[str, str] = Field(default_factory=dict)
    history_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvolutionFeedback(BaseModel):
    """Aggregated cycle feedback provided to the agent to guide evolution."""
    cycle: int
    success_rate: float
    total_tasks: int
    failed_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    safety_violations: List[Dict[str, Any]] = Field(default_factory=list)
    proxy_gap_average: float = 0.0
    custom_diagnostics: Dict[str, Any] = Field(default_factory=dict)


class EvolutionOutcome(BaseModel):
    """Result of an evolution step."""
    status: str  # accepted, rejected, rolled_back, unchanged
    new_version: str
    mutation_type: str
    diff_or_changes: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    error: Optional[str] = None


@runtime_checkable
class SandboxAPI(Protocol):
    """Sandbox interface presented to the agent."""
    def exec_command(self, cmd: str, timeout: int = 30) -> Dict[str, Any]: ...
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...
    def list_dir(self, path: str = ".") -> List[Dict[str, Any]]: ...


class AgentAdapter(ABC):
    """The framework-agnostic agent contract."""

    def __init__(self, group: str = "G1", config: Optional[Dict[str, Any]] = None):
        self.group = group
        self.config = config or {}
        self.state_history: Dict[str, AgentState] = {}
        self.version = "agent_v0"

    @abstractmethod
    def reset(self) -> None:
        """Reset agent to its initial configuration (wipe episodic memory)."""
        pass

    @abstractmethod
    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        """Execute a coding task inside the provided sandbox environment."""
        pass

    @abstractmethod
    def get_state(self) -> AgentState:
        """Return the current mutable agent state."""
        pass

    @abstractmethod
    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        """Analyze cycle feedback and update internal state/prompt/memory."""
        pass

    @abstractmethod
    def rollback(self, checkpoint_id: str) -> None:
        """Revert agent state to a previous checkpoint."""
        pass
