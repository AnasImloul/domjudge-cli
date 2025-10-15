import json
from pathlib import Path

import jmespath
import typer
from rich.console import Console

from dom.cli.validators import validate_contest_name, validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.contest import (
    ApplyContestsOperation,
    LoadConfigOperation,
    PlanContestChangesOperation,
    VerifyProblemsetOperation,
)
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
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
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, dry_run=dry_run)

    # Build and execute an operation pipeline
    if dry_run:
        # For dry-run, load config and show preview
        result = OperationRunner(operation=LoadConfigOperation(file), show_progress=False).run(
            context
        )

        if result.is_success():
            _preview_contest_changes(result.unwrap(), secrets)
    else:
        # For actual apply, execute operations
        # Execute the load operation first
        load_runner = OperationRunner(LoadConfigOperation(file))
        load_result = load_runner.run(context)

        if not load_result.is_success():
            return

        config = load_result.unwrap()
        apply_runner = OperationRunner(ApplyContestsOperation(config))
        apply_runner.run(context)


def _preview_contest_changes(config, secrets: SecretsManager) -> None:
    """
    Preview what changes would be made without applying them.

    Uses the PlanContestChangesOperation to analyze changes, then displays them.

    Args:
        config: Complete DOMjudge configuration
        secrets: Secrets manager for retrieving credentials
    """
    console = Console()
    console.print("\n[bold cyan]🔍 DRY RUN - Preview Mode[/bold cyan]\n")
    console.print("[dim]No changes will be applied to the platform[/dim]\n")

    # Use operation to plan changes
    context = OperationContext(secrets=secrets)
    plan_operation = PlanContestChangesOperation(config)
    runner = OperationRunner(plan_operation, show_progress=False)
    result = runner.run(context)

    if not result.is_success():
        console.print("[yellow]⚠️  Could not analyze changes[/yellow]")
        console.print("[dim]Unable to show detailed preview[/dim]\n")
        return

    # Display the plan
    plan_summary = result.unwrap()
    console.print(plan_summary)
    console.print()
    console.print("[green]✓[/green] To apply these changes, run without --dry-run")
    console.print("[dim]  Example: dom contest apply --file config.yaml[/dim]")


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
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets)

    # Verify problemset using operation
    verify_runner = OperationRunner(VerifyProblemsetOperation(file, contest))
    verify_runner.run(context)


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
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets)

    # Load configuration
    load_runner = OperationRunner(LoadConfigOperation(file), show_progress=False)
    load_result = load_runner.run(context)

    if not load_result.is_success():
        return

    config = load_result.unwrap()
    data = [contest.inspect(show_secrets=show_secrets) for contest in config.contests]

    if format:
        data = jmespath.search(format, data)

    # pretty-print or just print the dict
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
