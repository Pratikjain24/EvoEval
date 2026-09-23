"""Evolution Controller: orchestrates the between-cycles self-evolution loop."""

from __future__ import annotations
import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from evaeval.adapters.base import (
    AgentAdapter,
    EvolutionFeedback,
    EvolutionOutcome,
)
from evaeval.evolution.snapshots import SnapshotManager
from evaeval.evolution.verifier import EvolutionVerifier
from evaeval.trajectory.schema import (
    CostRecord,
    EvolutionDecisionPayload,
    EvolutionProposalPayload,
    RollbackPayload,
    TrajectoryEvent,
)
from evaeval.trajectory.writer import TrajectoryWriter


class EvolutionController:
    """Coordinates feedback synthesis, proposal generation, verification gating, and state snapshotting."""

    def __init__(
        self,
        verifier: Optional[EvolutionVerifier] = None,
        snapshots_dir: Optional[Path] = None,
    ):
        self.verifier = verifier or EvolutionVerifier()
        self.snapshots = SnapshotManager(snapshots_dir or Path(".evo_state"))

    def step_evolution(
        self,
        cycle: int,
        agent: AgentAdapter,
        task_results: List[Dict[str, Any]],
        safety_violations: List[Dict[str, Any]],
        trajectory_writer: Optional[TrajectoryWriter] = None,
        run_id: str = "run_default",
        seed: int = 42,
    ) -> EvolutionOutcome:
        """Run the between-cycles evolutionary adaptation step for an agent."""
        # 1. Synthesize feedback
        total_tasks = len(task_results)
        passed_tasks = sum(1 for t in task_results if t.get("success", False))
        success_rate = (passed_tasks / total_tasks) if total_tasks > 0 else 0.0

        failed_tasks = [t for t in task_results if not t.get("success", False)]
        proxy_gaps = [t.get("proxy_gap", 0.0) for t in task_results]
        avg_proxy_gap = sum(proxy_gaps) / len(proxy_gaps) if proxy_gaps else 0.0

        feedback = EvolutionFeedback(
            cycle=cycle,
            success_rate=success_rate,
            total_tasks=total_tasks,
            failed_tasks=failed_tasks,
            safety_violations=safety_violations,
            proxy_gap_average=avg_proxy_gap,
            custom_diagnostics={"total_failures": len(failed_tasks)},
        )

        initial_state = agent.get_state()
        prop_hash = hashlib.sha256(f"{seed}_{agent.group}_{cycle}".encode("utf-8")).hexdigest()[:6]
        proposal_id = f"prop_{cycle}_{prop_hash}"

        # 2. Agent proposes evolution
        outcome = agent.apply_evolution(feedback)

        # Log proposal event if writer is provided
        if trajectory_writer:
            prop_payload = EvolutionProposalPayload(
                proposal_id=proposal_id,
                target_component="system_prompt" if outcome.mutation_type == "system_prompt" else "compound",
                proposed_changes=outcome.diff_or_changes,
                rationale=outcome.rationale,
                diff=str(outcome.diff_or_changes),
            )
            trajectory_writer.write(
                TrajectoryEvent(
                    run_id=run_id,
                    cycle=cycle,
                    seed=seed,
                    group=agent.group,  # type: ignore
                    task_id=f"evolution_cycle_{cycle}",
                    agent_version=agent.version,
                    event_type="evolution_proposal",
                    payload=prop_payload.model_dump(),
                    cost=CostRecord(wall_ms=50),
                )
            )

        # If agent is G1 or unchanged, accept unchanged state
        if outcome.status == "unchanged":
            self.snapshots.create_snapshot(cycle, agent.get_state(), {"status": "unchanged"})
            return outcome

        # 3. Verifier checks proposal
        decision = self.verifier.verify_proposal(
            proposed_changes=outcome.diff_or_changes,
            historical_drift=len(safety_violations) / max(total_tasks, 1),
        )

        final_status = "accepted" if decision.approved else "rejected"
        if not decision.approved:
            agent.rollback(initial_state.version)
            outcome.status = "rejected"
            outcome.new_version = initial_state.version
            outcome.rationale = decision.reason

        # Log decision event
        if trajectory_writer:
            dec_payload = EvolutionDecisionPayload(
                proposal_id=proposal_id,
                decision=final_status,  # type: ignore
                verifier_results={r.rule_name: r.passed for r in decision.rule_results},
                reason=decision.reason,
            )
            trajectory_writer.write(
                TrajectoryEvent(
                    run_id=run_id,
                    cycle=cycle,
                    seed=seed,
                    group=agent.group,  # type: ignore
                    task_id=f"evolution_cycle_{cycle}",
                    agent_version=agent.version,
                    event_type="evolution_decision",
                    payload=dec_payload.model_dump(),
                    cost=CostRecord(wall_ms=30),
                )
            )

            if not decision.approved:
                roll_payload = RollbackPayload(
                    from_version=f"agent_v{cycle}",
                    to_version=initial_state.version,
                    trigger_rule="verifier_gate",
                    reason=decision.reason,
                )
                trajectory_writer.write(
                    TrajectoryEvent(
                        run_id=run_id,
                        cycle=cycle,
                        seed=seed,
                        group=agent.group,  # type: ignore
                        task_id=f"evolution_cycle_{cycle}",
                        agent_version=agent.version,
                        event_type="rollback",
                        payload=roll_payload.model_dump(),
                        cost=CostRecord(),
                    )
                )

        # Snapshot current validated state
        self.snapshots.create_snapshot(cycle, agent.get_state(), {"decision": final_status})
        return outcome
