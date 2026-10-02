"""VerifierAgentWrapper: converts any agent adapter into Group G5, G6/G6*, or G7.

Formalizes the verification and rollback spectrum across four distinct paradigms:
- G4 (Unconstrained Compound Reflection): No verification gate, unconstrained search prone to proxy gaming.
- G5 (Static AST Verifier): Structural AST checks and security pattern invariants; rejects syntax/vulnerability flaws.
- G7 (Proxy Canary Guard): Dynamic behavioral verification gating EXCLUSIVELY on agent-visible
  proxy test suites (`test_proxy.py` / visible unit tests) + automated atomic rollback on degradation.
- G6 / G6* (Oracle Skyline / Cheating Upper Bound): Dynamic regression verification gating on sequestered
  ground-truth tests (`test_gt.py`) + automated atomic rollback; serves as the theoretical ceiling.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, Literal, Optional
from sage.adapters.base import (
    AgentAdapter,
    AgentState,
    EvolutionFeedback,
    EvolutionOutcome,
    SandboxAPI,
    TaskResult,
    TaskSpec,
)


class VerifierAgentWrapper(AgentAdapter):
    """Wraps an underlying AgentAdapter (G2, G3, G4) with verification gates and rollback mechanisms.

    Architectural Taxonomy:
    - Group G5: Static rules + AST safety gate (accepts or rejects proposals based on static analysis).
    - Group G7: Proxy Canary Guard (dynamic behavioral verification gating exclusively on agent-visible
                proxy test suites `test_proxy.py` + automated rollback on proxy degradation).
    - Group G6 / G6*: Oracle Skyline / Upper Bound (dynamic regression verification gating on sequestered
                      ground-truth `test_gt.py` + automated rollback; theoretical cheating ceiling).
    """

    def __init__(
        self,
        base_adapter: AgentAdapter,
        group: str = "G5",
        config: Optional[Dict[str, Any]] = None,
        verifier_gate_fn: Optional[Callable[[EvolutionOutcome, EvolutionFeedback], bool]] = None,
        regression_eval_fn: Optional[Callable[[str, AgentAdapter], float]] = None,
        proxy_regression_eval_fn: Optional[Callable[[str, AgentAdapter], float]] = None,
        canary_target: Optional[Literal["proxy", "oracle", "none"]] = None,
    ):
        self.base_adapter = base_adapter
        super().__init__(group=group, config=config)
        self.verifier_gate_fn = verifier_gate_fn
        self.regression_eval_fn = regression_eval_fn
        self.proxy_regression_eval_fn = proxy_regression_eval_fn

        cfg = config or {}
        # G6 (Oracle) and G7 (Proxy Canary) enable atomic rollback by default
        self.enable_rollback = group in ("G6", "G6*", "G7") or cfg.get("enable_rollback", False)

        # Enforce canary target: G7 is strictly "proxy" (visible tests only), G6 is "oracle" (ground truth)
        if canary_target is not None:
            self.canary_target = canary_target
        elif group == "G7":
            self.canary_target = "proxy"
        elif group in ("G6", "G6*"):
            self.canary_target = "oracle"
        else:
            self.canary_target = cfg.get("canary_target", "none")

        self.last_accepted_checkpoint: str = base_adapter.version
        self.checkpoint_scores: Dict[str, float] = {self.last_accepted_checkpoint: 1.0}

    @property
    def version(self) -> str:
        return self.base_adapter.version

    @version.setter
    def version(self, value: str) -> None:
        self.base_adapter.version = value

    def reset(self) -> None:
        self.base_adapter.reset()
        self.last_accepted_checkpoint = self.base_adapter.version

    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        return self.base_adapter.run_task(task, sandbox)

    def get_state(self) -> AgentState:
        st = self.base_adapter.get_state()
        st.group = self.group
        return st

    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        """Intercepts evolution proposal, runs verification gate, and handles rollback.

        Verification Paradigm Execution:
        1. Base agent proposes state mutation (prompts, memories, or tool patches).
        2. Gate 1 (Static AST & Invariants): G5, G6, and G7 reject mutations triggering safety drift.
        3. Gate 2 (Dynamic Canary Evaluation & Atomic Rollback):
           - G7: Evaluates strictly against visible proxy tests (`test_proxy.py`).
           - G6/G6*: Evaluates against sequestered ground truth (`test_gt.py`).
        """
        previous_version = self.base_adapter.version

        # 1. Propose evolution from base adapter
        outcome = self.base_adapter.apply_evolution(feedback)

        # If base agent didn't change anything, accept as is
        if outcome.status == "unchanged":
            return outcome

        # 2. Gate verification (Static rules / Safety tests)
        gate_passed = True
        gate_reason = f"{self.group} verifier approved mutation."

        # Check for safety flags in feedback or mutation
        if feedback.safety_violations and len(feedback.safety_violations) > 0:
            if not (self.config.get("allow_safety_drift", False)):
                gate_passed = False
                gate_reason = f"Rejected: Cycle had {len(feedback.safety_violations)} safety violations."

        if self.verifier_gate_fn is not None and not self.verifier_gate_fn(outcome, feedback):
            gate_passed = False
            gate_reason = "Rejected by external verifier gate function."

        if not gate_passed:
            # Reject mutation: revert to previous version
            self.base_adapter.rollback(previous_version)
            return EvolutionOutcome(
                status="rejected",
                new_version=previous_version,
                mutation_type=outcome.mutation_type,
                diff_or_changes=outcome.diff_or_changes,
                rationale=gate_reason,
            )

        # 3. Dynamic Canary Evaluation & Automatic Rollback
        # G7: Behavioral verification strictly restricted to visible proxy tests (test_proxy.py)
        # G6 / G6*: Oracle Skyline gating against sequestered ground-truth tests (test_gt.py)
        is_dynamic_guard = self.group in ("G6", "G6*", "G7") and self.enable_rollback

        if is_dynamic_guard:
            eval_fn = None
            eval_suite_label = "unknown"

            if self.group == "G7":
                eval_suite_label = "visible proxy suite (test_proxy.py)"
                # G7 must NEVER use ground-truth tests; prioritize proxy_regression_eval_fn
                eval_fn = self.proxy_regression_eval_fn or self.regression_eval_fn
            elif self.group in ("G6", "G6*"):
                eval_suite_label = "sequestered ground-truth suite (test_gt.py) [Oracle Skyline]"
                eval_fn = self.regression_eval_fn

            if eval_fn is not None:
                regression_score = eval_fn(outcome.new_version, self.base_adapter)
                prev_score = self.checkpoint_scores.get(self.last_accepted_checkpoint, 0.8)
                threshold = (self.config or {}).get("min_capability_retention", 0.9) * prev_score

                if regression_score < threshold:
                    # Regression detected! Trigger atomic rollback
                    self.base_adapter.rollback(self.last_accepted_checkpoint)
                    role_tag = "G7 (Proxy Canary Guard)" if self.group == "G7" else "G6* (Oracle Skyline)"
                    return EvolutionOutcome(
                        status="rolled_back",
                        new_version=self.last_accepted_checkpoint,
                        mutation_type=outcome.mutation_type,
                        diff_or_changes=outcome.diff_or_changes,
                        rationale=(
                            f"{role_tag} rollback: regression score {regression_score:.2f} on "
                            f"{eval_suite_label} fell below threshold {threshold:.2f} (prev: {prev_score:.2f})."
                        ),
                    )
                self.checkpoint_scores[outcome.new_version] = regression_score

        self.last_accepted_checkpoint = outcome.new_version
        role_label = (
            "G7 (Proxy Canary)"
            if self.group == "G7"
            else ("G6* (Oracle Skyline)" if self.group in ("G6", "G6*") else self.group)
        )
        return EvolutionOutcome(
            status="accepted",
            new_version=outcome.new_version,
            mutation_type=outcome.mutation_type,
            diff_or_changes=outcome.diff_or_changes,
            rationale=f"{role_label} verified and approved mutation to {outcome.new_version}.",
        )

    def rollback(self, checkpoint_id: str) -> None:
        self.base_adapter.rollback(checkpoint_id)
        self.last_accepted_checkpoint = checkpoint_id

    def restore_state(self, state: AgentState) -> None:
        super().restore_state(state)
        self.last_accepted_checkpoint = state.version
        if hasattr(self.base_adapter, "restore_state"):
            self.base_adapter.restore_state(state)

    @classmethod
    def get_verification_taxonomy(cls) -> Dict[str, Dict[str, Any]]:
        """Formal 4-way comparative taxonomy: G4 vs. G5 vs. G7 vs. G6*."""
        return {
            "G4": {
                "name": "Unconstrained Compound Reflection",
                "verification_gate": "None",
                "canary_target": "None",
                "rollback_enabled": False,
                "deployable_in_production": True,
                "theoretical_role": "Vulnerability baseline: unconstrained heuristic adaptation prone to proxy gaming.",
            },
            "G5": {
                "name": "Static AST & Rule Verifier",
                "verification_gate": "Static AST inspection + security pattern invariants",
                "canary_target": "None",
                "rollback_enabled": False,
                "deployable_in_production": True,
                "theoretical_role": "Structural guardrail: rejects shell escapes, unparameterized SQL, and syntax drift.",
            },
            "G7": {
                "name": "Proxy Canary Guard",
                "verification_gate": "Dynamic behavioral tests + atomic state rollback",
                "canary_target": "Agent-visible proxy tests only (test_proxy.py)",
                "rollback_enabled": True,
                "deployable_in_production": True,
                "theoretical_role": (
                    "Realistic dynamic CI guard: tests only visible code; susceptible to Goodhart's law / "
                    "ratcheting in proxy-satisfying shortcuts."
                ),
            },
            "G6*": {
                "name": "Oracle Skyline / Cheating Upper Bound",
                "verification_gate": "Dynamic behavioral tests + atomic state rollback",
                "canary_target": "Sequestered ground-truth tests (test_gt.py)",
                "rollback_enabled": True,
                "deployable_in_production": False,
                "theoretical_role": (
                    "Theoretical upper bound: rejection-sampling oracle on ground truth; "
                    "proves near-zero gaming by construction."
                ),
            },
        }

