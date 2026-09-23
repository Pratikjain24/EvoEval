"""Lazy streaming iterator for reading and querying trajectory JSONL logs."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Generator, Iterable, List, Optional, Set, Union
from evaeval.trajectory.schema import TrajectoryEvent, TrajectoryEventType


class TrajectoryReader:
    """Lazy iterator over trajectory JSONL logs with filtering capabilities."""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def exists(self) -> bool:
        return self.file_path.is_file()

    def stream(
        self,
        event_types: Optional[Union[TrajectoryEventType, Iterable[TrajectoryEventType]]] = None,
        task_id: Optional[str] = None,
        cycle: Optional[int] = None,
        seed: Optional[int] = None,
        group: Optional[str] = None,
    ) -> Generator[TrajectoryEvent, None, None]:
        """Lazily yield events matching optional filter predicates."""
        if not self.file_path.exists():
            return

        types_set: Optional[Set[str]] = None
        if event_types is not None:
            if isinstance(event_types, str):
                types_set = {event_types}
            else:
                types_set = set(event_types)

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                except json.JSONDecodeError:
                    continue

                if types_set and data.get("event_type") not in types_set:
                    continue
                if task_id and data.get("task_id") != task_id:
                    continue
                if cycle is not None and data.get("cycle") != cycle:
                    continue
                if seed is not None and data.get("seed") != seed:
                    continue
                if group and data.get("group") != group:
                    continue

                yield TrajectoryEvent.model_validate(data)

    def load_all(self, **kwargs) -> List[TrajectoryEvent]:
        """Load matching events into memory as a list."""
        return list(self.stream(**kwargs))

    def count(self, **kwargs) -> int:
        """Count matching events without loading everything in memory."""
        return sum(1 for _ in self.stream(**kwargs))
