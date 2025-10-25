"""Infrastructure status checking service.

This module provides health check functionality for DOMjudge infrastructure.
"""

import json
import subprocess  # nosec B404
from pathlib import Path

import yaml
from rich import box
from rich.console import Console
from rich.table import Table

from dom.exceptions import DockerError
from dom.infrastructure.docker import DockerClient
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig, InfrastructureStatus, ServiceStatus
from dom.utils.cli import ensure_dom_directory

logger = get_logger(__name__)


def _get_expected_services_from_compose() -> dict[str, str]:
    """
    Parse the generated docker-compose.yml to extract expected services and container names.

    This avoids hardcoding services and ensures the status check matches
    the actual docker-compose configuration.

    Returns:
        Dictionary mapping service names to container names

    Raises:
        FileNotFoundError: If docker-compose.yml doesn't exist
    """
    compose_file = ensure_dom_directory() / "docker-compose.yml"

    if not compose_file.exists():
        logger.warning(f"Docker compose file not found at {compose_file}")
        return {}

    try:
        with Path(compose_file).open() as f:
            compose_data = yaml.safe_load(f)

        # Extract service names and container names from the compose file
        services = {}
        for service_name, service_config in compose_data.get("services", {}).items():
            container_name = service_config.get("container_name", service_name)
            services[service_name] = container_name

        logger.debug(
            f"Found {len(services)} services in docker-compose.yml: {list(services.keys())}"
        )
        return services

    except Exception as e:
        logger.error(f"Failed to parse docker-compose.yml: {e}", exc_info=True)
        return {}


def check_infrastructure_status(config: InfraConfig | None = None) -> InfrastructureStatus:  # noqa: ARG001
    """
    Check the status of DOMjudge infrastructure.

    This performs health checks on:
    - Docker daemon availability
    - DOMserver container status
    - MariaDB container status
    - Judgehost containers status
    - MySQL client container status

    The expected services are determined by parsing the generated docker-compose.yml
    file to avoid split-brain issues between configuration and status checks.

    Args:
        config: Infrastructure configuration (optional, kept for backwards compatibility)

    Returns:
        InfrastructureStatus object with detailed status information

    Example:
        >>> status = check_infrastructure_status()
        >>> if status.is_healthy():
        ...     print("All systems operational")
    """
    status = InfrastructureStatus()

    # Check Docker availability
    try:
        docker = DockerClient()
        status.docker_available = True
        logger.debug("Docker daemon is available")
    except DockerError as e:
        status.docker_available = False
        status.docker_error = str(e)
        logger.error(f"Docker is not available: {e}")
        return status

    # Get expected services from docker-compose.yml
    expected_services = _get_expected_services_from_compose()

    if not expected_services:
        logger.warning("No services found in docker-compose.yml or file doesn't exist")
        # Return early if no compose file exists
        return status

    # Check each service
    for service_name, container_name in expected_services.items():
        service_status, details = _check_container_status(docker, container_name)
        status.services[service_name] = service_status
        status.service_details[service_name] = details

    logger.info(
        "Infrastructure status check complete",
        extra={
            "healthy": status.is_healthy(),
            "services_count": len(status.services),
            "healthy_services": sum(
                1 for s in status.services.values() if s == ServiceStatus.HEALTHY
            ),
        },
    )

    return status


def _check_container_status(
    docker: DockerClient, container_name: str
) -> tuple[ServiceStatus, dict]:
    """
    Check the status of a specific container.

    Args:
        docker: Docker client instance
        container_name: Name of container to check

    Returns:
        Tuple of (ServiceStatus, details_dict)
    """
    try:
        # First check if container exists and get its state
        cmd = [
            *docker._cmd,
            "inspect",
            "--format={{.State.Status}}",
            container_name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603

        if result.returncode != 0:
            # Container doesn't exist
            return ServiceStatus.MISSING, {
                "container": container_name,
                "error": "Container not found",
            }

        container_status = result.stdout.strip()

        # Determine service status
        if container_status != "running":
            return ServiceStatus.STOPPED, {"container": container_name, "state": container_status}

        # Check if container has health check configured
        health_cmd = [
            *docker._cmd,
            "inspect",
            "--format={{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}",
            container_name,
        ]
        health_result = subprocess.run(health_cmd, capture_output=True, text=True, check=False)  # nosec B603

        health_status = (
            health_result.stdout.strip() if health_result.returncode == 0 else "no_healthcheck"
        )

        if health_status == "healthy":
            return ServiceStatus.HEALTHY, {
                "container": container_name,
                "state": container_status,
                "health": health_status,
            }
        elif health_status == "starting":
            return ServiceStatus.STARTING, {
                "container": container_name,
                "state": container_status,
                "health": health_status,
            }
        elif health_status == "unhealthy":
            return ServiceStatus.UNHEALTHY, {
                "container": container_name,
                "state": container_status,
                "health": health_status,
            }
        else:
            # No health check defined, assume healthy if running
            return ServiceStatus.HEALTHY, {
                "container": container_name,
                "state": container_status,
                "health": "no_healthcheck",
            }

    except Exception as e:
        logger.error(
            f"Failed to check container status: {e}",
            exc_info=True,
            extra={"container": container_name},
        )
        return ServiceStatus.MISSING, {"container": container_name, "error": str(e)}


def print_status_human_readable(status: InfrastructureStatus) -> None:
    """
    Print status in human-readable format.

    Args:
        status: Infrastructure status to print
    """
    console = Console()

    # Overall status
    if status.is_healthy():
        console.print("✅ [bold green]Infrastructure Status: HEALTHY[/bold green]\n")
    else:
        console.print("❌ [bold red]Infrastructure Status: UNHEALTHY[/bold red]\n")

    # Docker status
    if status.docker_available:
        console.print("✓ [green]Docker daemon: Running[/green]")
    else:
        console.print("✗ [red]Docker daemon: Not available[/red]")
        if status.docker_error:
            console.print(f"  Error: {status.docker_error}")
        return

    # Services table
    console.print("\n[bold]Services:[/bold]\n")

    table = Table(box=box.ROUNDED)
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Details", style="dim")

    # Status icons and colors
    status_format = {
        ServiceStatus.HEALTHY: ("✓", "green"),
        ServiceStatus.UNHEALTHY: ("✗", "red"),
        ServiceStatus.STARTING: ("⟳", "yellow"),
        ServiceStatus.STOPPED: ("■", "red"),
        ServiceStatus.MISSING: ("?", "dim"),
    }

    for service_name, service_status in sorted(status.services.items()):
        icon, color = status_format.get(service_status, ("?", "white"))
        details = status.service_details.get(service_name, {})

        status_text = f"{icon} [{color}]{service_status.value}[/{color}]"

        # Format details
        detail_parts = []
        if "state" in details:
            detail_parts.append(f"state: {details['state']}")
        if "health" in details and details["health"] != "no_healthcheck":
            detail_parts.append(f"health: {details['health']}")
        if "error" in details:
            detail_parts.append(f"error: {details['error']}")

        detail_text = ", ".join(detail_parts) if detail_parts else "-"

        table.add_row(service_name, status_text, detail_text)

    console.print(table)

    # Summary
    console.print()
    healthy_count = sum(1 for s in status.services.values() if s == ServiceStatus.HEALTHY)
    total_count = len(status.services)
    console.print(f"[dim]{healthy_count}/{total_count} services healthy[/dim]")

    if status.is_healthy():
        console.print("\n✅ [green]Ready to accept commands[/green]")
    else:
        console.print(
            "\n⚠️  [yellow]Some services are not healthy. Infrastructure may not be fully operational.[/yellow]"
        )


def print_status_json(status: InfrastructureStatus) -> None:
    """
    Print status in JSON format.

    Args:
        status: Infrastructure status to print
    """
    print(json.dumps(status.to_dict(), indent=2))
