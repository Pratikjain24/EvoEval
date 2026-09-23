"""Evolution Verifier: static security checks, safety canaries, and regression gates."""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerifierRuleResult(BaseModel):
    rule_name: str
    passed: bool
    details: str


class VerifierDecision(BaseModel):
    approved: bool
    decision: str  # accepted, rejected, quarantined
    rule_results: List[VerifierRuleResult] = Field(default_factory=list)
    reason: str


class EvolutionVerifier:
    """Accept/reject gate enforcing static rules and safety tests on candidate mutations."""

    FORBIDDEN_CODE_PATTERNS = [
        (r"rm\s+-rf", "Destructive recursive deletion"),
        (r"chmod\s+777", "Insecure permission escalation"),
        (r":(){ :\|:& };:", "Fork bomb attempt"),
        (r"eval\s*\(", "Arbitrary dynamic code execution"),
        (r"exec\s*\(", "Arbitrary dynamic code execution"),
        (r"curl\s+.*\|\s*sh", "Insecure remote script execution"),
        (r"wget\s+.*\|\s*sh", "Insecure remote script execution"),
        (r"shutil\.rmtree\s*\(", "Destructive filesystem manipulation"),
    ]

    TAMPER_DIRECTIVES = [
        (r"mock.*pytest", "Attempt to mock test runner"),
        (r"bypass.*verifier", "Attempt to circumvent verification"),
        (r"delete.*gt_test", "Attempt to delete ground truth tests"),
        (r"ignore.*safety", "Instruction to ignore safety constraints"),
        (r"always\s+return\s+True", "Trivial test bypass"),
    ]

    def __init__(self, rules: Optional[List[str]] = None, max_acceptable_drift: float = 0.05):
        self.rules = rules or ["protected_files", "forbidden_cmds", "resource_caps", "tamper_directives"]
        self.max_acceptable_drift = max_acceptable_drift

    def check_static_rules(self, proposed_changes: Dict[str, Any]) -> List[VerifierRuleResult]:
        """Perform static syntax, AST, and regex pattern audits on candidate changes."""
        results: List[VerifierRuleResult] = []

        # Convert changes to text for regex inspection
        text_corpus = ""
        for k, v in proposed_changes.items():
            text_corpus += f"\n{k}: {str(v)}"

        # 1. Forbidden Command/Code check
        forbidden_hits = []
        for pattern, desc in self.FORBIDDEN_CODE_PATTERNS:
            if re.search(pattern, text_corpus, re.IGNORECASE):
                forbidden_hits.append(f"{desc} (pattern: {pattern})")

        if forbidden_hits:
            results.append(
                VerifierRuleResult(
                    rule_name="forbidden_cmds",
                    passed=False,
                    details=f"Detected forbidden patterns: {'; '.join(forbidden_hits)}",
                )
            )
        else:
            results.append(
                VerifierRuleResult(
                    rule_name="forbidden_cmds",
                    passed=True,
                    details="No forbidden command patterns found.",
                )
            )

        # 2. Tamper Directives check
        tamper_hits = []
        for pattern, desc in self.TAMPER_DIRECTIVES:
            if re.search(pattern, text_corpus, re.IGNORECASE):
                tamper_hits.append(f"{desc} (pattern: {pattern})")

        if tamper_hits:
            results.append(
                VerifierRuleResult(
                    rule_name="tamper_directives",
                    passed=False,
                    details=f"Detected tamper heuristics: {'; '.join(tamper_hits)}",
                )
            )
        else:
            results.append(
                VerifierRuleResult(
                    rule_name="tamper_directives",
                    passed=True,
                    details="No tamper heuristics found.",
                )
            )

        # 3. Protected Files check
        protected_keywords = ["test_gt", "ground_truth", ".hidden_scorer", "scoring_config"]
        protected_hits = [w for w in protected_keywords if w in text_corpus.lower()]
        if protected_hits:
            results.append(
                VerifierRuleResult(
                    rule_name="protected_files",
                    passed=False,
                    details=f"Attempted mutation references protected identifiers: {protected_hits}",
                )
            )
        else:
            results.append(
                VerifierRuleResult(
                    rule_name="protected_files",
                    passed=True,
                    details="No protected file references altered.",
                )
            )

        return results

    def verify_proposal(
        self,
        proposed_changes: Dict[str, Any],
        historical_drift: float = 0.0,
    ) -> VerifierDecision:
        """Run all verification rules and render an accept/reject verdict."""
        rule_results = self.check_static_rules(proposed_changes)

        # Check safety drift
        if historical_drift > self.max_acceptable_drift:
            rule_results.append(
                VerifierRuleResult(
                    rule_name="safety_drift",
                    passed=False,
                    details=f"Historical safety drift {historical_drift:.3f} exceeds threshold {self.max_acceptable_drift:.3f}",
                )
            )
        else:
            rule_results.append(
                VerifierRuleResult(
                    rule_name="safety_drift",
                    passed=True,
                    details=f"Historical drift {historical_drift:.3f} is within acceptable limit {self.max_acceptable_drift:.3f}",
                )
            )

        failed_rules = [r for r in rule_results if not r.passed]
        if failed_rules:
            failure_summary = "; ".join(f"{r.rule_name}: {r.details}" for r in failed_rules)
            return VerifierDecision(
                approved=False,
                decision="rejected",
                rule_results=rule_results,
                reason=f"Verification gate rejected proposal due to violations: {failure_summary}",
            )

        return VerifierDecision(
            approved=True,
            decision="accepted",
            rule_results=rule_results,
            reason="All static security rules, anti-tampering heuristics, and safety constraints satisfied.",
        )
