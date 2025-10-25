"""Startup validation to fail fast with clear error messages.

This module provides validation checks that run before operations begin,
ensuring prerequisites are met and giving users actionable feedback.
"""

import socket
import subprocess  # nosec B404
from pathlib import Path

from dom.exceptions import ConfigError, DockerError, InfrastructureError
from dom.logging_config import console, get_logger
from dom.utils.cli import get_container_prefix

logger = get_logger(__name__)


def validate_docker_available() -> None:
    """
    Validate that Docker is available and accessible.

    Raises:
        DockerError: If Docker is not available or not accessible
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )

        if result.returncode != 0:
            error_output = result.stderr.decode() if result.stderr else ""

            # Check for common permission issues
            if "permission denied" in error_output.lower():
                raise DockerError(
                    "Docker permission denied. Solutions:\n"
                    "  1. Run with sudo: 'sudo dom infra apply'\n"
                    "  2. Add your user to docker group: 'sudo usermod -aG docker $USER'\n"
                    "     (Then log out and back in)\n"
                    "  3. Check if Docker daemon is running: 'sudo systemctl status docker'"
                )

            # Check if Docker is not running
            elif "cannot connect" in error_output.lower():
                raise DockerError(
                    "Cannot connect to Docker daemon. Solutions:\n"
                    "  1. Start Docker: 'sudo systemctl start docker'\n"
                    "  2. Check Docker status: 'sudo systemctl status docker'\n"
                    "  3. Install Docker: https://docs.docker.com/engine/install/"
                )

            else:
                raise DockerError(
                    f"Docker is not functioning correctly:\n{error_output}\n\n"
                    "Please ensure Docker is installed and running."
                )

        logger.debug("Docker validation passed")

    except FileNotFoundError:
        raise DockerError(
            "Docker is not installed. Please install Docker:\n"
            "  https://docs.docker.com/engine/install/"
        ) from None
    except subprocess.TimeoutExpired:
        raise DockerError("Docker command timed out. Docker daemon may be unresponsive.") from None


def is_port_used_by_domjudge(port: int) -> bool:
    """
    Check if a port is being used by our own DOMjudge infrastructure.

    Args:
        port: Port number to check

    Returns:
        True if port is used by DOMjudge containers, False otherwise
    """
    try:
        container_prefix = get_container_prefix()
        domserver_container = f"{container_prefix}-domserver"

        # Check if domserver container exists and is using this port
        result = subprocess.run(  # nosec B603, B607
            ["docker", "ps", "--filter", f"name={domserver_container}", "--format", "{{.Ports}}"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout:
            # Check if our port is in the container's port mappings
            ports_output = result.stdout.strip()
            if f"{port}:" in ports_output or f":{port}->" in ports_output:
                logger.debug(
                    f"Port {port} is being used by DOMjudge container '{domserver_container}' (idempotent)"
                )
                return True

        return False
    except Exception as e:
        logger.debug(f"Could not check if port is used by DOMjudge: {e}")
        return False


def validate_port_available(port: int, allow_domjudge: bool = True) -> None:
    """
    Validate that a port is available for binding.

    For idempotent deployments, this function allows ports that are already
    in use by our own DOMjudge infrastructure.

    Args:
        port: Port number to check
        allow_domjudge: If True, allow port if it's used by DOMjudge (for idempotency)

    Raises:
        InfrastructureError: If port is already in use by another process
    """
    try:
        # Try to bind to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", port))
            logger.debug(f"Port {port} is available")
    except OSError as e:
        if e.errno in {48, 98}:  # Address already in use
            # Check if it's our own infrastructure (idempotent operation)
            if allow_domjudge and is_port_used_by_domjudge(port):
                logger.info(
                    f"Port {port} is already in use by DOMjudge infrastructure (idempotent operation)"
                )
                return

            raise InfrastructureError(
                f"Port {port} is already in use. Solutions:\n"
                f"  1. Stop the process using this port\n"
                f"  2. Choose a different port in your configuration\n"
                f"  3. Find what's using the port: 'lsof -i :{port}' or 'netstat -tulpn | grep {port}'\n"
                f"  4. If DOMjudge is already running, use 'dom infra destroy' first"
            ) from e
        else:
            raise InfrastructureError(f"Cannot bind to port {port}: {e}") from e


def validate_config_file(config_path: Path | None) -> Path:
    """
    Validate configuration file exists and is readable.

    Args:
        config_path: Path to configuration file (None = use default)

    Returns:
        Validated Path to configuration file

    Raises:
        ConfigError: If configuration file is invalid
    """
    if config_path is None:
        # Look for default config files
        yaml_path = Path("dom-judge.yaml")
        yml_path = Path("dom-judge.yml")

        if yaml_path.is_file() and yml_path.is_file():
            raise ConfigError(
                "Both 'dom-judge.yaml' and 'dom-judge.yml' exist. "
                "Please specify which one to use with --file."
            )

        if yaml_path.is_file():
            config_path = yaml_path
        elif yml_path.is_file():
            config_path = yml_path
        else:
            raise ConfigError(
                "No configuration file found. Please:\n"
                "  1. Create 'dom-judge.yaml' in the current directory, or\n"
                "  2. Run 'dom init' to generate a template, or\n"
                "  3. Specify a config file with --file"
            )

    # Validate file exists
    if not config_path.exists():
        raise ConfigError(
            f"Configuration file not found: {config_path}\nPlease check the path and try again."
        )

    # Validate it's a file (not directory)
    if not config_path.is_file():
        raise ConfigError(
            f"Configuration path is not a file: {config_path}\n"
            "Please provide a valid YAML configuration file."
        )

    # Validate file is readable
    try:
        with config_path.open("r") as f:
            f.read(1)  # Try to read at least one byte
    except PermissionError:
        raise ConfigError(
            f"Permission denied reading configuration file: {config_path}\n"
            "Please check file permissions."
        ) from None
    except Exception as e:
        raise ConfigError(f"Cannot read configuration file: {config_path}\nError: {e}") from e

    logger.debug(f"Configuration file validated: {config_path}")
    return config_path


def validate_infrastructure_prerequisites(port: int | None = None) -> None:
    """
    Validate all infrastructure prerequisites before deployment.

    Args:
        port: Optional port to check availability

    Raises:
        DockerError: If Docker is not available
        InfrastructureError: If prerequisites are not met
    """
    logger.info("Validating prerequisites...")

    # Check Docker
    try:
        validate_docker_available()
        logger.info("✓ Docker is available")
    except DockerError:
        logger.error("✗ Docker validation failed")
        raise

    # Check port if specified
    if port is not None:
        try:
            validate_port_available(port)
            logger.info(f"✓ Port {port} is available")
        except InfrastructureError:
            logger.error(f"✗ Port {port} is not available")
            raise

    logger.info("Prerequisites validated successfully")


def warn_if_privileged_port(port: int) -> None:
    """
    Warn user if using a privileged port (< 1024).

    Args:
        port: Port number to check
    """
    if port < 1024:
        console.print(f"[yellow]⚠️  Warning: Port {port} is privileged (< 1024)[/yellow]")
        console.print("[yellow]   You may need to run with sudo or use a port >= 1024[/yellow]\n")
        logger.warning(f"Using privileged port: {port}")
