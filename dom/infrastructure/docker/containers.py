"""Docker container management for DOMjudge infrastructure.

This module provides a DockerClient class to manage Docker containers for DOMjudge,
including starting services, checking health, and managing passwords.
"""

import re
import subprocess  # nosec B404
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dom.constants import HEALTH_CHECK_INTERVAL, HEALTH_CHECK_TIMEOUT, ContainerNames
from dom.exceptions import DockerError
from dom.logging_config import get_logger
from dom.security.password_hasher import hash_password as generate_bcrypt_password
from dom.shared.filesystem import get_container_prefix

logger = get_logger(__name__)


class DockerClient:
    """
    Docker client for managing containers and services.

    Encapsulates Docker command execution with proper error handling and logging.
    """

    def __init__(self) -> None:
        """
        Initialize Docker client.

        Raises:
            DockerError: If Docker is not accessible
        """
        self._cmd = self._initialize_docker_cmd()
        self._container_prefix = get_container_prefix()
        logger.info(
            f"Docker client initialized successfully with prefix '{self._container_prefix}'"
        )

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
                "You don't have permission to run 'docker'.\n"
                "Solutions:\n"
                "  1. Run with sudo: 'sudo dom infra apply'\n"
                "  2. Add your user to docker group: 'sudo usermod -aG docker $USER'\n"
                "     Then log out and back in for changes to take effect.\n"
                "  3. Check if Docker daemon is running: 'sudo systemctl status docker'"
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

    def stop_all_services(self, compose_file: Path, remove_volumes: bool = False) -> None:
        """
        Stop all Docker services.

        Args:
            compose_file: Path to docker-compose.yml file
            remove_volumes: Whether to remove volumes (WARNING: deletes all data)

        Raises:
            DockerError: If services fail to stop
        """
        logger.info("Stopping all services")
        cmd = [*self._cmd, "compose", "-f", str(compose_file), "down"]

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

    def wait_for_container_healthy(
        self, container_name: str, timeout: int = HEALTH_CHECK_TIMEOUT
    ) -> None:
        """
        Wait for a container to become healthy.

        Args:
            container_name: Name of the container to wait for (with prefix)
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

    def wait_for_containers_healthy(
        self, container_names: list[str], timeout: int = HEALTH_CHECK_TIMEOUT
    ) -> None:
        """
        Wait for multiple containers to become healthy concurrently.

        This is much faster than sequential health checks, especially with many judgehosts.
        Uses thread pool to check health of all containers in parallel.

        Args:
            container_names: List of container names to wait for (with prefix)
            timeout: Maximum time to wait in seconds per container

        Raises:
            DockerError: If any container becomes unhealthy or times out
        """
        logger.info(f"Waiting for {len(container_names)} containers to become healthy...")

        failures: list[tuple[str, Exception]] = []
        successful = []

        with ThreadPoolExecutor(max_workers=min(len(container_names), 10)) as executor:
            # Submit all health checks concurrently
            future_to_container = {
                executor.submit(self.wait_for_container_healthy, name, timeout): name
                for name in container_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_container):
                container_name = future_to_container[future]
                try:
                    future.result()
                    successful.append(container_name)
                    logger.debug(f"Health check passed: {container_name}")
                except Exception as e:
                    logger.error(f"Health check failed for {container_name}: {e}")
                    failures.append((container_name, e))

        # Report results
        if failures:
            failure_details = ", ".join([f"{name}: {e}" for name, e in failures])
            raise DockerError(
                f"Health check failed for {len(failures)} container(s): {failure_details}"
            )

        logger.info(f"All {len(successful)} containers are healthy!")

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
            ContainerNames.DOMSERVER.with_prefix(self._container_prefix),
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
            ContainerNames.DOMSERVER.with_prefix(self._container_prefix),
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
        Update admin password in the database using docker exec.

        This method uses docker exec to connect to the database from within the mysql-client
        container, which is more reliable than direct host connections.

        Args:
            new_password: New admin password (will be bcrypt hashed)
            db_user: Database user
            db_password: Database password

        Raises:
            DockerError: If password update fails or database connection fails
        """
        hashed_password = generate_bcrypt_password(new_password)

        # Validate the hash format to ensure it's a valid bcrypt hash
        if not hashed_password.startswith("$2") or len(hashed_password) != 60:
            logger.error("Invalid bcrypt hash format detected")
            raise DockerError("Generated bcrypt hash has unexpected format")

        logger.info("Updating admin password in database")

        # Use docker exec method directly since it's more reliable
        # The mysql-client container is already running and connected to the same network
        self._update_admin_password_via_docker(hashed_password, db_user, db_password)

    def _update_admin_password_via_docker(
        self, hashed_password: str, db_user: str, db_password: str
    ) -> None:
        """
        Update admin password via docker exec as fallback.

        Uses parameterized query via mysql CLI with proper escaping for bcrypt hashes.
        Bcrypt hashes contain $ characters that need special handling.

        Args:
            hashed_password: Bcrypt hashed password (contains $ characters)
            db_user: Database user
            db_password: Database password

        Raises:
            DockerError: If password update fails
        """
        try:
            # Escape the bcrypt hash properly:
            # 1. Replace single quotes with doubled single quotes for SQL
            # 2. Escape backslashes for MySQL string literals
            escaped_password = hashed_password.replace("\\", "\\\\").replace("'", "\\'")

            # Build SQL query with escaped password
            sql_query = f"UPDATE domjudge.user SET password = '{escaped_password}' WHERE username = 'admin';"  # nosec B608

            cmd = [
                *self._cmd,
                "exec",
                "-e",
                f"MYSQL_PWD={db_password}",
                ContainerNames.MYSQL_CLIENT.with_prefix(self._container_prefix),
                "mysql",
                "-h",
                ContainerNames.MARIADB.with_prefix(self._container_prefix),
                "-u",
                db_user,
                "domjudge",
                "--execute",
                sql_query,
            ]

            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                text=True,
            )  # nosec B603

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
