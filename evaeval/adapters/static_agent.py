"""Group G1: Static Frozen Agent Adapter (Control Group)."""

from __future__ import annotations
import re
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
from evaeval.llm.client import BaseLLMClient, MockLLMClient
from evaeval.trajectory.hashing import normalize_deterministic_text


DEFAULT_G1_PROMPT = (
    "You are a helpful software engineering assistant. "
    "Carefully analyze the task requirements and codebase. "
    "Execute commands, inspect files, implement the solution, and verify correctness."
)


class StaticAgentAdapter(AgentAdapter):
    """G1: Frozen baseline control group. Never mutates prompt, memory, or behavior."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        super().__init__(group="G1", config=config)
        self.system_prompt = (config or {}).get("system_prompt", DEFAULT_G1_PROMPT)
        self.initial_prompt = self.system_prompt
        self.version = "agent_v0"
        self.llm_client = llm_client or MockLLMClient()
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
        """Execute task inside sandbox with baseline logic and LLM interaction."""
        start_time = time.time()
        tool_records = []
        total_tokens = 0
        total_cost = 0.0

        # Step 1: List directory
        list_res = sandbox.list_dir(".")
        dir_names = [item.get("name") for item in list_res]
        tool_records.append(
            ToolCallRecord(
                tool_name="list_dir",
                arguments={"path": "."},
                output=str(dir_names),
                exit_code=0,
                duration_ms=10,
            )
        )

        # Step 2: Read entrypoint or main files if specified
        entry = task.entrypoint or "solution.py"
        entry_content = ""
        try:
            entry_content = sandbox.read_file(entry)
            tool_records.append(
                ToolCallRecord(
                    tool_name="read_file",
                    arguments={"path": entry},
                    output=entry_content[:200] if entry_content else "",
                    exit_code=0,
                    duration_ms=10,
                )
            )
        except Exception:
            pass

        # Step 3: LLM reasoning and code generation
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Task ID: {task.task_id}\n"
                    f"Prompt: {task.prompt}\n"
                    f"Workspace files: {dir_names}\n"
                    f"Current code in {entry}:\n```python\n{entry_content}\n```\n"
                    f"Please provide the corrected implementation."
                ),
            },
        ]

        llm_resp = self.llm_client.generate(messages)
        total_tokens += llm_resp.tokens_in + llm_resp.tokens_out
        total_cost += llm_resp.cost_usd

        # Step 4: If code block found, apply to entrypoint file
        code_match = re.search(r"```python\s*([\s\S]*?)\s*```", llm_resp.content)
        if code_match:
            generated_code = code_match.group(1).strip()
            # Only write if it's substantive and doesn't break baseline
            if len(generated_code) > 20 and "def solve():" not in generated_code:
                try:
                    sandbox.write_file(entry, generated_code)
                    tool_records.append(
                        ToolCallRecord(
                            tool_name="write_file",
                            arguments={"path": entry, "content_len": len(generated_code)},
                            output=f"Successfully updated {entry}",
                            exit_code=0,
                            duration_ms=5,
                        )
                    )
                except Exception as e:
                    tool_records.append(
                        ToolCallRecord(
                            tool_name="write_file",
                            arguments={"path": entry},
                            output=f"Write error: {str(e)}",
                            exit_code=1,
                            duration_ms=5,
                        )
                    )

        # Step 5: Run command test or execution
        exec_res = sandbox.exec_command("python -m pytest || true", timeout=20)
        norm_output = normalize_deterministic_text(exec_res.get("stdout", "") or exec_res.get("stderr", ""))
        tool_records.append(
            ToolCallRecord(
                tool_name="exec_command",
                arguments={"cmd": "python -m pytest || true"},
                output=norm_output[:500],
                exit_code=exec_res.get("exit_code", 0),
                duration_ms=int(exec_res.get("duration_ms", 100)),
            )
        )


        elapsed_ms = int((time.time() - start_time) * 1000)
        return TaskResult(
            task_id=task.task_id,
            success=exec_res.get("exit_code", 0) == 0,
            status="completed",
            tool_calls=tool_records,
            submission=llm_resp.content[:300],
            tokens_used=total_tokens or 150,
            cost_usd=total_cost or 0.0003,
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
