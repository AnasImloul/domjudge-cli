import typer
from dom.core.config.loaders import load_config, load_contest_config, load_infrastructure_config
from dom.core.services.contest.apply import apply_contests
from dom.core.services.problem.verify import verify_problemset as verify_problemset_service

contest_command = typer.Typer()

@contest_command.command("apply")
def apply_from_config(
    file: str = typer.Option(None, "-f", "--file", help="Path to configuration YAML file")
) -> None:
    """
    Apply configuration to contests on the platform.
    """
    config = load_config(file)
    apply_contests(config)

@contest_command.command("verify-problemset")
def verify_problemset_command(
    contest: str = typer.Argument(..., help="Name of the contest to verify its problemset"),
    file: str = typer.Option(None, "-f", "--file", help="Path to configuration YAML file"),
) -> None:
    """
    Verify the problemset of the specified contest.

    This checks whether the submissions associated with the contest match the expected configuration.
    """
    contest_config = load_contest_config(file, contest_name=contest)
    infra_config = load_infrastructure_config(file_path=file)
    verify_problemset_service(infra=infra_config, contest=contest_config)
