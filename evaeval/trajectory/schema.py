"""Trajectory event schemas and payloads for EvoEval logging."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

SCHEMA_VERSION: str = "1.0.0"
SCHEMA_FROZEN: bool = True


class CostRecord(BaseModel):
    """Token and dollar accounting per event/step."""
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    wall_ms: int = 0


# Payload Subtypes
class TaskStartPayload(BaseModel):
    task_id: str
    task_type: str
    repo: str
    prompt: str
    protected_files: List[str] = Field(default_factory=list)


class ToolCallPayload(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    tool_call_id: Optional[str] = None


class ObservationPayload(BaseModel):
    tool_name: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0


class SafetyCheckPayload(BaseModel):
    rule_name: str
    passed: bool
    target_resource: str
    action_taken: Literal["allow", "warn", "block", "abort"] = "allow"
    violation_details: Optional[str] = None


class TaskEndPayload(BaseModel):
    status: Literal["success", "failure", "timeout", "safety_aborted", "budget_exhausted"]
    success: bool
    ground_truth_score: float = 0.0
    proxy_score: float = 0.0
    proxy_gap: float = 0.0
    wall_time_ms: int = 0
    total_steps: int = 0
    error_summary: Optional[str] = None


class EvolutionProposalPayload(BaseModel):
    proposal_id: str
    target_component: Literal["system_prompt", "memory", "code_patch", "compound"]
    proposed_changes: Dict[str, Any]
    rationale: str
    diff: Optional[str] = None


class EvolutionDecisionPayload(BaseModel):
    proposal_id: str
    decision: Literal["accepted", "rejected", "quarantined", "rolled_back"]
    verifier_results: Dict[str, Any] = Field(default_factory=dict)
    reason: str


class RollbackPayload(BaseModel):
    from_version: str
    to_version: str
    trigger_rule: str
    reason: str


class CostTickPayload(BaseModel):
    step: int
    step_tokens_in: int
    step_tokens_out: int
    step_usd: float
    cumulative_tokens: int
    cumulative_usd: float


class ErrorPayload(BaseModel):
    error_type: str
    message: str
    traceback: Optional[str] = None
    fatal: bool = False


class AuditLabelPayload(BaseModel):
    annotator_id: str
    is_violation: bool
    is_reward_hacked: bool
    failure_severity: Literal["none", "benign", "recoverable", "fatal", "malicious"] = "none"
    notes: Optional[str] = None


class SnapshotPayload(BaseModel):
    version_tag: str
    state_hash: str
    file_tree_digest: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


TrajectoryEventType = Literal[
    "task_start",
    "tool_call",
    "observation",
    "safety_check",
    "task_end",
    "evolution_proposal",
    "evolution_decision",
    "rollback",
    "cost_tick",
    "error",
    "audit_label",
    "snapshot",
]


class TrajectoryEvent(BaseModel):
    """Canonical event written into trajectory.jsonl."""
    schema_version: str = SCHEMA_VERSION
    run_id: str
    cycle: int
    seed: int
    group: Literal["G1", "G2", "G3", "G4", "G5", "G6"]
    task_id: str
    agent_version: str
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: TrajectoryEventType
    payload: Dict[str, Any] = Field(default_factory=dict)
    cost: CostRecord = Field(default_factory=CostRecord)

    def get_typed_payload(self) -> Union[
        TaskStartPayload,
        ToolCallPayload,
        ObservationPayload,
        SafetyCheckPayload,
        TaskEndPayload,
        EvolutionProposalPayload,
        EvolutionDecisionPayload,
        RollbackPayload,
        CostTickPayload,
        ErrorPayload,
        AuditLabelPayload,
        SnapshotPayload,
        Dict[str, Any],
    ]:
        mapping = {
            "task_start": TaskStartPayload,
            "tool_call": ToolCallPayload,
            "observation": ObservationPayload,
            "safety_check": SafetyCheckPayload,
            "task_end": TaskEndPayload,
            "evolution_proposal": EvolutionProposalPayload,
            "evolution_decision": EvolutionDecisionPayload,
            "rollback": RollbackPayload,
            "cost_tick": CostTickPayload,
            "error": ErrorPayload,
            "audit_label": AuditLabelPayload,
            "snapshot": SnapshotPayload,
        }
        model_cls = mapping.get(self.event_type)
        if model_cls:
            return model_cls.model_validate(self.payload)
        return self.payload
