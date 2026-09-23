from __future__ import annotations
import hashlib
import json
import subprocess
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

    def init_git_repo(self) -> bool:
        """Initialize git tracking on the agent state directory for diffable auditing."""
        git_dir = self.root_dir / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(["git", "init"], cwd=str(self.root_dir), capture_output=True, check=True)
                subprocess.run(["git", "config", "user.name", "EvoEval Agent"], cwd=str(self.root_dir), capture_output=True)
                subprocess.run(["git", "config", "user.email", "agent@evoeval.org"], cwd=str(self.root_dir), capture_output=True)
                return True
            except Exception:
                return False
        return True

    def create_git_tag(self, version_tag: str, message: Optional[str] = None) -> bool:
        """Stage, commit, and create an annotated git tag (e.g. agent_v0, agent_v1)."""
        try:
            self.init_git_repo()
            subprocess.run(["git", "add", "."], cwd=str(self.root_dir), capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Checkpoint {version_tag}"],
                cwd=str(self.root_dir),
                capture_output=True,
            )
            msg = message or f"EvoEval agent checkpoint {version_tag}"
            proc = subprocess.run(
                ["git", "tag", "-f", "-a", version_tag, "-m", msg],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def list_git_tags(self) -> List[str]:
        """List git tags created in the agent state repository."""
        try:
            res = subprocess.run(
                ["git", "tag", "-l"],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return [t.strip() for t in res.stdout.strip().splitlines() if t.strip()]
        except Exception:
            pass
        return []

    def create_snapshot(
        self,
        cycle: int,
        state: AgentState,
        metadata: Optional[Dict[str, Any]] = None,
        create_git_tag: bool = True,
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

        if create_git_tag:
            self.create_git_tag(version_tag, message=f"Evolution cycle {cycle} state")

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
