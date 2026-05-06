"""Check and display infrastructure status."""

import json

from rich import box
from rich.console import Console
from rich.table import Table

from dom.core.operations.framework import Context, operation
from dom.core.services.infra.service import InfraService
from dom.types.infra import InfrastructureStatus, ServiceStatus


@operation("Display infrastructure status", show_progress=False)
def print_infra_status_op(ctx: Context, json_output: bool = False) -> InfrastructureStatus:
    status = InfraService(ctx.secrets).check_status()
    if json_output:
        _print_status_json(status)
    else:
        _print_status_human_readable(status)
    return status


# ---------------------------------------------------------------- presenters


def _print_status_human_readable(status: InfrastructureStatus) -> None:
    console = Console()

    if status.is_healthy():
        console.print("[OK] [bold green]Infrastructure Status: HEALTHY[/bold green]\n")
    else:
        console.print("[!!] [bold red]Infrastructure Status: UNHEALTHY[/bold red]\n")

    if status.docker_available:
        console.print("+ [green]Docker daemon: Running[/green]")
    else:
        console.print("x [red]Docker daemon: Not available[/red]")
        if status.docker_error:
            console.print(f"  Error: {status.docker_error}")
        return

    console.print("\n[bold]Services:[/bold]\n")

    table = Table(box=box.ROUNDED)
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Details", style="dim")

    status_format = {
        ServiceStatus.HEALTHY: ("+", "green"),
        ServiceStatus.UNHEALTHY: ("x", "red"),
        ServiceStatus.STARTING: ("~", "yellow"),
        ServiceStatus.STOPPED: ("#", "red"),
        ServiceStatus.MISSING: ("?", "dim"),
    }

    for service_name, service_status in sorted(status.services.items()):
        icon, color = status_format.get(service_status, ("?", "white"))
        details = status.service_details.get(service_name, {})
        status_text = f"{icon} [{color}]{service_status.value}[/{color}]"

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
    console.print()
    healthy_count = sum(1 for s in status.services.values() if s == ServiceStatus.HEALTHY)
    total_count = len(status.services)
    console.print(f"[dim]{healthy_count}/{total_count} services healthy[/dim]")

    if status.is_healthy():
        console.print("\n[OK] [green]Ready to accept commands[/green]")
    else:
        console.print(
            "\n[**] [yellow]Some services are not healthy. Infrastructure may not be fully operational.[/yellow]"
        )


def _print_status_json(status: InfrastructureStatus) -> None:
    print(json.dumps(status.to_dict(), indent=2))
