"""Group G1: Static Frozen Agent Adapter (Control Group)."""

from __future__ import annotations
import time
from typing import Any, Dict, Optional
from evaeval.adapters.base import (
    AgentAdapter,
    AgentState,
    EvolutionFeedback,
    EvolutionOutcome,
    SandboxAPI,
    TaskResult,
    TaskSpec,
    ToolCallRecord,
)

DEFAULT_G1_PROMPT = (
    "You are a helpful software engineering assistant. "
    "Carefully analyze the task requirements and codebase. "
    "Execute commands, inspect files, implement the solution, and verify correctness."
)


class StaticAgentAdapter(AgentAdapter):
    """G1: Frozen baseline control group. Never mutates prompt, memory, or behavior."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(group="G1", config=config)
        self.system_prompt = (config or {}).get("system_prompt", DEFAULT_G1_PROMPT)
        self.initial_prompt = self.system_prompt
        self.version = "agent_v0"
        self._record_state()

    def _record_state(self) -> None:
        self.state_history[self.version] = AgentState(
            version=self.version,
            group="G1",
            system_prompt=self.system_prompt,
            memory={},
            patches={},
        )

    def reset(self) -> None:
        """Reset state to baseline."""
        self.system_prompt = self.initial_prompt
        self.version = "agent_v0"

    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        """Execute task inside sandbox with baseline logic."""
        start_time = time.time()
        tool_records = []
        tokens_used = 150
        cost_usd = 0.0003

        # Step 1: List directory
        list_res = sandbox.list_dir(".")
        tool_records.append(
            ToolCallRecord(
                tool_name="list_dir",
                arguments={"path": "."},
                output=str([item.get("name") for item in list_res]),
                exit_code=0,
                duration_ms=10,
            )
        )

        # Step 2: Read entrypoint or main files if specified
        entry = task.entrypoint or "solution.py"
        try:
            content = sandbox.read_file(entry)
            tool_records.append(
                ToolCallRecord(
                    tool_name="read_file",
                    arguments={"path": entry},
                    output=content[:200] if content else "",
                    exit_code=0,
                    duration_ms=10,
                )
            )
        except Exception:
            pass

        # Step 3: Run command test or execution
        exec_res = sandbox.exec_command("python -m pytest || true", timeout=20)
        tool_records.append(
            ToolCallRecord(
                tool_name="exec_command",
                arguments={"cmd": "python -m pytest || true"},
                output=exec_res.get("stdout", "")[:500],
                exit_code=exec_res.get("exit_code", 0),
                duration_ms=int(exec_res.get("duration_ms", 100)),
            )
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        return TaskResult(
            task_id=task.task_id,
            success=True,
            status="completed",
            tool_calls=tool_records,
            submission="Baseline static completion",
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            wall_time_ms=elapsed_ms,
        )

    def get_state(self) -> AgentState:
        return AgentState(
            version=self.version,
            group="G1",
            system_prompt=self.system_prompt,
            memory={},
            patches={},
        )

    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        """G1 is frozen: rejects/ignores all evolution mutations."""
        return EvolutionOutcome(
            status="unchanged",
            new_version=self.version,
            mutation_type="none",
            rationale="G1 is a frozen baseline control group; no self-evolution applied.",
        )

    def rollback(self, checkpoint_id: str) -> None:
        """Rollback to a specified version."""
        if checkpoint_id in self.state_history:
            st = self.state_history[checkpoint_id]
            self.system_prompt = st.system_prompt
            self.version = checkpoint_id
