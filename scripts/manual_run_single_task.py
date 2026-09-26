"""Manual End-to-End Single Task Runner (Week 2 Milestone).

Proves the complete loop:
AgentAdapter ABC + G1 Static Agent + LLM Client + Sandbox + TrajectoryWriter + HiddenScorer.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from evaeval.adapters.base import TaskSpec
from evaeval.adapters.static_agent import StaticAgentAdapter
from evaeval.environment.safety_monitor import SafetyMonitor
from evaeval.environment.sandbox import LocalSandbox
from evaeval.environment.task_loader import TaskLoader
from evaeval.llm.client import MockLLMClient
from evaeval.scoring.hidden_scorer import HiddenScorer
from evaeval.trajectory.hashing import normalize_deterministic_text
from evaeval.trajectory.reader import TrajectoryReader

from evaeval.trajectory.schema import (
    CostRecord,
    ObservationPayload,
    TaskEndPayload,
    TaskStartPayload,
    ToolCallPayload,
    TrajectoryEvent,
)
from evaeval.trajectory.writer import TrajectoryWriter

console = Console()


def run_single_task_manual(
    task_id: str = "math_001",
    run_dir_name: str = "manual_run_01",
) -> Path:
    """Execute a single task manual end-to-end run proving the evaluation loop."""
    console.print(Panel.fit("[bold cyan]EvoEval: Week 2 Single-Task Manual Run (Proving the Loop)[/bold cyan]"))

    run_dir = Path("experiments/manual_runs") / run_dir_name
    run_dir.mkdir(parents=True, exist_ok=True)
    traj_file = run_dir / "trajectory.jsonl"

    # 1. Initialize TaskLoader and get task
    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)
    task = loader.get_task(task_id)
    if not task:
        tasks = loader.list_tasks()
        task = tasks[0] if tasks else None

    if not task:
        raise ValueError("No tasks found in tasks/tasks_index.json")

    console.print(f"[bold green]1. Task Loaded:[/bold green] [cyan]{task.id}[/cyan] ({task.type}) - {task.prompt[:60]}...")

    # 2. Setup isolated sandbox workspace
    task_ws = run_dir / "workspace"
    loader.setup_task_workspace(task, task_ws)
    safety_mon = SafetyMonitor(protected_files=task.protected_files)
    sandbox = LocalSandbox(workspace_dir=task_ws, safety_monitor=safety_mon)
    console.print(f"[bold green]2. Isolated Sandbox Initialized:[/bold green] {task_ws}")

    # 3. Instantiate G1 Static Agent Adapter with LLM Client
    llm = MockLLMClient("qwen2.5-coder-7b-instruct")
    agent = StaticAgentAdapter(llm_client=llm)
    console.print(f"[bold green]3. Agent Adapter Initialized:[/bold green] Group={agent.group}, Version={agent.version}")

    # 4. Open TrajectoryWriter (append-only with fsync)
    writer = TrajectoryWriter(traj_file)
    console.print(f"[bold green]4. TrajectoryWriter Active:[/bold green] {traj_file}")

    # Log task_start event
    writer.write(
        TrajectoryEvent(
            run_id=run_dir_name,
            cycle=0,
            seed=42,
            group=agent.group,  # type: ignore
            task_id=task.id,
            agent_version=agent.version,
            event_type="task_start",
            payload=TaskStartPayload(
                task_id=task.id,
                task_type=task.type,
                repo=task.repo,
                prompt=task.prompt,
                protected_files=task.protected_files,
            ).model_dump(),
            cost=CostRecord(),
        )
    )

    # 5. Execute Task Spec via AgentAdapter
    console.print("[bold green]5. Executing Task via AgentAdapter.run_task()...[/bold green]")
    spec = TaskSpec(
        task_id=task.id,
        task_type=task.type,
        repo_name=task.repo,
        prompt=task.prompt,
        entrypoint=task.entrypoint,
        protected_files=task.protected_files,
    )

    start_t = time.time()
    task_result = agent.run_task(spec, sandbox)
    wall_ms = int((time.time() - start_t) * 1000)

    # Log tool calls and observations to trajectory
    for tc in task_result.tool_calls:
        writer.write(
            TrajectoryEvent(
                run_id=run_dir_name,
                cycle=0,
                seed=42,
                group=agent.group,  # type: ignore
                task_id=task.id,
                agent_version=agent.version,
                event_type="tool_call",
                payload=ToolCallPayload(
                    tool_name=tc.tool_name,
                    arguments=tc.arguments,
                ).model_dump(),
                cost=CostRecord(),
            )
        )
        writer.write(
            TrajectoryEvent(
                run_id=run_dir_name,
                cycle=0,
                seed=42,
                group=agent.group,  # type: ignore
                task_id=task.id,
                agent_version=agent.version,
                event_type="observation",
                payload=ObservationPayload(
                    tool_name=tc.tool_name,
                    stdout=normalize_deterministic_text(tc.output)[:300],
                    exit_code=tc.exit_code,
                    duration_ms=tc.duration_ms,
                ).model_dump(),
                cost=CostRecord(wall_ms=tc.duration_ms),
            )
        )

    # 6. Evaluate with Read-Only HiddenScorer
    console.print("[bold green]6. Scoring Solution with Read-Only HiddenScorer...[/bold green]")
    scorer = HiddenScorer()
    eval_score = scorer.evaluate_task(
        task=task,
        workspace_dir=task_ws,
        cycle=0,
        group=agent.group,
    )

    # 7. Log Task End
    end_payload = TaskEndPayload(
        status="success" if eval_score.ground_truth_score >= 0.5 else "failure",
        success=eval_score.ground_truth_score >= 0.5,
        ground_truth_score=eval_score.ground_truth_score,
        proxy_score=eval_score.proxy_score,
        proxy_gap=eval_score.proxy_gap,
        wall_time_ms=wall_ms,
        total_steps=len(task_result.tool_calls),
    )

    writer.write(
        TrajectoryEvent(
            run_id=run_dir_name,
            cycle=0,
            seed=42,
            group=agent.group,  # type: ignore
            task_id=task.id,
            agent_version=agent.version,
            event_type="task_end",
            payload=end_payload.model_dump(),
            cost=CostRecord(
                tokens_in=task_result.tokens_used // 2,
                tokens_out=task_result.tokens_used // 2,
                usd=task_result.cost_usd,
                wall_ms=wall_ms,
            ),
        )
    )
    writer.close()

    # 8. Read back trajectory and print verification report
    console.print("[bold green]7. Loop Proved: Streaming Back Trajectory Events:[/bold green]")
    reader = TrajectoryReader(traj_file)
    events = reader.load_all()

    table = Table(title=f"Logged Trajectory Events ({len(events)} events)")
    table.add_column("Step", style="cyan", justify="right")
    table.add_column("Event Type", style="magenta")
    table.add_column("Agent Version", style="yellow")
    table.add_column("Payload Summary", style="white")

    for i, ev in enumerate(events, start=1):
        summary = ""
        if ev.event_type == "task_start":
            summary = f"Task {ev.task_id} ({ev.payload.get('task_type')})"
        elif ev.event_type == "tool_call":
            summary = f"${ev.payload.get('tool_name')}: {json.dumps(ev.payload.get('arguments', {}))}"
        elif ev.event_type == "observation":
            summary = f"Output (exit {ev.payload.get('exit_code')}): {ev.payload.get('stdout', '')[:60]}..."
        elif ev.event_type == "task_end":
            summary = f"Success={ev.payload.get('success')}, GT={ev.payload.get('ground_truth_score')}, ProxyGap={ev.payload.get('proxy_gap')}"
        table.add_row(str(i), ev.event_type, ev.agent_version, summary)

    console.print(table)

    console.print(Panel.fit(
        f"[bold green]SUCCESS: End-to-End Loop Fully Proved![/bold green]\n"
        f"Ground Truth Score: [cyan]{eval_score.ground_truth_score:.2f}[/cyan] | "
        f"Proxy Score: [cyan]{eval_score.proxy_score:.2f}[/cyan] | "
        f"Proxy Gap: [cyan]{eval_score.proxy_gap:.2f}[/cyan]\n"
        f"Trajectory log saved and fsynced at: [yellow]{traj_file}[/yellow]"
    ))

    return traj_file


if __name__ == "__main__":
    run_single_task_manual()
