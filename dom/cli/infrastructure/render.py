"""CLI-side renderers for infrastructure output."""

import json

from rich import box
from rich.table import Table

from dom import ui
from dom.core.services.infra.state import InfraChangeSet
from dom.types.infra import InfrastructureStatus, ServiceStatus


def render_planned_changes(change_set: InfraChangeSet | None) -> None:
    if not change_set:
        ui.blank()
        ui.hint("No infrastructure state found.")
        ui.blank()
        return

    ui.blank()
    ui.write("Planned Infrastructure Changes:", style="bold")
    ui.blank()
    ui.info(f"  {change_set.summary()}")
    ui.blank()

    if change_set.requires_restart:
        ui.write("  [yellow]⚠ WARNING:[/yellow] This change requires full infrastructure restart")
        ui.warn("  ⚠ This will cause downtime for running contests!")
        ui.blank()

    if change_set.old_config:
        ui.write("  [bold]Current state:[/bold]")
        ui.info(f"    Port:       {change_set.old_config.port}")
        ui.info(f"    Judgehosts: {change_set.old_config.judges}")
        ui.blank()

    ui.write("  [bold]Desired state:[/bold]")
    ui.info(f"    Port:       {change_set.new_config.port}")
    ui.info(f"    Judgehosts: {change_set.new_config.judges}")
    ui.blank()

    if change_set.is_safe_live_change:
        ui.success("  ✓ This change is safe to apply to running infrastructure")
        ui.blank()
    elif change_set.requires_restart:
        ui.error("  Recommendation:")
        ui.info("    1. Notify participants of downtime")
        ui.info("    2. Pause or finish active contests")
        ui.info("    3. Run: dom infra destroy --confirm")
        ui.info("    4. Run: dom infra apply")
        ui.info("    5. Reconfigure contests if needed")
        ui.blank()


def render_status(status: InfrastructureStatus, *, json_output: bool = False) -> None:
    """Render infrastructure status to the user."""
    if json_output:
        print(json.dumps(status.to_dict(), indent=2))
        return

    if status.is_healthy():
        ui.success("[OK] Infrastructure Status: HEALTHY", style="bold green")
    else:
        ui.error("[!!] Infrastructure Status: UNHEALTHY", style="bold red")
    ui.blank()

    if status.docker_available:
        ui.success("+ Docker daemon: Running")
    else:
        ui.error("x Docker daemon: Not available")
        if status.docker_error:
            ui.info(f"  Error: {status.docker_error}")
        return

    ui.blank()
    ui.write("Services:", style="bold")
    ui.blank()

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

    ui.render(table)
    ui.blank()
    healthy_count = sum(1 for s in status.services.values() if s == ServiceStatus.HEALTHY)
    total_count = len(status.services)
    ui.hint(f"{healthy_count}/{total_count} services healthy")

    if status.is_healthy():
        ui.blank()
        ui.success("[OK] Ready to accept commands")
    else:
        ui.blank()
        ui.warn(
            "[**] Some services are not healthy. " "Infrastructure may not be fully operational."
        )
