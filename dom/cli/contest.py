import json
from pathlib import Path

import jmespath
import typer
from rich import box
from rich.console import Console
from rich.table import Table

from dom.cli.validators import validate_contest_name, validate_file_path
from dom.core.config.loaders import (
    load_config,
    load_contest_config,
    load_contests_config,
    load_infrastructure_config,
)
from dom.core.services.contest.apply import apply_contests
from dom.core.services.contest.plan import ChangeAction, ContestPlanner
from dom.core.services.problem.verify import verify_problemset as verify_problemset_service
from dom.infrastructure.api.factory import APIClientFactory
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
from dom.types.config import DomConfig
from dom.utils.cli import cli_command, get_secrets_manager

logger = get_logger(__name__)
contest_command = typer.Typer()


@contest_command.command("apply")
@cli_command
def apply_from_config(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
) -> None:
    """
    Apply configuration to contests on the platform.

    Use --dry-run to preview what changes would be made without actually applying them.
    This is useful for validating configuration before making changes.
    """
    # Dependency injection: create secrets manager at entry point
    secrets = get_secrets_manager()
    config = load_config(file, secrets)

    if dry_run:
        _preview_contest_changes(config, secrets)
    else:
        apply_contests(config, secrets)


def _preview_contest_changes(config: DomConfig, secrets: SecretsManager) -> None:
    """
    Preview what changes would be made without applying them.

    Uses the ContestPlanner service to analyze changes, then renders them
    in a user-friendly format using Rich.

    Args:
        config: Complete DOMjudge configuration
        secrets: Secrets manager for retrieving credentials
    """
    console = Console()
    console.print("\n[bold cyan]🔍 DRY RUN - Preview Mode[/bold cyan]\n")
    console.print("[dim]No changes will be applied to the platform[/dim]\n")

    # Create planner service
    factory = APIClientFactory()
    try:
        client = factory.create_admin_client(config.infra, secrets)
        planner = ContestPlanner(client, config)
        plan = planner.plan_changes()
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not connect to DOMjudge API: {e}[/yellow]")
        console.print("[dim]Unable to show detailed preview[/dim]\n")
        return

    # Group changes by contest
    changes_by_contest: dict = {}
    for change in plan.changes:
        contest_id = change.identifier
        if contest_id not in changes_by_contest:
            changes_by_contest[contest_id] = []
        changes_by_contest[contest_id].append(change)

    # Render changes for each contest
    for contest_shortname, changes in changes_by_contest.items():
        # Find contest name
        contest_obj = next((c for c in config.contests if c.shortname == contest_shortname), None)
        contest_name = contest_obj.name if contest_obj else contest_shortname

        table = Table(
            title=f"Contest: {contest_name} ({contest_shortname})",
            box=box.ROUNDED,
            title_style="bold",
        )
        table.add_column("Resource", style="cyan", no_wrap=True)
        table.add_column("Action", no_wrap=True)
        table.add_column("Details", style="dim")

        # Add rows for each change
        for change in changes:
            action_style = _get_action_style(change.action)
            table.add_row(
                change.resource_type.capitalize(),
                f"[{action_style}]{change.action.value}[/{action_style}]",
                change.details,
            )

        console.print(table)
        console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")
    console.print(f"  • {plan.contest_count} contest(s) will be configured")
    console.print(f"  • Total problems: {plan.total_problems}")
    console.print(f"  • Total teams: {plan.total_teams}")
    console.print()
    console.print("[green]✓[/green] To apply these changes, run without --dry-run")
    console.print("[dim]  Example: dom contest apply --file config.yaml[/dim]")


def _get_action_style(action: ChangeAction) -> str:
    """
    Get Rich style for an action.

    Args:
        action: Change action

    Returns:
        Rich color style name
    """
    style_map = {
        ChangeAction.CREATE: "green",
        ChangeAction.UPDATE: "yellow",
        ChangeAction.LINK: "blue",
        ChangeAction.SKIP: "dim",
    }
    return style_map.get(action, "white")


@contest_command.command("verify-problemset")
@cli_command
def verify_problemset_command(
    contest: str = typer.Argument(
        ..., help="Name of the contest to verify its problemset", callback=validate_contest_name
    ),
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
) -> None:
    """
    Verify the problemset of the specified contest.

    This checks whether the submissions associated with the contest match the expected configuration.
    """
    # Dependency injection: create secrets manager at entry point
    secrets = get_secrets_manager()
    contest_config = load_contest_config(file, contest_name=contest, secrets=secrets)
    infra_config = load_infrastructure_config(file_path=file)
    verify_problemset_service(infra=infra_config, contest=contest_config, secrets=secrets)


@contest_command.command("inspect")
@cli_command
def inspect_contests_command(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    format: str = typer.Option(None, "--format", help="JMESPath expression to filter output."),
    show_secrets: bool = typer.Option(
        False, "--show-secrets", help="Include secret values instead of masking them"
    ),
) -> None:
    """
    Inspect loaded configuration. By default secret fields are masked;
    pass --show-secrets to reveal them.
    """
    # Dependency injection: create secrets manager at entry point
    secrets = get_secrets_manager()
    config = load_contests_config(file, secrets)
    data = [contest.inspect(show_secrets=show_secrets) for contest in config]

    if format:
        data = jmespath.search(format, data)

    # pretty-print or just print the dict
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
