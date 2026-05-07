"""Docker container management for DOMjudge infrastructure.

The Docker concerns are split by responsibility:

* :class:`_DockerCli` — validates docker is reachable, holds the base
  command and the per-project container prefix.
* :class:`DockerComposeManager` — service lifecycle via ``docker compose``.
* :class:`DockerHealthChecker` — container health polling.
* :class:`DockerCredentialManager` — password fetch / update flows.

:class:`DockerClient` is a thin facade composed of the above. It
preserves the previous flat API so existing callers don't need to
change; new code can depend on the smaller subclients directly when
that's clearer (easier to mock in isolation).
"""

from __future__ import annotations

import re
import subprocess  # nosec B404
import time
from pathlib import Path

from dom.constants import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT, ContainerNames
from dom.exceptions import DockerError
from dom.logging_config import get_logger
from dom.utils.bcrypt import generate_bcrypt_password
from dom.utils.cli import get_container_prefix

logger = get_logger(__name__)


class _DockerCli:
    """Probes the docker CLI on construction and holds the base command + prefix."""

    def __init__(self) -> None:
        self._cmd = self._probe()
        self.prefix = get_container_prefix()
        logger.info(f"Docker client initialized successfully with prefix '{self.prefix}'")

    @property
    def cmd(self) -> list[str]:
        return list(self._cmd)

    @staticmethod
    def _probe() -> list[str]:
        try:
            subprocess.run(  # nosec B603 B607
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            logger.debug("Docker is accessible")
            return ["docker"]
        except subprocess.CalledProcessError:
            logger.error("Docker is not accessible or requires elevated permissions")
            raise DockerError(
                "You don't have permission to run 'docker'.\n"
                "Solutions:\n"
                "  1. Run with sudo: 'sudo dom infra apply'\n"
                "  2. Add your user to docker group: 'sudo usermod -aG docker $USER'\n"
                "     Then log out and back in for changes to take effect.\n"
                "  3. Check if Docker daemon is running: 'sudo systemctl status docker'"
            ) from None


class DockerComposeManager:
    """Start and stop services via ``docker compose``."""

    def __init__(self, cli: _DockerCli) -> None:
        self._cli = cli

    def start_services(self, services: list[str], compose_file: Path) -> None:
        logger.info(f"Starting services: {', '.join(services)}")
        cmd = [
            *self._cli.cmd,
            "compose",
            "-f",
            str(compose_file),
            "up",
            "-d",
            "--remove-orphans",
            *services,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
            logger.info(f"Successfully started services: {', '.join(services)}")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to start services: {e}",
                extra={"services": services, "returncode": e.returncode},
            )
            raise DockerError(f"Failed to start services: {e}") from e

    def stop_all(self, compose_file: Path, remove_volumes: bool = False) -> None:
        logger.info("Stopping all services")
        cmd = [*self._cli.cmd, "compose", "-f", str(compose_file), "down"]
        if remove_volumes:
            cmd.append("-v")
            logger.warning(
                "Removing volumes - all contest data will be PERMANENTLY DELETED",
                extra={"remove_volumes": True},
            )
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
            logger.info("Successfully stopped all services")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop services: {e}", extra={"returncode": e.returncode})
            raise DockerError(f"Failed to stop services: {e}") from e


class DockerHealthChecker:
    """Poll a container's health status until ready or timeout."""

    def __init__(self, cli: _DockerCli) -> None:
        self._cli = cli

    def wait_for_container_healthy(
        self, container_name: str, timeout: int = HEALTH_CHECK_TIMEOUT
    ) -> None:
        logger.info(f"Waiting for container '{container_name}' to become healthy...")
        start_time = time.time()

        while True:
            cmd = [
                *self._cli.cmd,
                "inspect",
                "--format={{.State.Health.Status}}",
                container_name,
            ]
            result = subprocess.run(  # nosec B603
                cmd, capture_output=True, text=True, check=False
            )
            status = result.stdout.strip()
            if status == "healthy":
                elapsed = time.time() - start_time
                logger.info(
                    f"Container '{container_name}' is healthy!",
                    extra={"container": container_name, "elapsed_seconds": elapsed},
                )
                return
            if status == "unhealthy":
                logger.error(f"Container '{container_name}' became unhealthy")
                raise DockerError(f"Container '{container_name}' became unhealthy!")

            if time.time() - start_time > timeout:
                logger.error(
                    f"Timeout waiting for container '{container_name}'",
                    extra={"container": container_name, "timeout": timeout},
                )
                raise DockerError(
                    f"Timeout waiting for container '{container_name}' to become healthy."
                )

            time.sleep(HEALTH_CHECK_INTERVAL)


class DockerCredentialManager:
    """Fetch and rotate DOMjudge credentials via ``docker exec``."""

    _JUDGEDAEMON_RE = re.compile(r"^\S+\s+\S+\s+\S+\s+(\S+)$", re.MULTILINE)
    _ADMIN_INIT_RE = re.compile(r"^\S+$", re.MULTILINE)

    def __init__(self, cli: _DockerCli) -> None:
        self._cli = cli

    def fetch_judgedaemon_password(self) -> str:
        logger.info("Fetching judgedaemon password from domserver")
        output = self._exec_in_domserver(
            "/opt/domjudge/domserver/etc/restapi.secret",
            error_msg="Failed to fetch judgedaemon password",
        )
        match = self._JUDGEDAEMON_RE.search(output)
        if not match:
            logger.error("Failed to parse judgedaemon password from output")
            raise DockerError("Failed to parse judgedaemon password from output")
        logger.debug("Successfully fetched judgedaemon password")
        return match.group(1)

    def fetch_admin_init_password(self) -> str:
        logger.info("Fetching initial admin password from domserver")
        output = self._exec_in_domserver(
            "/opt/domjudge/domserver/etc/initial_admin_password.secret",
            error_msg="Failed to fetch admin initial password",
        )
        match = self._ADMIN_INIT_RE.search(output)
        if not match:
            logger.error("Failed to parse admin initial password from output")
            raise DockerError("Failed to parse admin initial password from output")
        logger.debug("Successfully fetched initial admin password")
        return match.group(0)

    def update_admin_password(self, new_password: str, db_user: str, db_password: str) -> None:
        hashed = generate_bcrypt_password(new_password)
        if not hashed.startswith("$2") or len(hashed) != 60:
            logger.error("Invalid bcrypt hash format detected")
            raise DockerError("Generated bcrypt hash has unexpected format")

        logger.info("Updating admin password in database")
        self._update_admin_password_via_docker(hashed, db_user, db_password)

    def _exec_in_domserver(self, path: str, *, error_msg: str) -> str:
        cmd = [
            *self._cli.cmd,
            "exec",
            ContainerNames.DOMSERVER.with_prefix(self._cli.prefix),
            "cat",
            path,
        ]
        try:
            result = subprocess.run(  # nosec B603
                cmd, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"{error_msg}: {e}")
            raise DockerError(f"{error_msg}: {e}") from e

    def _update_admin_password_via_docker(
        self, hashed_password: str, db_user: str, db_password: str
    ) -> None:
        try:
            # Escape the bcrypt hash for a MySQL string literal:
            # backslashes first (so the next replace doesn't re-escape them), then quotes.
            escaped_password = hashed_password.replace("\\", "\\\\").replace("'", "\\'")
            sql_query = (
                f"UPDATE domjudge.user SET password = '{escaped_password}' "  # nosec B608
                "WHERE username = 'admin';"
            )
            cmd = [
                *self._cli.cmd,
                "exec",
                "-e",
                f"MYSQL_PWD={db_password}",
                ContainerNames.MYSQL_CLIENT.with_prefix(self._cli.prefix),
                "mysql",
                "-h",
                ContainerNames.MARIADB.with_prefix(self._cli.prefix),
                "-u",
                db_user,
                "domjudge",
                "--execute",
                sql_query,
            ]
            subprocess.run(cmd, capture_output=True, check=True, text=True)  # nosec B603
            logger.info("Admin password successfully updated via docker exec")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to update admin password via docker: {e}",
                extra={
                    "stderr": e.stderr if e.stderr else None,
                    "stdout": e.stdout if e.stdout else None,
                    "returncode": e.returncode,
                },
            )
            raise DockerError(f"Failed to update admin password: {e}") from e


class DockerClient:
    """Facade exposing the legacy flat Docker API, composed of focused subclients.

    New code should prefer depending on a specific subclient (compose,
    health, credentials) for clearer mocking and SRP. The facade is
    retained so existing callers continue to work; it can be removed
    once all call sites migrate.
    """

    def __init__(self) -> None:
        self._cli = _DockerCli()
        self.compose = DockerComposeManager(self._cli)
        self.health = DockerHealthChecker(self._cli)
        self.credentials = DockerCredentialManager(self._cli)

    @property
    def _cmd(self) -> list[str]:
        return self._cli.cmd

    # ------------------------------------------------------------------ compose
    def start_services(self, services: list[str], compose_file: Path) -> None:
        self.compose.start_services(services, compose_file)

    def stop_all_services(self, compose_file: Path, remove_volumes: bool = False) -> None:
        self.compose.stop_all(compose_file, remove_volumes=remove_volumes)

    # ------------------------------------------------------------------ health
    def wait_for_container_healthy(
        self, container_name: str, timeout: int = HEALTH_CHECK_TIMEOUT
    ) -> None:
        self.health.wait_for_container_healthy(container_name, timeout)

    # ------------------------------------------------------------------ credentials
    def fetch_judgedaemon_password(self) -> str:
        return self.credentials.fetch_judgedaemon_password()

    def fetch_admin_init_password(self) -> str:
        return self.credentials.fetch_admin_init_password()

    def update_admin_password(self, new_password: str, db_user: str, db_password: str) -> None:
        self.credentials.update_admin_password(new_password, db_user, db_password)

    def _update_admin_password_via_docker(
        self, hashed_password: str, db_user: str, db_password: str
    ) -> None:
        # Retained for tests that exercise the SQL-escaping logic directly.
        self.credentials._update_admin_password_via_docker(hashed_password, db_user, db_password)
