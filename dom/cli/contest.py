import json
from datetime import datetime
from pathlib import Path

import jmespath
import typer

from dom.cli.validators import validate_contest_name, validate_file_path
from dom.core.operations import OperationContext, OperationRunner
from dom.core.operations.contest import (
    ApplyContestsOperation,
    LoadConfigOperation,
    PlanContestChangesOperation,
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
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Apply configuration to contests on the platform.

    Use --dry-run to preview what changes would be made without actually applying them.
    This is useful for validating configuration before making changes.
    """
    # Create execution context
    secrets = get_secrets_manager()

    # Load configuration (always runs, even in dry-run mode, since it's read-only)
    load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    load_runner = OperationRunner(LoadConfigOperation(file))
    load_result = load_runner.run(load_context)

    if not load_result.is_success():
        raise typer.Exit(code=1)

    config = load_result.unwrap()

    # Apply contests with context (operations handle dry-run)
    apply_context = OperationContext(secrets=secrets, dry_run=dry_run, verbose=verbose)
    apply_runner = OperationRunner(ApplyContestsOperation(config))
    apply_result = apply_runner.run(apply_context)

    # Don't treat dry-run (skipped) as failure
    if apply_result.is_failure():
        raise typer.Exit(code=1)


@contest_command.command("plan")
@add_global_options
@cli_command
def plan_changes(
    file: Path = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
    verbose: bool = False,
    no_color: bool = False,  # noqa: ARG001
) -> None:
    """
    Show what changes would be made to contests without applying them.

    This command analyzes your configuration and displays:
    - Which contests would be created
    - Which contests would be updated and what fields would change
    - Which problems/teams would be added

    This is more detailed than --dry-run and shows actual differences
    between current state and desired configuration.
    """
    # Create execution context
    secrets = get_secrets_manager()

    # Load configuration
    load_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    load_runner = OperationRunner(LoadConfigOperation(file))
    load_result = load_runner.run(load_context)

    if not load_result.is_success():
        raise typer.Exit(code=1)

    config = load_result.unwrap()

    # Plan changes
    plan_context = OperationContext(secrets=secrets, dry_run=False, verbose=verbose)
    plan_runner = OperationRunner(PlanContestChangesOperation(config), show_progress=False)
    plan_result = plan_runner.run(plan_context)

    if plan_result.is_failure():
        raise typer.Exit(code=1)


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
