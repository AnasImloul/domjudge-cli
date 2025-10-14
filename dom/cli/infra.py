from pathlib import Path

import typer

from dom.cli.validators import validate_file_path
from dom.core.config.loaders import load_infrastructure_config
from dom.core.services.infra.apply import apply_infra_and_platform
from dom.core.services.infra.destroy import destroy_infra_and_platform
from dom.core.services.infra.status import (
    check_infrastructure_status,
    print_status_human_readable,
    print_status_json,
)
from dom.exceptions import DomJudgeCliError
from dom.infrastructure.secrets.manager import SecretsManager
from dom.logging_config import get_logger
from dom.utils.cli import ensure_dom_directory

logger = get_logger(__name__)
infra_command = typer.Typer()


@infra_command.command("apply")
def apply_from_config(
    file: str = typer.Option(
        None, "-f", "--file", help="Path to configuration YAML file", callback=validate_file_path
    ),
) -> None:
    """
    Apply configuration to infrastructure and platform.
    """
    try:
        # Dependency injection: create secrets manager at entry point
        config = load_infrastructure_config(file)
        secrets = SecretsManager(Path(ensure_dom_directory()))
        apply_infra_and_platform(config, secrets)
    except DomJudgeCliError as e:
        logger.error(f"Failed to apply infrastructure: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.error(f"Unexpected error applying infrastructure: {e}", exc_info=True)
        raise typer.Exit(code=1) from e


@infra_command.command("destroy")
def destroy_all(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm destruction"),
) -> None:
    """
    Destroy all infrastructure and platform resources.

    WARNING: This will permanently remove all containers, volumes, and data.
    """
    if not confirm:
        typer.echo("❗ Use --confirm to actually destroy infrastructure.")
        typer.echo("   This action is irreversible and will delete all data.")
        raise typer.Exit(code=1)

    try:
        # Dependency injection: create secrets manager at entry point
        secrets = SecretsManager(Path(ensure_dom_directory()))
        destroy_infra_and_platform(secrets)
    except DomJudgeCliError as e:
        logger.error(f"Failed to destroy infrastructure: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.error(f"Unexpected error destroying infrastructure: {e}", exc_info=True)
        raise typer.Exit(code=1) from e


@infra_command.command("status")
def check_status(
    file: str = typer.Option(
        None,
        "-f",
        "--file",
        help="Path to configuration YAML file (optional, for expected judgehost count)",
        callback=validate_file_path,
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output in JSON format instead of human-readable"
    ),
) -> None:
    """
    Check the health status of DOMjudge infrastructure.

    This command checks:
    - Docker daemon availability
    - DOMserver container status
    - MariaDB container status
    - Judgehost containers status
    - MySQL client container status

    Returns exit code 0 if all systems healthy, 1 otherwise.
    Useful for CI/CD pipelines and automation scripts.
    """
    try:
        # Load config if provided (to know expected judgehost count)
        config = None
        if file:
            config = load_infrastructure_config(file)

        # Check status
        status = check_infrastructure_status(config)

        # Output results
        if json_output:
            print_status_json(status)
        else:
            print_status_human_readable(status)

        # Exit with appropriate code
        if not status.is_healthy():
            raise typer.Exit(code=1)

    except DomJudgeCliError as e:
        logger.error(f"Failed to check infrastructure status: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.error(f"Unexpected error checking infrastructure status: {e}", exc_info=True)
        raise typer.Exit(code=1) from e
