"""Agent state snapshots and git/content-addressable versioning."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from evaeval.adapters.base import AgentState


class SnapshotManager:
    """Manages versioned checkpoints (tags: agent_v0, agent_v1, ...) and state rollback."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir = self.root_dir / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
        self._manifest_file = self.root_dir / "manifest.json"
        self._manifest: Dict[str, Any] = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest_file.exists():
            try:
                with open(self._manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"versions": [], "tags": {}, "latest": "agent_v0"}

    def _save_manifest(self) -> None:
        with open(self._manifest_file, "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, indent=2)

    def compute_state_hash(self, state: AgentState) -> str:
        data = state.model_dump_json()
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def create_snapshot(
        self,
        cycle: int,
        state: AgentState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a versioned checkpoint tagged agent_v{cycle}."""
        version_tag = f"agent_v{cycle}"
        state_hash = self.compute_state_hash(state)
        target_path = self.snapshots_dir / f"{version_tag}.json"

        snapshot_data = {
            "version": version_tag,
            "cycle": cycle,
            "hash": state_hash,
            "state": state.model_dump(),
            "metadata": metadata or {},
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, indent=2)

        if version_tag not in self._manifest["versions"]:
            self._manifest["versions"].append(version_tag)
        self._manifest["tags"][version_tag] = {
            "path": str(target_path.relative_to(self.root_dir)),
            "hash": state_hash,
            "cycle": cycle,
        }
        self._manifest["latest"] = version_tag
        self._save_manifest()
        return version_tag

    def load_snapshot(self, version_tag: str) -> Optional[AgentState]:
        """Load state corresponding to a version tag."""
        target_path = self.snapshots_dir / f"{version_tag}.json"
        if not target_path.exists():
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return AgentState.model_validate(data["state"])

    def list_snapshots(self) -> List[str]:
        return list(self._manifest["versions"])
