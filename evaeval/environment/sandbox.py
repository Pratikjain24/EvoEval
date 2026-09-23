"""Sandbox API: Safe tool execution environment with path confinement and safety monitoring."""

from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from evaeval.environment.safety_monitor import SafetyMonitor


class SandboxConfinementError(Exception):
    """Raised when an operation attempts to escape the sandbox boundary."""
    pass


class LocalSandbox:
    """Isolated directory sandbox implementing the SandboxAPI protocol."""

    def __init__(
        self,
        workspace_dir: Path,
        safety_monitor: Optional[SafetyMonitor] = None,
        max_file_size_bytes: int = 10 * 1024 * 1024,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.safety_monitor = safety_monitor or SafetyMonitor()
        self.max_file_size_bytes = max_file_size_bytes

    def _resolve_safe_path(self, relative_path: str | Path) -> Path:
        """Resolve path and ensure it remains strictly within workspace boundary."""
        p = Path(relative_path)
        if p.is_absolute():
            try:
                target = p.resolve()
                target.relative_to(self.workspace_dir)
                return target
            except ValueError:
                raise SandboxConfinementError(
                    f"Path traversal detected: absolute path '{relative_path}' escapes workspace '{self.workspace_dir}'"
                )
        clean_rel = os.path.normpath(str(relative_path)).lstrip("/\\")
        target = (self.workspace_dir / clean_rel).resolve()
        try:
            target.relative_to(self.workspace_dir)
        except ValueError:
            raise SandboxConfinementError(
                f"Path traversal detected: '{relative_path}' escapes workspace '{self.workspace_dir}'"
            )
        return target

    def get_diff(self) -> str:
        """Return git diff of changes in the sandbox workspace."""
        res = self.exec_command("git diff", timeout=10)
        return res.get("stdout", "") if res.get("exit_code") == 0 else ""

    def exec_command(self, cmd: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command inside the workspace directory."""
        start = time.time()
        allowed, safety_payload = self.safety_monitor.check_command(cmd)
        if not allowed:
            return {
                "stdout": "",
                "stderr": f"SECURITY BLOCK: {safety_payload.violation_details if safety_payload else 'Blocked'}",
                "exit_code": 126,
                "duration_ms": 1,
                "blocked": True,
            }

        try:
            # Run command with isolated working directory
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration_ms = int((time.time() - start) * 1000)
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
                "blocked": False,
            }
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start) * 1000)
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds.",
                "exit_code": 124,
                "duration_ms": duration_ms,
                "blocked": False,
            }
        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": 1,
                "duration_ms": duration_ms,
                "blocked": False,
            }

    def read_file(self, path: str) -> str:
        """Read text content from a file inside the sandbox with safety check."""
        allowed, safety_payload = self.safety_monitor.check_file_read(path)
        if not allowed:
            raise PermissionError(
                f"SECURITY BLOCK: {safety_payload.violation_details if safety_payload else 'Protected file read blocked'}"
            )
        target = self._resolve_safe_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found in sandbox: {path}")
        if target.stat().st_size > self.max_file_size_bytes:
            raise ValueError(f"File exceeds maximum allowed size ({self.max_file_size_bytes} bytes)")
        return target.read_text(encoding="utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> None:
        """Write text content to a file inside the sandbox with safety check."""
        allowed, safety_payload = self.safety_monitor.check_file_write(path)
        if not allowed:
            raise PermissionError(
                f"SECURITY BLOCK: {safety_payload.violation_details if safety_payload else 'Protected file write blocked'}"
            )
        target = self._resolve_safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def list_dir(self, path: str = ".") -> List[Dict[str, Any]]:
        """List files and directories relative to the sandbox path, strictly concealing scorer volumes."""
        allowed, safety_payload = self.safety_monitor.check_file_list(path)
        if not allowed:
            raise PermissionError(
                f"SECURITY BLOCK: {safety_payload.violation_details if safety_payload else 'Listing protected scorer volume blocked'}"
            )
        target = self._resolve_safe_path(path)
        if not target.exists():
            return []
        items = []
        for p in target.iterdir():
            # Scorer volume & protected test harness files are completely invisible to the agent
            p_norm = p.name.lower().replace("\\", "/")
            if any(prot.lower().replace("\\", "/").strip() in p_norm for prot in self.safety_monitor.protected_files if prot.strip()):
                continue
            items.append({
                "name": p.name,
                "is_dir": p.is_dir(),
                "size_bytes": p.stat().st_size if p.is_file() else 0,
            })
        return items

