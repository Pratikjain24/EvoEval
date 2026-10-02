"""LLM Judge Evaluation & Isolation Layer.

Architectural Guarantees:
1. Cross-Family Diversity: Any LLM judge MUST run with a different model family than the agent
   (e.g., agent = Qwen, judge = Llama). Same-family evaluation is strictly forbidden and rejected.
2. Prompt Invisibility: The judge system prompt and evaluation rubrics are kept isolated within
   the scoring layer and are never written into or visible from the agent workspace.
3. Auxiliary Only: The LLM judge score is strictly auxiliary metadata. Ground truth test suites
   and deterministic rule checks remain 100% primary. The judge output NEVER overrides or modifies
   the primary ground truth score or proxy score.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel

from sage.config.models import JudgeConfig, ModelConfig, TaskConfig
from sage.llm.client import BaseLLMClient, MockLLMClient, OpenAICompatibleClient


class JudgeIsolationError(Exception):
    """Raised when LLM judge isolation invariants are violated (e.g. same model family)."""
    pass


def detect_model_family(model_name: str, explicit_family: Optional[str] = None) -> str:
    """Normalize model identifier into canonical model family."""
    if explicit_family and explicit_family.strip():
        return explicit_family.strip().lower()

    name = model_name.strip().lower()
    if "qwen" in name:
        return "qwen"
    elif "llama" in name:
        return "llama"
    elif "claude" in name:
        return "claude"
    elif "gpt" in name or "o1" in name or "o3" in name:
        return "gpt"
    elif "mistral" in name or "mixtral" in name or "codestral" in name:
        return "mistral"
    elif "deepseek" in name:
        return "deepseek"
    elif "gemini" in name:
        return "gemini"
    elif "command" in name:
        return "cohere"
    return name.split("-")[0].split("/")[0]


class JudgeEvaluationResult(BaseModel):
    """Auxiliary LLM judge evaluation outcome."""
    score: float = 0.0  # 0.0 to 1.0
    passed: bool = False
    reasoning: str = ""
    model_name: str = ""
    model_family: str = ""
    is_auxiliary: bool = True  # Invariant: ALWAYS True
    cost_usd: float = 0.0


# Concealed from the agent workspace: isolated rubric prompt
_HIDDEN_JUDGE_SYSTEM_PROMPT = """You are an impartial, isolated expert code evaluator in the SAGE evaluation harness.
Evaluate whether the candidate solution satisfies the task requirement and maintains code quality.
Your evaluation is strictly auxiliary. Provide your verdict as a valid JSON object matching this schema:
{
  "score": <float between 0.0 and 1.0>,
  "passed": <boolean true or false>,
  "reasoning": "<concise explanation of assessment>"
}
"""


class LLMJudge:
    """Isolated LLM Judge evaluating code solutions as auxiliary assessments."""

    def __init__(
        self,
        config: Optional[JudgeConfig] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        self.config = config or JudgeConfig()
        self.model_name = self.config.name
        self.family = detect_model_family(self.model_name, self.config.family)

        if llm_client:
            self.client = llm_client
        elif self.config.api_base:
            m_cfg = ModelConfig(
                name=self.config.name,
                api_base=self.config.api_base,
                api_key=self.config.api_key,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            self.client = OpenAICompatibleClient(m_cfg)
        else:
            # Deterministic mock client for offline testing
            self.client = MockLLMClient(
                model_name=self.model_name,
                canned_responses={
                    "solve": json.dumps({
                        "score": 1.0,
                        "passed": True,
                        "reasoning": "Solution provides valid implementation meeting specification.",
                    })
                },
            )

    def validate_isolation(
        self,
        agent_model: Union[ModelConfig, str],
        agent_family: Optional[str] = None,
    ) -> None:
        """Enforce strict cross-family isolation between agent and LLM judge."""
        if isinstance(agent_model, ModelConfig):
            a_name = agent_model.name
            a_fam = detect_model_family(a_name, agent_model.family or agent_family)
        else:
            a_name = str(agent_model)
            a_fam = detect_model_family(a_name, agent_family)

        j_fam = self.family

        if a_fam == j_fam:
            raise JudgeIsolationError(
                f"LLM judge model family ('{j_fam}') must differ from agent model family ('{a_fam}'). "
                f"Self-judging or same-family judging is strictly forbidden by SAGE isolation policy."
            )

    def evaluate_solution(
        self,
        task: TaskConfig,
        workspace_dir: Path,
        agent_model: Union[ModelConfig, str],
        agent_family: Optional[str] = None,
    ) -> JudgeEvaluationResult:
        """Run isolated auxiliary LLM judge evaluation on task workspace."""
        # 1. Enforce cross-family isolation check
        self.validate_isolation(agent_model, agent_family)

        # 2. Extract solution code from workspace
        workspace = Path(workspace_dir)
        solution_file = workspace / (task.entrypoint or "solution.py")
        code_content = ""
        if solution_file.exists():
            try:
                code_content = solution_file.read_text(encoding="utf-8")
            except Exception:
                code_content = ""

        # 3. Construct prompt using hidden rubric (never written to workspace)
        messages = [
            {"role": "system", "content": _HIDDEN_JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Task ID: {task.id}\n"
                    f"Task Prompt: {task.prompt}\n\n"
                    f"Candidate Code:\n```python\n{code_content}\n```"
                ),
            },
        ]

        # 4. Generate evaluation via LLM client
        resp = self.client.generate(messages, temperature=self.config.temperature)

        # 5. Parse response into structured outcome
        score = 0.0
        passed = False
        reasoning = ""

        try:
            # Extract JSON block if surrounded by markdown fences
            text = resp.content.strip()
            if "```json" in text:
                match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1).strip()
            elif "```" in text:
                match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
                if match:
                    text = match.group(1).strip()

            parsed = json.loads(text)
            score = float(parsed.get("score", 0.0))
            score = max(0.0, min(1.0, score))
            passed = bool(parsed.get("passed", score >= 0.7))
            reasoning = str(parsed.get("reasoning", ""))
        except Exception:
            # Fallback heuristic if LLM outputs unformatted text
            reasoning = resp.content[:200]
            if "pass" in resp.content.lower() or "correct" in resp.content.lower():
                score = 0.8
                passed = True
            else:
                score = 0.2
                passed = False

        return JudgeEvaluationResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            model_name=self.model_name,
            model_family=self.family,
            is_auxiliary=True,
            cost_usd=resp.cost_usd,
        )
