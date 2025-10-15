"""Docker container management for DOMjudge infrastructure.

This module provides a DockerClient class to manage Docker containers for DOMjudge,
including starting services, checking health, and managing passwords.
"""

import re
import subprocess  # nosec B404
import tempfile
import time
from pathlib import Path

from dom.constants import CONTAINER_PREFIX, HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT
from dom.exceptions import DockerError
from dom.logging_config import get_logger
from dom.utils.hash import generate_bcrypt_password

logger = get_logger(__name__)


class DockerClient:
    """
    Docker client for managing containers and services.

    Encapsulates Docker command execution with proper error handling and logging.
    """

    def __init__(self):
        """
        Initialize Docker client.

        Raises:
            DockerError: If Docker is not accessible
        """
        self._cmd = self._initialize_docker_cmd()
        logger.info("Docker client initialized successfully")

    def _initialize_docker_cmd(self) -> list[str]:
        """
        Initialize and validate Docker command.

        Returns:
            List containing the docker command

        Raises:
            DockerError: If docker is not accessible
        """
        try:
            subprocess.run(  # nosec B603 B607
                ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
            logger.debug("Docker is accessible")
            return ["docker"]
        except subprocess.CalledProcessError:
            logger.error("Docker is not accessible or requires elevated permissions")
            raise DockerError(
                "You don't have permission to run 'docker'. "
                "Please run this command with 'sudo' (e.g., 'sudo dom infra apply') "
                "or fix your docker permissions."
            ) from None

    def start_services(self, services: list[str], compose_file: Path) -> None:
        """
        Start Docker services using docker compose.

        Args:
            services: List of service names to start
            compose_file: Path to docker-compose.yml file

        Raises:
            DockerError: If services fail to start
        """
        logger.info(f"Starting services: {', '.join(services)}")
        cmd = [
            *self._cmd,
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

    def stop_all_services(self, compose_file: Path) -> None:
        """
        Stop all Docker services.

        Args:
            compose_file: Path to docker-compose.yml file

        Raises:
            DockerError: If services fail to stop
        """
        logger.info("Stopping all services")
        cmd = [*self._cmd, "compose", "-f", str(compose_file), "down", "-v"]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603
            logger.info("Successfully stopped all services")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop services: {e}", extra={"returncode": e.returncode})
            raise DockerError(f"Failed to stop services: {e}") from e

    def wait_for_container_healthy(
        self, container_name: str, timeout: int = HEALTH_CHECK_TIMEOUT
    ) -> None:
        """
        Wait for a container to become healthy.

        Args:
            container_name: Name of the container to wait for
            timeout: Maximum time to wait in seconds

        Raises:
            DockerError: If container becomes unhealthy or times out
        """
        logger.info(f"Waiting for container '{container_name}' to become healthy...")
        start_time = time.time()

        while True:
            cmd = [*self._cmd, "inspect", "--format={{.State.Health.Status}}", container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603

            status = result.stdout.strip()
            if status == "healthy":
                elapsed = time.time() - start_time
                logger.info(
                    f"Container '{container_name}' is healthy!",
                    extra={"container": container_name, "elapsed_seconds": elapsed},
                )
                return
            elif status == "unhealthy":
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

    def fetch_judgedaemon_password(self) -> str:
        """
        Fetch the judgedaemon password from the domserver container.

        Returns:
            The judgedaemon password

        Raises:
            DockerError: If password cannot be fetched or parsed
        """
        logger.info("Fetching judgedaemon password from domserver")
        cmd = [
            *self._cmd,
            "exec",
            f"{CONTAINER_PREFIX}-domserver",
            "cat",
            "/opt/domjudge/domserver/etc/restapi.secret",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # nosec B603

            pattern = re.compile(r"^\S+\s+\S+\s+\S+\s+(\S+)$", re.MULTILINE)
            match = pattern.search(result.stdout.strip())
            if not match:
                logger.error("Failed to parse judgedaemon password from output")
                raise DockerError("Failed to parse judgedaemon password from output")

            logger.debug("Successfully fetched judgedaemon password")
            return match.group(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch judgedaemon password: {e}")
            raise DockerError(f"Failed to fetch judgedaemon password: {e}") from e

    def fetch_admin_init_password(self) -> str:
        """
        Fetch the initial admin password from the domserver container.

        Returns:
            The initial admin password

        Raises:
            DockerError: If password cannot be fetched or parsed
        """
        logger.info("Fetching initial admin password from domserver")
        cmd = [
            *self._cmd,
            "exec",
            f"{CONTAINER_PREFIX}-domserver",
            "cat",
            "/opt/domjudge/domserver/etc/initial_admin_password.secret",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # nosec B603

            pattern = re.compile(r"^\S+$", re.MULTILINE)
            match = pattern.search(result.stdout.strip())
            if not match:
                logger.error("Failed to parse admin initial password from output")
                raise DockerError("Failed to parse admin initial password from output")

            logger.debug("Successfully fetched initial admin password")
            return match.group(0)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch admin initial password: {e}")
            raise DockerError(f"Failed to fetch admin initial password: {e}") from e

    def update_admin_password(self, new_password: str, db_user: str, db_password: str) -> None:
        """
        Update admin password in the database.

        SECURITY NOTES:
        1. Password is bcrypt hashed (60 chars, base64 alphabet: [A-Za-z0-9./+])
        2. Bcrypt output is safe for SQL, but we escape single quotes as defense-in-depth
        3. This uses Docker exec + SQL file, not a proper DB client library
        4. Hash format is validated before use to detect tampering

        LIMITATION: This approach writes SQL to a temp file due to Docker exec limitations.
        For production-critical deployments, consider:
        - Using a proper MySQL client library (pymysql) with parameterized queries
        - Direct database connection with proper connection pooling
        - Vault or similar secret management for database credentials

        Args:
            new_password: New admin password (will be bcrypt hashed)
            db_user: Database user
            db_password: Database password

        Raises:
            DockerError: If password update fails or hash validation fails
        """
        hashed_password = generate_bcrypt_password(new_password)

        # Defense-in-depth: escape single quotes even though bcrypt hashes shouldn't contain them
        # Bcrypt hashes are base64-encoded, but we escape as a safety measure
        escaped_hash = hashed_password.replace("'", "''")

        # Validate the hash format to ensure it's a valid bcrypt hash
        if not escaped_hash.startswith("$2") or len(escaped_hash) != len(hashed_password):
            logger.error("Invalid bcrypt hash format detected")
            raise DockerError("Generated bcrypt hash has unexpected format")

        # Create a temporary SQL file with the properly escaped hash
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("USE domjudge;\n")
            # Safe: bcrypt hash is base64-encoded and validated, single quotes escaped
            sql_update = f"UPDATE user SET password = '{escaped_hash}' WHERE username = 'admin';\n"  # nosec B608
            f.write(sql_update)
            temp_sql_file = f.name

        try:
            # Copy SQL file to container
            copy_cmd = [
                *self._cmd,
                "cp",
                temp_sql_file,
                f"{CONTAINER_PREFIX}-mysql-client:/tmp/update_password.sql",  # nosec B108
            ]
            subprocess.run(copy_cmd, check=True, capture_output=True)  # nosec B603

            # Execute SQL file in container
            cmd = [
                *self._cmd,
                "exec",
                "-e",
                f"MYSQL_PWD={db_password}",
                f"{CONTAINER_PREFIX}-mysql-client",
                "mysql",
                "-h",
                f"{CONTAINER_PREFIX}-mariadb",
                "-u",
                db_user,
                "-e",
                "source /tmp/update_password.sql",
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603

            # Cleanup SQL file from container
            cleanup_cmd = [
                *self._cmd,
                "exec",
                f"{CONTAINER_PREFIX}-mysql-client",
                "rm",
                "/tmp/update_password.sql",  # nosec B108
            ]
            subprocess.run(cleanup_cmd, check=True, capture_output=True)  # nosec B603

            logger.info("Admin password successfully updated in database")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to update admin password: {e}",
                extra={
                    "stderr": e.stderr if hasattr(e, "stderr") else None,
                    "returncode": e.returncode,
                },
            )
            raise DockerError(f"Failed to update admin password: {e}") from e
        finally:
            # Cleanup local temp file
            temp_sql_path = Path(temp_sql_file)
            if temp_sql_path.exists():
                temp_sql_path.unlink()
                logger.debug(f"Cleaned up temporary SQL file: {temp_sql_path}")
