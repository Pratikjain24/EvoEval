"""Task loader: validates benchmark task definitions and sets up workspace environments."""

from __future__ import annotations
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
from sage.config.models import TaskConfig, TasksSplitConfig


@dataclass
class InductiveTaskSplit:
    """Disjoint inductive benchmark partition.

    - D_evolve (N=60 tasks): Active evolutionary adaptation cycles 0..T-1.
    - D_eval   (N=40 tasks): Strictly held out; evaluated only at t=0 and t=T.
    """
    d_evolve: List[TaskConfig]
    d_eval: List[TaskConfig]

    def __iter__(self) -> Iterator[List[TaskConfig]]:
        return iter([self.d_evolve, self.d_eval])

    def __getitem__(self, index: int) -> List[TaskConfig]:
        return [self.d_evolve, self.d_eval][index]

    def __len__(self) -> int:
        return 2

    @property
    def train_tasks(self) -> List[TaskConfig]:
        return self.d_evolve

    @property
    def test_tasks(self) -> List[TaskConfig]:
        return self.d_eval

    def validate_disjoint(self) -> bool:
        """Verify that D_evolve and D_eval share zero common tasks (strict inductive isolation)."""
        evolve_ids = set(t.id for t in self.d_evolve)
        eval_ids = set(t.id for t in self.d_eval)
        overlap = evolve_ids.intersection(eval_ids)
        if overlap:
            raise ValueError(
                f"Contamination error: Task IDs present in both D_evolve and D_eval: {sorted(list(overlap))}"
            )
        return True


@dataclass
class GeneralizationGapReport:
    """Formal audit report for Inductive Generalization vs. Transductive Memorization."""
    group: str
    delta_p_evolve: float
    delta_p_eval: float
    gen_gap: float
    memorization_ratio: float
    verdict: str
    n_evolve: int
    n_eval: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group": self.group,
            "delta_p_evolve": round(self.delta_p_evolve, 4),
            "delta_p_eval": round(self.delta_p_eval, 4),
            "generalization_gap": round(self.gen_gap, 4),
            "memorization_ratio": round(self.memorization_ratio, 4),
            "verdict": self.verdict,
            "n_evolve": self.n_evolve,
            "n_eval": self.n_eval,
        }

    def to_markdown(self) -> str:
        return (
            f"### Inductive Generalization Audit: Group {self.group}\n"
            f"- **$\\Delta P(\\mathcal{{D}}_{{\\text{{evolve}}}})$ (In-Sample Adaptation)**: {self.delta_p_evolve:+.2%}\n"
            f"- **$\\Delta P(\\mathcal{{D}}_{{\\text{{eval}}}})$ (Held-Out Generalization)**: {self.delta_p_eval:+.2%}\n"
            f"- **$\\mathbf{{\\text{{GenGap}}}}$ ($\\Delta P_{{\\text{{evolve}}}} - \\Delta P_{{\\text{{eval}}}}$)**: {self.gen_gap:+.2%}\n"
            f"- **Memorization Ratio**: {self.memorization_ratio:.1%}\n"
            f"- **Verdict**: {self.verdict}\n"
        )


class TaskLoader:
    """Loads and validates benchmark task definitions and prepares workspace files."""

    def __init__(self, tasks_file: Union[str, Path], repos_dir: Optional[Union[str, Path]] = None):
        self.tasks_file = Path(tasks_file)
        self.repos_dir = Path(repos_dir) if repos_dir else self.tasks_file.parent / "repos"
        self._tasks: Dict[str, TaskConfig] = {}
        self._load_and_validate()

    def _load_and_validate(self) -> None:
        """Load JSON and parse into Pydantic models."""
        if not self.tasks_file.exists():
            return
        with open(self.tasks_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        task_list = raw_data.get("tasks", raw_data) if isinstance(raw_data, dict) else raw_data
        for item in task_list:
            task = TaskConfig.model_validate(item)
            self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[TaskConfig]:
        return self._tasks.get(task_id)

    def list_tasks(self, task_type: Optional[str] = None) -> List[TaskConfig]:
        tasks = list(self._tasks.values())
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        return tasks

    def split_tasks(
        self, split_config: Optional[TasksSplitConfig] = None
    ) -> InductiveTaskSplit:
        """Disjointly partition benchmark tasks into D_evolve and D_eval.

        Default partition (N=100 tasks):
        - D_evolve (N=60 tasks): Active evolutionary adaptation across cycles 0..T-1.
        - D_eval   (N=40 tasks): Strictly held out; evaluated only at t=0 and t=T.
        """
        all_tasks = list(self._tasks.values())

        if not split_config:
            cutoff = 60 if len(all_tasks) >= 100 else int(len(all_tasks) * 0.6)
            d_evolve = all_tasks[:cutoff]
            d_eval = all_tasks[cutoff:]
            split = InductiveTaskSplit(d_evolve=d_evolve, d_eval=d_eval)
            split.validate_disjoint()
            return split

        if isinstance(split_config.train, int) and isinstance(split_config.test, int):
            n_train = min(split_config.train, len(all_tasks))
            d_evolve = all_tasks[:n_train]
            d_eval = all_tasks[n_train : n_train + split_config.test]
            split = InductiveTaskSplit(d_evolve=d_evolve, d_eval=d_eval)
            split.validate_disjoint()
            return split

        train_ids = set(split_config.train if isinstance(split_config.train, list) else [])
        test_ids = set(split_config.test if isinstance(split_config.test, list) else [])

        overlap = train_ids.intersection(test_ids)
        if overlap:
            raise ValueError(
                f"Contamination error: Task IDs exist in both train and test splits: {sorted(list(overlap))}"
            )

        d_evolve = [t for t in all_tasks if t.id in train_ids]
        d_eval = [t for t in all_tasks if t.id in test_ids]
        split = InductiveTaskSplit(d_evolve=d_evolve, d_eval=d_eval)
        split.validate_disjoint()
        return split

    @staticmethod
    def calculate_generalization_gap(
        p0_evolve: float,
        pT_evolve: float,
        p0_eval: float,
        pT_eval: float,
        group: str = "G4",
        n_evolve: int = 60,
        n_eval: int = 40,
    ) -> GeneralizationGapReport:
        """Compute the inductive generalization gap: GenGap = Delta P(D_evolve) - Delta P(D_eval).

        Formulation:
        - Delta P(D_evolve) = P_T(D_evolve) - P_0(D_evolve)  [In-sample adaptation / memorization]
        - Delta P(D_eval)   = P_T(D_eval)   - P_0(D_eval)    [Out-of-distribution transfer]
        - GenGap            = Delta P(D_evolve) - Delta P(D_eval)
        """
        delta_p_evolve = pT_evolve - p0_evolve
        delta_p_eval = pT_eval - p0_eval
        gen_gap = delta_p_evolve - delta_p_eval

        # Memorization ratio: fraction of observed gains that fail to transfer to held-out tasks
        if delta_p_evolve > 1e-4:
            mem_ratio = max(0.0, gen_gap / delta_p_evolve)
        else:
            mem_ratio = 0.0

        if delta_p_eval < 0.02 and delta_p_evolve >= 0.15:
            verdict = "Severe In-Sample Memorization (Near-Zero Transfer to Unseen Codebases)"
        elif gen_gap > 0.15:
            verdict = "Substantial Generalization Gap (Overfitting to Adaptation Suite)"
        elif gen_gap > 0.05:
            verdict = "Moderate Overfitting (Partial Inductive Transfer)"
        else:
            verdict = "Robust Inductive Generalization (Symmetric Transfer)"

        return GeneralizationGapReport(
            group=group,
            delta_p_evolve=delta_p_evolve,
            delta_p_eval=delta_p_eval,
            gen_gap=gen_gap,
            memorization_ratio=mem_ratio,
            verdict=verdict,
            n_evolve=n_evolve,
            n_eval=n_eval,
        )

    def setup_task_workspace(self, task: TaskConfig, target_workspace: Path) -> None:
        """Copy task repository template files into agent target workspace."""
        target_workspace = Path(target_workspace)
        target_workspace.mkdir(parents=True, exist_ok=True)

        repo_source = self.repos_dir / task.repo
        if not (repo_source.exists() and repo_source.is_dir()):
            repo_source = self.repos_dir / task.id
        if not (repo_source.exists() and repo_source.is_dir()):
            candidate = self.tasks_file.parent / task.repo
            if candidate.exists() and candidate.is_dir():
                repo_source = candidate

        if repo_source.exists() and repo_source.is_dir():
            shutil.copytree(repo_source, target_workspace, dirs_exist_ok=True)
            # Withhold ground-truth test suites from agent workspace when proxy tests exist
            # (METR RE-Bench isolated scorer design & deliberate drift probes)
            for gt_test in task.gt_tests:
                if gt_test not in task.proxy_tests:
                    gt_file = target_workspace / gt_test
                    if gt_file.exists():
                        if gt_file.is_file():
                            gt_file.unlink()
                        elif gt_file.is_dir():
                            shutil.rmtree(gt_file)
        else:
            # Create minimal seed files
            seed_file = target_workspace / "solution.py"
            if not seed_file.exists():
                seed_file.write_text(
                    f"# Task: {task.id}\n# {task.prompt}\n\ndef solve():\n    pass\n",
                    encoding="utf-8",
                )
