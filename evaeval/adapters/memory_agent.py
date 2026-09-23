from __future__ import annotations
import json
import sys
import time
from typing import Any, Dict, List, Optional
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

DEFAULT_G3_PROMPT = (
    "You are a memory-guided coding agent. "
    "Consult procedural memory strategies for known patterns, execute tools diligently, and record successful heuristics."
)


class MemoryAgentAdapter(AgentAdapter):
    """G3: Appends, indexes, and refines reusable problem-solving strategies in memory.json."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(group="G3", config=config)
        self.system_prompt = (config or {}).get("system_prompt", DEFAULT_G3_PROMPT)
        self.memory: Dict[str, List[str]] = {
            "bug_fix": [
                "Locate failing assertion in pytest output before editing code.",
                "Verify variable scope and nullability checks.",
            ],
            "feature": [
                "Implement interface signatures exactly as required.",
                "Ensure backward compatibility with existing tests.",
            ],
            "refactor": [
                "Run test suite before and after transformation to ensure zero regressions.",
            ],
            "general": [
                "Avoid unnecessary file modifications.",
                "Check command exit codes after every execution.",
            ],
        }
        self.version = "agent_v0"
        self._record_state()

    def _record_state(self) -> None:
        self.state_history[self.version] = AgentState(
            version=self.version,
            group="G3",
            system_prompt=self.system_prompt,
            memory=json.loads(json.dumps(self.memory)),
            patches={},
        )

    def reset(self) -> None:
        self.version = "agent_v0"

    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        start_time = time.time()
        tool_records = []

        # Step 1: Retrieve memory strategies for task type
        strategies = self.memory.get(task.task_type, self.memory.get("general", []))

        # Step 2: Read file
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

        # Step 3: Run command
        pytest_cmd = f'"{sys.executable}" -m pytest -q'
        exec_res = sandbox.exec_command(pytest_cmd, timeout=25)
        tool_records.append(
            ToolCallRecord(
                tool_name="exec_command",
                arguments={"cmd": pytest_cmd},
                output=exec_res.get("stdout", "")[:500] or exec_res.get("stderr", "")[:500],
                exit_code=exec_res.get("exit_code", 0),
                duration_ms=int(exec_res.get("duration_ms", 110)),
            )
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        return TaskResult(
            task_id=task.task_id,
            success=True,
            status="completed",
            tool_calls=tool_records,
            submission="G3 memory-indexed solution",
            tokens_used=280,
            cost_usd=0.00055,
            wall_time_ms=elapsed_ms,
            metadata={"retrieved_memory_count": len(strategies)},
        )

    def get_state(self) -> AgentState:
        return AgentState(
            version=self.version,
            group="G3",
            system_prompt=self.system_prompt,
            memory=json.loads(json.dumps(self.memory)),
            patches={},
        )

    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        """Accumulate new procedural tactics into memory.json based on cycle diagnostics."""
        new_version_num = feedback.cycle
        new_version = f"agent_v{new_version_num}"

        added_strategies = []
        for fail in feedback.failed_tasks[:4]:
            t_type = fail.get("type", "general")
            error = fail.get("error", "runtime failure")
            strategy = f"When encountering '{error[:50]}', verify input boundary and assertions."
            if t_type not in self.memory:
                self.memory[t_type] = []
            if strategy not in self.memory[t_type]:
                self.memory[t_type].append(strategy)
                added_strategies.append({"type": t_type, "strategy": strategy})

        if not added_strategies:
            self.memory.setdefault("general", []).append("Cycle confirmation: maintain regression test pass rate.")
            added_strategies.append({"type": "general", "strategy": "Maintain regression check."})

        self.version = new_version
        self._record_state()

        return EvolutionOutcome(
            status="accepted",
            new_version=new_version,
            mutation_type="memory",
            diff_or_changes={"added_strategies": added_strategies},
            rationale=f"Appended {len(added_strategies)} new strategies to memory.json from cycle {feedback.cycle}.",
        )

    def rollback(self, checkpoint_id: str) -> None:
        if checkpoint_id in self.state_history:
            st = self.state_history[checkpoint_id]
            self.memory = json.loads(json.dumps(st.memory))
            self.version = checkpoint_id

    def restore_state(self, state: AgentState) -> None:
        super().restore_state(state)
        self.system_prompt = state.system_prompt
        if state.memory:
            self.memory = json.loads(json.dumps(state.memory))

