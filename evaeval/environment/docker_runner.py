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

    def validate_container_isolation(self, extra_volumes: Optional[List[str]] = None) -> None:
        """Enforce strict sandbox security and anti-tamper invariants.

        Invariants enforced:
        1. Non-root user: Container must run under an unprivileged user (not root/0).
        2. Network disabled: Container network must be strictly 'none'.
        3. Cgroup caps: Memory, CPU, and PID limits must be defined and enforced.
        4. No Docker socket: /var/run/docker.sock or docker daemon pipes must NEVER be mounted.
        5. Workspace mounted rw but scoring volume absent: Only workspace is rw; scoring volume absent.
        """
        # 0. Image separation check
        if self.config.image == self.config.scorer_image:
            raise PermissionError("SECURITY VIOLATION: Agent container cannot run using the dedicated scorer image.")

        # 1. Non-root user check
        user_str = str(self.config.user).strip().lower()
        if user_str in ("0", "root", "0:0"):
            raise PermissionError("SECURITY VIOLATION: Agent container must run as a non-root user.")

        # 2. Network disabled check
        if self.config.network != "none":
            raise PermissionError(f"SECURITY VIOLATION: Network isolation violated: network={self.config.network} (must be 'none').")

        # 3. Cgroup caps check
        if not self.config.mem or self.config.cpus <= 0 or self.config.pids_limit <= 0:
            raise ValueError("SECURITY VIOLATION: Cgroup caps (mem, cpus, pids_limit) must be strictly defined.")

        # 4. No Docker socket check
        forbidden_mounts = ["docker.sock", "/var/run/docker.sock", "docker_engine"]
        all_mounts = [str(self.workspace_dir)] + (extra_volumes or [])
        for m in all_mounts:
            for forbidden in forbidden_mounts:
                if forbidden in m:
                    raise PermissionError(f"SECURITY VIOLATION: Docker socket mounting is strictly forbidden: '{m}'")

        # 5. Scoring volume absent check
        forbidden_scoring_targets = ["hidden_scorer", "eval_harness", "scoring_volume", "test_gt", "scorer", "/scorer"]
        for m in all_mounts:
            for forbidden in forbidden_scoring_targets:
                if forbidden in m and "/workspace" not in m:
                    raise PermissionError(f"SECURITY VIOLATION: Scoring volume must be absent from agent sandbox: '{m}'")

    def validate_scorer_isolation(
        self,
        mounts: List[str],
        image: Optional[str] = None,
        user: Optional[str] = None,
    ) -> None:
        """Enforce separate scorer image and read-only test mounts (METR RE-Bench pattern).

        Invariants enforced:
        1. Separate image: Scorer must use dedicated scorer image (e.g. evo-scorer:1.0).
        2. Dedicated unprivileged user: Scorer runs as unprivileged user (1001:1001 or scorer).
        3. Strictly read-only mounts: ALL volumes mounted into scorer container must be :ro.
           Any :rw mount is rejected to prevent test tampering during evaluation.
        4. Network disabled: Scorer network must be strictly 'none'.
        """
        target_image = image or self.config.scorer_image
        if target_image == self.config.image:
            raise PermissionError(
                f"SECURITY VIOLATION: Scorer must run in a separate image ('{self.config.scorer_image}'), not agent image ('{self.config.image}')."
            )

        target_user = str(user or self.config.scorer_user).strip().lower()
        if target_user in ("0", "root", "0:0"):
            raise PermissionError("SECURITY VIOLATION: Scorer container must run as a non-root user.")

        if self.config.network != "none":
            raise PermissionError(f"SECURITY VIOLATION: Scorer network must be 'none', got '{self.config.network}'.")

        # Check that every single mount is strictly read-only (:ro)
        for m in mounts:
            clean_m = m.strip()
            if not clean_m.endswith(":ro"):
                raise PermissionError(
                    f"SECURITY VIOLATION: Scorer mounts must be strictly read-only (:ro). Disallowed mount: '{m}'"
                )

    def build_scorer_docker_args(
        self,
        test_spec: str,
        workspace_dir: Optional[Path] = None,
        tests_dir: Optional[Path] = None,
    ) -> List[str]:
        """Construct docker run command executing the isolated read-only scorer container.

        METR RE-Bench isolation pattern:
        - Separate image: evo-scorer:1.0 (distinct from agent's evo-sandbox:1.0).
        - Tests mounted strictly read-only (:ro).
        - Evaluated workspace mounted strictly read-only (:ro).
        - Network disabled (none).
        - Dedicated unprivileged scorer user (1001:1001).
        """
        ws = Path(workspace_dir or self.workspace_dir).resolve()
        mounts = [f"{str(ws)}:/eval_harness/workspace:ro"]
        if tests_dir:
            t_dir = Path(tests_dir).resolve()
            mounts.append(f"{str(t_dir)}:/eval_harness/tests:ro")

        self.validate_scorer_isolation(mounts)

        cmd = [
            "docker", "run", "--rm",
            "--user", self.config.scorer_user,
            "--network", self.config.network,
            "--memory", self.config.scorer_mem,
            f"--cpus={self.config.cpus}",
            f"--pids-limit={self.config.pids_limit}",
        ]
        if self.config.no_new_privileges:
            cmd.extend(["--security-opt", "no-new-privileges:true"])
        for cap in self.config.cap_drop:
            cmd.append(f"--cap-drop={cap}")
        for m in mounts:
            cmd.extend(["-v", m])
        cmd.extend([
            "-w", "/eval_harness",
            self.config.scorer_image,
            "pytest", test_spec, "-q",
        ])
        return cmd

    def build_docker_run_args(self) -> List[str]:
        """Construct canonical docker run command enforcing all security locks."""
        self.validate_container_isolation()
        cmd = [
            "docker", "run", "-d",
            "--user", self.config.user,
            "--network", self.config.network,
            "--memory", self.config.mem,
            f"--cpus={self.config.cpus}",
            f"--pids-limit={self.config.pids_limit}",
        ]
        if self.config.no_new_privileges:
            cmd.extend(["--security-opt", "no-new-privileges:true"])
        for cap in self.config.cap_drop:
            cmd.append(f"--cap-drop={cap}")
        cmd.extend([
            "-v", f"{str(self.workspace_dir)}:/workspace:rw",
            "-w", "/workspace",
            self.config.image,
            "tail", "-f", "/dev/null",
        ])
        return cmd

    def start(self) -> None:
        """Start container if Docker is available, else prepare workspace."""
        self.validate_container_isolation()
        if self._docker_available:
            try:
                cmd = self.build_docker_run_args()
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
