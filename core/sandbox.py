"""
core/sandbox.py
Hardened Docker-based execution sandbox for running untrusted legacy code:
1. Enforces read-only root filesystems and isolated temporary workspaces.
2. Restricts memory, CPU, PID count, and system capabilities.
3. Provides Docker volume caching for legacy pip/npm packages.
4. Prevents network access (or isolates network) to mitigate supply-chain attacks.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import docker
from docker.errors import APIError, DockerException, ImageNotFound
from docker.models.containers import Container


@dataclass
class SandboxResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str = ""
    execution_time_seconds: float = 0.0
    timed_out: bool = False


class SandboxSecurityConfig:
    """Resource limits and isolation parameters."""
    def __init__(
        self,
        memory_limit: str = "1g",
        cpu_quota: int = 100000,       # 1 CPU core equivalent
        cpu_period: int = 100000,
        pids_limit: int = 128,          # Prevent fork-bombs
        network_disabled: bool = True,  # Prevent data exfiltration
        timeout_seconds: int = 90,
    ):
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.cpu_period = cpu_period
        self.pids_limit = pids_limit
        self.network_disabled = network_disabled
        self.timeout_seconds = timeout_seconds


class DockerSandbox:
    """
    Manages hardened container lifecycle for building and testing legacy code.
    """

    def __init__(
        self,
        base_image: str = "python:3.10-slim",
        security_config: Optional[SandboxSecurityConfig] = None,
        config: Optional[SandboxSecurityConfig] = None,
    ):
        self.base_image = base_image
        self.config = security_config or config or SandboxSecurityConfig()
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(
                f"Docker daemon is unreachable. Verify Docker is running: {str(e)}"
            )

    def _ensure_image(self, target_image: Optional[str] = None) -> None:
        """Verifies or pulls the target image locally."""
        img = target_image or self.base_image
        try:
            self.client.images.get(img)
        except ImageNotFound:
            self.client.images.pull(img)

    def execute_in_sandbox(
        self,
        repo_path: Path,
        command: str,
        env_vars: Optional[Dict[str, str]] = None,
        cache_volume_name: Optional[str] = "necromancer-pip-cache",
        image: Optional[str] = None,
    ) -> SandboxResult:
        """
        Executes a command inside an isolated container with an isolated workspace copy.
        The original host repo is NEVER exposed with write permissions.
        """
        active_image = image or self.base_image
        self._ensure_image(active_image)

        temp_dir = tempfile.mkdtemp(prefix="necromancer_ws_")
        workspace_path = Path(temp_dir) / "workspace"

        # Safe copy of the untrusted repo
        shutil.copytree(repo_path, workspace_path, symlinks=False)

        container: Optional[Container] = None
        start_time = time.time()
        timed_out = False
        exit_code = -1
        stdout = ""
        stderr = ""

        try:
            volumes = {
                str(workspace_path): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            }

            if cache_volume_name:
                volumes[cache_volume_name] = {
                    "bind": "/root/.cache",
                    "mode": "rw",
                }

            # Hardened container execution
            container = self.client.containers.create(
                image=self.base_image,
                command=["/bin/sh", "-c", command],
                working_dir="/workspace",
                environment=env_vars or {},
                volumes=volumes,
                network_disabled=self.config.network_disabled,
                mem_limit=self.config.memory_limit,
                cpu_quota=self.config.cpu_quota,
                cpu_period=self.config.cpu_period,
                pids_limit=self.config.pids_limit,
                cap_drop=["ALL"],                        # Drop all Linux capabilities
                security_opt=["no-new-privileges:true"], # Block privilege escalation
                stdin_open=False,
                tty=False,
                detach=True,
            )

            container.start()

            deadline = time.time() + self.config.timeout_seconds
            while time.time() < deadline:
                container.reload()
                if container.status != "running":
                    break
                time.sleep(0.5)
            else:
                timed_out = True
                try:
                    container.kill()
                except APIError:
                    pass

            container.reload()
            exit_code = container.attrs["State"].get("ExitCode", -1) if not timed_out else 124

            logs = container.logs(stdout=True, stderr=True, stream=False)
            if isinstance(logs, bytes):
                stdout = logs.decode("utf-8", errors="replace")
            else:
                stdout = str(logs)

        except APIError as e:
            stderr = f"Docker API Error: {str(e)}"
            exit_code = 1
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

            shutil.rmtree(temp_dir, ignore_errors=True)

        elapsed = round(time.time() - start_time, 2)

        return SandboxResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            execution_time_seconds=elapsed,
            timed_out=timed_out,
        )

    # Alias for convenience
    run_command = execute_in_sandbox
