"""Task loader: validates benchmark task definitions and sets up workspace environments."""

from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from evaeval.config.models import TaskConfig, TasksSplitConfig


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
    ) -> Tuple[List[TaskConfig], List[TaskConfig]]:
        """Split available tasks into train and test subsets."""
        all_tasks = list(self._tasks.values())
        if not split_config:
            cutoff = int(len(all_tasks) * 0.6)
            return all_tasks[:cutoff], all_tasks[cutoff:]

        if isinstance(split_config.train, int) and isinstance(split_config.test, int):
            n_train = min(split_config.train, len(all_tasks))
            train_set = all_tasks[:n_train]
            test_set = all_tasks[n_train : n_train + split_config.test]
            return train_set, test_set

        train_ids = set(split_config.train if isinstance(split_config.train, list) else [])
        test_ids = set(split_config.test if isinstance(split_config.test, list) else [])

        train_set = [t for t in all_tasks if t.id in train_ids]
        test_set = [t for t in all_tasks if t.id in test_ids]
        return train_set, test_set

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
