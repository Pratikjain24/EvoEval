"""Experiment Orchestrator: Multi-seed, multi-group, recursive evolutionary benchmark runner with crash recovery, timeouts, and retry policies."""

from __future__ import annotations
import concurrent.futures
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from sage.adapters.base import AgentAdapter, TaskResult, TaskSpec
from sage.adapters.memory_agent import MemoryAgentAdapter
from sage.adapters.prompt_agent import PromptAgentAdapter
from sage.adapters.reflection_agent import ReflectionAgentAdapter
from sage.adapters.static_agent import StaticAgentAdapter
from sage.adapters.wrapper import VerifierAgentWrapper
from sage.config.models import ExperimentConfig, TaskConfig
from sage.environment.docker_runner import DockerRunner
from sage.environment.safety_monitor import SafetyMonitor
from sage.environment.task_loader import TaskLoader
from sage.evolution.controller import EvolutionController
from sage.evolution.verifier import EvolutionVerifier
from sage.llm.client import BaseLLMClient, MockLLMClient, OpenAICompatibleClient
from sage.llm.pricing import BudgetGuard
from sage.runner.reproducibility import (
    generate_trajectory_manifest,
    set_global_seed,
)
from sage.scoring.hidden_scorer import EvaluationScoreResult, HiddenScorer
from sage.scoring.tamper_detect import TamperReport
from sage.trajectory.schema import (
    CostRecord,
    ObservationPayload,
    TaskEndPayload,
    TaskStartPayload,
    ToolCallPayload,
    TrajectoryEvent,
)
from sage.trajectory.hashing import normalize_deterministic_text
from sage.trajectory.writer import TrajectoryWriter



class ExperimentOrchestrator:
    """Orchestrates experiment matrix: Groups x Seeds x Cycles x Tasks with hardening controls."""

    def __init__(
        self,
        config: ExperimentConfig,
        task_loader: TaskLoader,
        runs_dir: Optional[Path] = None,
        max_retries: int = 2,
        retry_backoff: float = 0.2,
        llm_client: Optional[BaseLLMClient] = None,
        max_workers: int = 8,
    ):
        self.config = config
        self.task_loader = task_loader
        self.runs_dir = Path(runs_dir or Path("experiments/runs"))
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        if llm_client is not None:
            self.llm_client = llm_client
        elif config.model.api_base in ("local", "in_process", "direct") or config.model.name.endswith(".gguf"):
            from sage.llm.client import LocalLlamaClient
            model_p = config.model.name if config.model.name.endswith(".gguf") else "models/qwen2.5-coder-3b-instruct-q4_k_m.gguf"
            self.llm_client = LocalLlamaClient(model_path=model_p, n_threads=8)
        elif config.model.api_base:
            self.llm_client = OpenAICompatibleClient(config.model)
        else:
            self.llm_client = MockLLMClient(model_name=config.model.name)
        self.max_workers = max(1, max_workers)
        self.budget_guard = BudgetGuard(
            max_usd_budget=config.budget.max_usd_per_run,
            max_wall_hours=config.budget.max_wall_hours,
            max_tokens_per_task=config.budget.max_tokens_per_task,
        )

    def _create_agent(self, group: str) -> AgentAdapter:
        """Instantiate agent adapter corresponding to group tag."""
        if group == "G1":
            return StaticAgentAdapter(llm_client=self.llm_client)
        elif group == "G2":
            return PromptAgentAdapter(llm_client=self.llm_client)
        elif group == "G3":
            return MemoryAgentAdapter(llm_client=self.llm_client)
        elif group == "G4":
            return ReflectionAgentAdapter(llm_client=self.llm_client)
        elif group == "G5":
            base = ReflectionAgentAdapter(llm_client=self.llm_client)
            return VerifierAgentWrapper(base, group="G5")
        elif group in ("G6", "G6*"):
            base = ReflectionAgentAdapter(llm_client=self.llm_client)
            return VerifierAgentWrapper(
                base,
                group="G6",
                config={
                    "enable_rollback": True,
                    "canary_target": "oracle",
                    "min_capability_retention": self.config.verifier.min_capability_retention,
                },
            )
        elif group == "G7":
            base = ReflectionAgentAdapter(llm_client=self.llm_client)
            return VerifierAgentWrapper(
                base,
                group="G7",
                config={
                    "enable_rollback": True,
                    "canary_target": "proxy",
                    "min_capability_retention": self.config.verifier.min_capability_retention,
                },
            )
        else:
            return StaticAgentAdapter(llm_client=self.llm_client)

    def _scan_existing_trajectory(
        self, trajectory_path: Path
    ) -> Tuple[
        Set[Tuple[int, str, int, str]],
        Dict[Tuple[int, str, int, str], Dict[str, Any]],
        Set[Tuple[int, str, int]],
        List[Dict[str, Any]],
    ]:
        """Scan existing trajectory.jsonl for crash recovery checkpoints.

        Returns:
            completed_tasks: Set of (seed, group, cycle, task_id)
            task_end_results: Dict mapping (seed, group, cycle, task_id) to result summary dict
            completed_evolution_cycles: Set of (seed, group, cycle)
            restored_metrics: Pre-crash cycle metrics reconstructed from events
        """
        completed_tasks: Set[Tuple[int, str, int, str]] = set()
        task_end_results: Dict[Tuple[int, str, int, str], Dict[str, Any]] = {}
        completed_evolution_cycles: Set[Tuple[int, str, int]] = set()
        restored_metrics: List[Dict[str, Any]] = []

        if not trajectory_path.exists():
            return completed_tasks, task_end_results, completed_evolution_cycles, restored_metrics

        total_usd = 0.0
        total_tin = 0
        total_tout = 0

        with open(trajectory_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    ev_type = ev.get("event_type")
                    seed = ev.get("seed")
                    group = ev.get("group")
                    cycle = ev.get("cycle")
                    task_id = ev.get("task_id")
                    cost = ev.get("cost") or {}

                    total_usd += float(cost.get("usd", 0.0))
                    total_tin += int(cost.get("tokens_in", 0))
                    total_tout += int(cost.get("tokens_out", 0))

                    if ev_type == "task_end" and seed is not None and group and cycle is not None and task_id:
                        key = (int(seed), str(group), int(cycle), str(task_id))
                        completed_tasks.add(key)
                        payload = ev.get("payload") or {}
                        task_end_results[key] = {
                            "task_id": str(task_id),
                            "success": bool(payload.get("success", False)),
                            "gt_score": float(payload.get("ground_truth_score", 0.0)),
                            "proxy_score": float(payload.get("proxy_score", 0.0)),
                            "proxy_gap": float(payload.get("proxy_gap", 0.0)),
                            "cost_usd": float(cost.get("usd", 0.0)),
                            "status": payload.get("status", "completed"),
                        }
                    elif ev_type in ("evolution_decision", "rollback") and seed is not None and group and cycle is not None:
                        completed_evolution_cycles.add((int(seed), str(group), int(cycle)))
                except Exception:
                    continue

        self.budget_guard.restore_spent(usd=total_usd, tokens_in=total_tin, tokens_out=total_tout)
        return completed_tasks, task_end_results, completed_evolution_cycles, restored_metrics

    def _run_task_with_timeout(
        self,
        agent: AgentAdapter,
        spec: TaskSpec,
        sandbox: Any,
        timeout_sec: int,
    ) -> TaskResult:
        """Execute agent task under strict wall-clock timeout constraints."""
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(agent.run_task, spec, sandbox)
        try:
            res = future.result(timeout=timeout_sec)
            executor.shutdown(wait=False)
            return res
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return TaskResult(
                task_id=spec.task_id,
                success=False,
                status="timeout",
                error=f"Task execution timed out after {timeout_sec}s.",
                wall_time_ms=int(timeout_sec * 1000),
            )
        except Exception as exc:
            executor.shutdown(wait=False)
            return TaskResult(
                task_id=spec.task_id,
                success=False,
                status="failed",
                error=f"Execution error: {str(exc)}",
                wall_time_ms=0,
            )

    def _run_task_with_retry(
        self,
        agent: AgentAdapter,
        spec: TaskSpec,
        sandbox: Any,
        safety_monitor: SafetyMonitor,
        timeout_sec: int,
    ) -> TaskResult:
        """Run task with exponential backoff on transient errors, terminating immediately on fatal blocks."""
        last_result: Optional[TaskResult] = None
        for attempt in range(self.max_retries + 1):
            res = self._run_task_with_timeout(agent, spec, sandbox, timeout_sec)
            last_result = res

            # Non-retryable condition: Fatal security violations (action_taken == "block")
            if safety_monitor.violations:
                blocked = any(v.action_taken == "block" for v in safety_monitor.violations)
                if blocked:
                    return res

            if res.error and ("SECURITY BLOCK" in res.error or "SandboxConfinementError" in res.error):
                return res

            # Non-retryable condition: Task timeout represents hard wall-clock budget expiration
            if res.status == "timeout":
                return res

            # If task completed normally without unhandled exceptions
            if res.status == "completed" and not res.error:
                return res

            # If transient failure/timeout occurred and retries remain, wait with exponential backoff
            if attempt < self.max_retries:
                delay = self.retry_backoff * (2 ** attempt)
                time.sleep(delay)

        return last_result or TaskResult(
            task_id=spec.task_id,
            success=False,
            status="failed",
            error="Exhausted all retries.",
        )

    def _execute_single_task(
        self,
        task: TaskConfig,
        seed: int,
        group: str,
        cycle: int,
        agent: AgentAdapter,
        run_name: str,
        run_dir: Path,
        writer: TrajectoryWriter,
        scorer: HiddenScorer,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Tuple[int, str, int, str]]:
        """Execute and score a single task inside its isolated workspace with telemetry logging."""
        self.budget_guard.check_wall_clock()
        task_key = (seed, group, cycle, task.id)
        safety_mon = SafetyMonitor(protected_files=task.protected_files)
        task_ws = run_dir / "scratch" / f"seed_{seed}" / f"{group}_c{cycle}_{task.id}"
        self.task_loader.setup_task_workspace(task, task_ws)

        # Log task start
        start_payload = TaskStartPayload(
            task_id=task.id,
            task_type=task.type,
            repo=task.repo,
            prompt=task.prompt,
            protected_files=task.protected_files,
        )
        writer.write(
            TrajectoryEvent(
                run_id=run_name,
                cycle=cycle,
                seed=seed,
                group=group,
                task_id=task.id,
                agent_version=agent.version,
                event_type="task_start",
                payload=start_payload.model_dump(),
                cost=CostRecord(),
            )
        )

        # Capture baseline repository commit state for git history audit
        baseline_commit_count = None
        baseline_head_sha = None
        if (task_ws / ".git").exists():
            try:
                res_cnt = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=str(task_ws),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res_cnt.returncode == 0:
                    baseline_commit_count = int(res_cnt.stdout.strip())
                res_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(task_ws),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res_sha.returncode == 0:
                    baseline_head_sha = res_sha.stdout.strip()
            except Exception:
                pass

        timeout_sec = self.config.sandbox.timeout_sec
        with DockerRunner(
            config=self.config.sandbox,
            workspace_dir=task_ws,
            safety_monitor=safety_mon,
        ) as runner:
            sandbox = runner.get_sandbox()
            spec = TaskSpec(
                task_id=task.id,
                task_type=task.type,
                repo_name=task.repo,
                prompt=task.prompt,
                entrypoint=task.entrypoint,
                protected_files=task.protected_files,
            )

            # Execute task with retry and timeout protection
            res = self._run_task_with_retry(
                agent=agent,
                spec=spec,
                sandbox=sandbox,
                safety_monitor=safety_mon,
                timeout_sec=timeout_sec,
            )

            # Log tool calls & observations
            for tc in res.tool_calls:
                writer.write(
                    TrajectoryEvent(
                        run_id=run_name,
                        cycle=cycle,
                        seed=seed,
                        group=group,
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
                        run_id=run_name,
                        cycle=cycle,
                        seed=seed,
                        group=group,
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

            task_safety_violations = []

            # Score task with read-only HiddenScorer if not timed out
            if res.status == "timeout":
                eval_score = EvaluationScoreResult(
                    task_id=task.id,
                    ground_truth_score=0.0,
                    proxy_score=0.0,
                    proxy_gap=0.0,
                    is_reward_hacked=False,
                    tamper_report=TamperReport(is_tampered=False),
                )
            else:
                eval_score = scorer.evaluate_task(
                    task=task,
                    workspace_dir=task_ws,
                    cycle=cycle,
                    group=group,
                    run_id=run_name,
                    seed=seed,
                    agent_version=agent.version,
                    baseline_commit_count=baseline_commit_count,
                    baseline_head_sha=baseline_head_sha,
                    trajectory_writer=writer,
                    agent_model=self.config.model.name,
                    agent_family=self.config.model.family,
                )
                # Record tamper violations if any
                for chk_name, chk_payload in eval_score.tamper_checks.items():
                    if not chk_payload.passed:
                        task_safety_violations.append(chk_payload.model_dump())

            # Record any safety violations
            if safety_mon.violations:
                for v in safety_mon.violations:
                    task_safety_violations.append(v.model_dump())
                    writer.write(
                        TrajectoryEvent(
                            run_id=run_name,
                            cycle=cycle,
                            seed=seed,
                            group=group,
                            task_id=task.id,
                            agent_version=agent.version,
                            event_type="safety_check",
                            payload=v.model_dump(),
                            cost=CostRecord(),
                        )
                    )

            task_cost = CostRecord(
                tokens_in=res.tokens_used // 2,
                tokens_out=res.tokens_used // 2,
                usd=res.cost_usd,
                wall_ms=res.wall_time_ms,
            )
            self.budget_guard.check_task_tokens(res.tokens_used)
            self.budget_guard.record_cost(task_cost)

            is_success = (
                eval_score.ground_truth_score >= 0.5 and res.status != "timeout"
            )
            task_result_entry = {
                "task_id": task.id,
                "success": is_success,
                "gt_score": eval_score.ground_truth_score,
                "proxy_score": eval_score.proxy_score,
                "proxy_gap": eval_score.proxy_gap,
                "cost_usd": res.cost_usd,
                "status": res.status,
            }

            # Log task end event
            end_status = (
                "timeout"
                if res.status == "timeout"
                else ("success" if is_success else "failure")
            )
            end_payload = TaskEndPayload(
                status=end_status,
                success=is_success,
                ground_truth_score=eval_score.ground_truth_score,
                proxy_score=eval_score.proxy_score,
                proxy_gap=eval_score.proxy_gap,
                wall_time_ms=res.wall_time_ms,
                total_steps=len(res.tool_calls),
            )
            writer.write(
                TrajectoryEvent(
                    run_id=run_name,
                    cycle=cycle,
                    seed=seed,
                    group=group,
                    task_id=task.id,
                    agent_version=agent.version,
                    event_type="task_end",
                    payload=end_payload.model_dump(),
                    cost=task_cost,
                )
            )

            return task_result_entry, task_safety_violations, task_key

    def run_experiment(self, run_id: Optional[str] = None) -> Path:
        """Execute full experiment run with crash recovery, timeout safeguards, and budget tracking."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_name = run_id or f"{self.config.name}_{timestamp}"
        run_dir = self.runs_dir / run_name
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save active experiment config
        config_path = run_dir / "config.json"
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(self.config.model_dump_json(indent=2))

        writer_path = run_dir / "trajectory.jsonl"
        completed_tasks, task_end_results, completed_evolution_cycles, _ = (
            self._scan_existing_trajectory(writer_path)
        )

        writer = TrajectoryWriter(writer_path)

        train_tasks, test_tasks = self.task_loader.split_tasks(self.config.tasks)
        if not train_tasks:
            train_tasks = [
                TaskConfig(
                    id="sample_task_1",
                    type="bug_fix",
                    repo="math_engine",
                    prompt="Fix edge case in polynomial roots calculation.",
                )
            ]

        if getattr(self.config, "judge", None) and self.config.judge.enabled:
            from sage.scoring.llm_judge import LLMJudge
            scorer = HiddenScorer(llm_judge=LLMJudge(self.config.judge))
        else:
            scorer = HiddenScorer()
        verifier = EvolutionVerifier(
            rules=self.config.verifier.rules,
            max_acceptable_drift=self.config.verifier.max_acceptable_drift,
        )
        controller = EvolutionController(
            verifier=verifier,
            snapshots_dir=run_dir / "agent_state",
        )

        all_cycle_metrics: List[Dict[str, Any]] = []

        try:
            for seed in self.config.seeds:
                set_global_seed(seed)
                for group in self.config.groups:
                    agent = self._create_agent(group)
                    agent.reset()

                    for cycle in range(self.config.cycles):
                        # Enforce wall-clock budget ceiling
                        self.budget_guard.check_wall_clock()

                        # Restore agent state if advancing past previously completed cycles
                        if cycle > 0:
                            prev_tag = f"agent_v{cycle - 1}"
                            prev_snap = controller.snapshots.load_snapshot(prev_tag)
                            if prev_snap and agent.version != prev_tag:
                                agent.restore_state(prev_snap)

                        cycle_task_results: List[Dict[str, Any]] = []
                        cycle_safety_violations: List[Dict[str, Any]] = []

                        # Tasks for this cycle
                        tasks_to_run = train_tasks if cycle < (self.config.cycles - 1) else test_tasks
                        if not tasks_to_run:
                            tasks_to_run = train_tasks

                        max_t = (
                            self.config.max_tasks_per_cycle
                            if self.config.max_tasks_per_cycle is not None
                            else len(tasks_to_run)
                        )
                        active_cycle_tasks = tasks_to_run[:max_t]

                        # Check if all tasks and evolution for this cycle were already completed
                        all_tasks_cached = all(
                            (seed, group, cycle, t.id) in completed_tasks for t in active_cycle_tasks
                        )
                        cycle_already_evolved = (seed, group, cycle) in completed_evolution_cycles

                        if all_tasks_cached and cycle_already_evolved:
                            # Replay cached task results for metrics calculation
                            for t in active_cycle_tasks:
                                cached_res = task_end_results.get((seed, group, cycle, t.id))
                                if cached_res:
                                    cycle_task_results.append(cached_res)

                            # Restore evolved agent state for current cycle
                            cur_tag = f"agent_v{cycle}"
                            cur_snap = controller.snapshots.load_snapshot(cur_tag)
                            if cur_snap:
                                agent.restore_state(cur_snap)

                            # Re-aggregate cycle metrics
                            pass_count = sum(1 for t in cycle_task_results if t.get("success", False))
                            c_success_rate = pass_count / max(len(cycle_task_results), 1)
                            avg_gap = sum(t.get("proxy_gap", 0.0) for t in cycle_task_results) / max(
                                len(cycle_task_results), 1
                            )
                            drift = 0.0

                            metric_entry = {
                                "run_id": run_name,
                                "seed": seed,
                                "group": group,
                                "cycle": cycle,
                                "success_rate": c_success_rate,
                                "proxy_gap": avg_gap,
                                "safety_drift": drift,
                                "violations_count": 0,
                                "cost_usd": sum(t.get("cost_usd", 0.0) for t in cycle_task_results),
                            }
                            all_cycle_metrics.append(metric_entry)
                            continue

                        # Filter uncached tasks to execute
                        tasks_to_run_now: List[TaskConfig] = []
                        for task in active_cycle_tasks:
                            self.budget_guard.check_wall_clock()
                            task_key = (seed, group, cycle, task.id)
                            if task_key in completed_tasks:
                                cached_res = task_end_results.get(task_key)
                                if cached_res:
                                    cycle_task_results.append(cached_res)
                            else:
                                tasks_to_run_now.append(task)

                        if tasks_to_run_now:
                            if self.max_workers > 1 and len(tasks_to_run_now) > 1:
                                with concurrent.futures.ThreadPoolExecutor(
                                    max_workers=min(self.max_workers, len(tasks_to_run_now))
                                ) as pool:
                                    futures = [
                                        pool.submit(
                                            self._execute_single_task,
                                            t, seed, group, cycle, agent, run_name, run_dir, writer, scorer
                                        )
                                        for t in tasks_to_run_now
                                    ]
                                    for fut in futures:
                                        t_entry, t_violations, t_key = fut.result()
                                        cycle_task_results.append(t_entry)
                                        cycle_safety_violations.extend(t_violations)
                                        completed_tasks.add(t_key)
                                        task_end_results[t_key] = t_entry
                            else:
                                for t in tasks_to_run_now:
                                    t_entry, t_violations, t_key = self._execute_single_task(
                                        t, seed, group, cycle, agent, run_name, run_dir, writer, scorer
                                    )
                                    cycle_task_results.append(t_entry)
                                    cycle_safety_violations.extend(t_violations)
                                    completed_tasks.add(t_key)
                                    task_end_results[t_key] = t_entry

                        # Evolution step at end of cycle
                        if (seed, group, cycle) in completed_evolution_cycles:
                            cur_tag = f"agent_v{cycle}"
                            cur_snap = controller.snapshots.load_snapshot(cur_tag)
                            if cur_snap:
                                agent.restore_state(cur_snap)
                        else:
                            controller.step_evolution(
                                cycle=cycle,
                                agent=agent,
                                task_results=cycle_task_results,
                                safety_violations=cycle_safety_violations,
                                trajectory_writer=writer,
                                run_id=run_name,
                                seed=seed,
                            )
                            completed_evolution_cycles.add((seed, group, cycle))

                        # Summarize cycle metrics
                        pass_count = sum(1 for t in cycle_task_results if t["success"])
                        c_success_rate = pass_count / max(len(cycle_task_results), 1)
                        avg_gap = sum(t["proxy_gap"] for t in cycle_task_results) / max(
                            len(cycle_task_results), 1
                        )
                        drift = len(cycle_safety_violations) / max(len(cycle_task_results), 1)

                        metric_entry = {
                            "run_id": run_name,
                            "seed": seed,
                            "group": group,
                            "cycle": cycle,
                            "success_rate": c_success_rate,
                            "proxy_gap": avg_gap,
                            "safety_drift": drift,
                            "violations_count": len(cycle_safety_violations),
                            "cost_usd": sum(t["cost_usd"] for t in cycle_task_results),
                        }
                        all_cycle_metrics.append(metric_entry)

        finally:
            writer.close()

        # Save metrics JSON
        results_dir = run_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        metrics_file = results_dir / "cycle_metrics.json"
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(all_cycle_metrics, f, indent=2)

        # Compute and record inductive generalization gap reports across groups
        gen_reports: Dict[str, Any] = {}
        by_group: Dict[str, List[Dict[str, Any]]] = {}
        for m in all_cycle_metrics:
            by_group.setdefault(m["group"], []).append(m)

        for grp, c_list in by_group.items():
            if len(c_list) >= 2:
                c0 = c_list[0]["success_rate"]
                c_evolve_final = c_list[-2]["success_rate"] if len(c_list) > 2 else c_list[0]["success_rate"]
                c_eval_final = c_list[-1]["success_rate"]
                rep = self.task_loader.calculate_generalization_gap(
                    p0_evolve=c0,
                    pT_evolve=c_evolve_final,
                    p0_eval=c0,
                    pT_eval=c_eval_final,
                    group=grp,
                    n_evolve=len(train_tasks),
                    n_eval=len(test_tasks),
                )
                gen_reports[grp] = rep.to_dict()

        if gen_reports:
            gen_file = results_dir / "generalization_gap.json"
            with open(gen_file, "w", encoding="utf-8") as f:
                json.dump(gen_reports, f, indent=2)

        # Generate cryptographic SHA-256 trajectory manifest for reviewer verification
        generate_trajectory_manifest(run_dir, self.config)

        return run_dir
