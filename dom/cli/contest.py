import json
from datetime import datetime
from pathlib import Path

import jmespath
import typer
from rich.console import Console

from dom.cli.validators import validate_contest_name, validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.contest import (
    ApplyContestsOperation,
    LoadConfigOperation,
    VerifyProblemsetOperation,
)
from dom.logging_config import get_logger
from dom.utils.cli import add_global_options, cli_command, get_secrets_manager

logger = get_logger(__name__)
contest_command = typer.Typer()


@contest_command.command("apply")
@add_global_options
@cli_command
def apply_from_config(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying them"),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001  # noqa: ARG001
) -> None:
    """
    Apply configuration to contests on the platform.

    Use --dry-run to preview what changes would be made without actually applying them.
    This is useful for validating configuration before making changes.
    """
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)

    # Build and execute an operation pipeline
    if dry_run:
        # For dry-run, load config (with dry_run=False since it's read-only) and show preview
        load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
        result = OperationRunner(operation=LoadConfigOperation(file), show_progress=True).run(
            load_context
        )

        if result.is_success():
            _preview_contest_changes(result.unwrap())
    else:
        # For actual apply, execute operations
        # Execute the load operation first
        context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
        load_runner = OperationRunner(LoadConfigOperation(file))
        load_result = load_runner.run(context)

        if not load_result.is_success():
            return

        config = load_result.unwrap()
        apply_runner = OperationRunner(ApplyContestsOperation(config))
        apply_runner.run(context)


def _preview_contest_changes(config) -> None:
    """
    Preview what changes would be made without applying them.

    Args:
        config: Complete DOMjudge configuration
    """
    console = Console()
    console.print("\n[bold cyan]> DRY RUN - Preview Mode[/bold cyan]\n")
    console.print("[dim]No changes will be applied to the platform[/dim]\n")

    # Calculate unique problems and teams across all contests
    unique_problem_ids = set()
    unique_team_ids = set()

    for contest in config.contests:
        for problem in contest.problems:
            # Use problem short_name as identifier
            unique_problem_ids.add(problem.ini.short_name)
        for team in contest.teams:
            # Use team name as identifier (teams with same name are considered the same)
            unique_team_ids.add(team.name)

    # Display summary with accurate unique counts
    console.print("Planned changes:")
    console.print(f"  - Contests: {len(config.contests)}")
    console.print(f"  - Unique Problems: {len(unique_problem_ids)}")
    console.print(f"  - Unique Teams: {len(unique_team_ids)}")

    # Show per-contest breakdown
    console.print("\n[yellow]Per-contest breakdown:[/yellow]")
    for contest in config.contests:
        problem_count = len(contest.problems)
        team_count = len(contest.teams)
        console.print(f"  [cyan]{contest.shortname}[/cyan]: {problem_count}p / {team_count}t")

    console.print()
    console.print("[green]+[/green] To apply these changes, run without --dry-run")
    console.print("[dim]  Example: dom contest apply --file config.yaml[/dim]")


@contest_command.command("verify-problemset")
@add_global_options
@cli_command
def verify_problemset_command(
    contest: str = typer.Argument(
        ..., help="Name of the contest to verify its problemset", callback=validate_contest_name
    ),
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview what would be verified without actually verifying"
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Verify the problemset of the specified contest.

    This checks whether the submissions associated with the contest match the expected configuration.
    Use --dry-run to preview what would be checked without actually performing the verification.
    """
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)

    # Verify problemset using operation (disable progress bar since verification has its own)
    verify_runner = OperationRunner(VerifyProblemsetOperation(file, contest), show_progress=False)
    verify_runner.run(context)


@contest_command.command("inspect")
@add_global_options
@cli_command
def inspect_contests_command(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    format: str = typer.Option(None, "--format", help="JMESPath expression to filter output."),
    show_secrets: bool = typer.Option(
        False, "--show-secrets", help="Include secret values instead of masking them"
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Inspect loaded configuration. By default secret fields are masked;
    pass --show-secrets to reveal them.
    """
    # Create execution context
    secrets = get_secrets_manager()
    context = OperationContext(secrets=secrets, verbose=verbose)

    # Load configuration
    load_runner = OperationRunner(LoadConfigOperation(file), show_progress=False)
    load_result = load_runner.run(context)

    if not load_result.is_success():
        return

    config = load_result.unwrap()
    data = [contest.inspect(show_secrets=show_secrets) for contest in config.contests]

    if format:
        data = jmespath.search(format, data)

    # Custom JSON encoder to handle datetime objects
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    # pretty-print or just print the dict
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2, default=json_serializer))
