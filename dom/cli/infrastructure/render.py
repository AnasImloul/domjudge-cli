"""CLI-side renderers for infrastructure output."""

import json

from rich import box
from rich.table import Table

from dom.core.services.infra.state import InfraChangeSet
from dom.logging_config import console
from dom.types.infra import InfrastructureStatus, ServiceStatus


def render_planned_changes(change_set: InfraChangeSet | None) -> None:
    if not change_set:
        console.print("\n[dim]No infrastructure state found.[/dim]\n")
        return

    console.print("\n[bold]Planned Infrastructure Changes:[/bold]\n")
    console.print(f"  {change_set.summary()}\n")

    if change_set.requires_restart:
        console.print(
            "  [yellow]⚠ WARNING:[/yellow] This change requires full infrastructure restart"
        )
        console.print("  [yellow]⚠ This will cause downtime for running contests![/yellow]\n")

    if change_set.old_config:
        console.print("  [bold]Current state:[/bold]")
        console.print(f"    Port:       {change_set.old_config.port}")
        console.print(f"    Judgehosts: {change_set.old_config.judges}")
        console.print()

    console.print("  [bold]Desired state:[/bold]")
    console.print(f"    Port:       {change_set.new_config.port}")
    console.print(f"    Judgehosts: {change_set.new_config.judges}")
    console.print()

    if change_set.is_safe_live_change:
        console.print("  [green]✓ This change is safe to apply to running infrastructure[/green]\n")
    elif change_set.requires_restart:
        console.print("  [red]Recommendation:[/red]")
        console.print("    1. Notify participants of downtime")
        console.print("    2. Pause or finish active contests")
        console.print("    3. Run: dom infra destroy --confirm")
        console.print("    4. Run: dom infra apply")
        console.print("    5. Reconfigure contests if needed\n")


def render_status(status: InfrastructureStatus, *, json_output: bool = False) -> None:
    """Render infrastructure status to the user."""
    if json_output:
        print(json.dumps(status.to_dict(), indent=2))
        return

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
            "\n[**] [yellow]Some services are not healthy. "
            "Infrastructure may not be fully operational.[/yellow]"
        )
