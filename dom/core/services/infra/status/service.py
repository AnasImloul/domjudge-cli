"""Infrastructure status checking service.

This module provides health check functionality for DOMjudge infrastructure.
"""

import json
import subprocess  # nosec B404

from rich import box
from rich.console import Console
from rich.table import Table

from dom.constants import CONTAINER_PREFIX
from dom.exceptions import DockerError
from dom.infrastructure.docker import DockerClient
from dom.logging_config import get_logger
from dom.types.infra import InfraConfig, InfrastructureStatus, ServiceStatus

logger = get_logger(__name__)


def check_infrastructure_status(config: InfraConfig | None = None) -> InfrastructureStatus:
    """
    Check the status of DOMjudge infrastructure.

    This performs health checks on:
    - Docker daemon availability
    - DOMserver container status
    - MariaDB container status
    - Judgehost containers status
    - MySQL client container status

    Args:
        config: Infrastructure configuration (optional, used to know expected services)

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

    # Define expected services
    expected_services = [
        "domserver",
        "mariadb",
        "mysql-client",
    ]

    # Add judgehosts if config provided
    if config:
        for i in range(config.judges):
            expected_services.append(f"judgehost-{i}")

    # Check each service
    for service_name in expected_services:
        container_name = f"{CONTAINER_PREFIX}-{service_name}"
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
        # Check if container exists and get its status
        cmd = [
            *docker._cmd,
            "inspect",
            "--format={{.State.Status}}|{{.State.Health.Status}}",
            container_name,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603

        if result.returncode != 0:
            # Container doesn't exist
            return ServiceStatus.MISSING, {
                "container": container_name,
                "error": "Container not found",
            }

        # Parse output
        parts = result.stdout.strip().split("|")
        container_status = parts[0] if parts else "unknown"
        health_status = parts[1] if len(parts) > 1 else "no_healthcheck"

        # Determine service status
        if container_status != "running":
            return ServiceStatus.STOPPED, {"container": container_name, "state": container_status}

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
