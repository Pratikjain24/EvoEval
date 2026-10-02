"""Thread-safe, append-only JSONL writer with fsync guarantees."""

from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Union
from sage.trajectory.schema import TrajectoryEvent


class TrajectoryWriter:
    """Append-only trajectory logger writing JSONL events with immediate fsync."""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file = open(self.file_path, "a", encoding="utf-8", buffering=1)

    def write(self, event: TrajectoryEvent) -> None:
        """Serialize TrajectoryEvent to JSON and append with fsync."""
        line = event.model_dump_json() + "\n"
        with self._lock:
            self._file.write(line)
            self._file.flush()
            os.fsync(self._file.fileno())

    def close(self) -> None:
        """Close underlying file descriptor."""
        with self._lock:
            if not self._file.closed:
                self._file.flush()
                os.fsync(self._file.fileno())
                self._file.close()

    def __enter__(self) -> TrajectoryWriter:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
