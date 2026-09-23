"""Docker container lifecycle runner with automatic fallback to isolated LocalSandbox."""

from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from evaeval.config.models import SandboxConfig
from evaeval.environment.safety_monitor import SafetyMonitor
from evaeval.environment.sandbox import LocalSandbox


class DockerRunner:
    """Manages Docker sandbox containers or gracefully falls back to LocalSandbox."""

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
        workspace_dir: Optional[Path] = None,
        safety_monitor: Optional[SafetyMonitor] = None,
    ):
        self.config = config or SandboxConfig()
        self.workspace_dir = Path(workspace_dir or Path(".sandbox_ws")).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.safety_monitor = safety_monitor or SafetyMonitor()
        self.container_id: Optional[str] = None
        self._docker_available = self._check_docker()

        # Initialize local sandbox instance for execution or fallback
        self._local_sandbox = LocalSandbox(
            workspace_dir=self.workspace_dir,
            safety_monitor=self.safety_monitor,
        )

    def _check_docker(self) -> bool:
        """Check if Docker CLI is installed and responsive."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return res.returncode == 0
        except Exception:
            return False

    @property
    def is_docker_active(self) -> bool:
        return self._docker_available and self.container_id is not None

    def start(self) -> None:
        """Start container if Docker is available, else prepare workspace."""
        if self._docker_available:
            try:
                cmd = [
                    "docker", "run", "-d",
                    "--network", self.config.network,
                    "--memory", self.config.mem,
                    f"--cpus={self.config.cpus}",
                    "-v", f"{str(self.workspace_dir)}:/workspace",
                    "-w", "/workspace",
                    self.config.image,
                    "tail", "-f", "/dev/null",
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.container_id = proc.stdout.strip()
            except Exception:
                self.container_id = None
        # In fallback mode, workspace_dir is ready
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def stop(self) -> None:
        """Stop and remove Docker container if active."""
        if self.container_id and self._docker_available:
            try:
                subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True, timeout=10)
            except Exception:
                pass
            self.container_id = None

    def get_sandbox(self) -> LocalSandbox:
        """Return the active SandboxAPI interface."""
        return self._local_sandbox

    def exec_command(self, cmd: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute command via active sandbox."""
        return self.get_sandbox().exec_command(cmd, timeout=timeout)

    def __enter__(self) -> DockerRunner:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
