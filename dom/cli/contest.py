import typer
import jmespath
import json
from dom.core.config.loaders import load_config, load_contest_config, load_infrastructure_config, load_contests_config
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


@contest_command.command("inspect")
def inspect_contests_command(
    file: str = typer.Option(None, "-f", "--file", help="Path to configuration YAML file"),
    format: str = typer.Option(None, "--format", help="JMESPath expression to filter output."),
    show_secrets: bool = typer.Option(
        False, "--show-secrets", help="Include secret values instead of masking them"
    ),
) -> None:
    """
    Inspect loaded configuration. By default secret fields are masked;
    pass --show-secrets to reveal them.
    """
    config = load_contests_config(file)
    data = [
        contest.inspect(show_secrets=show_secrets)
        for contest in config
    ]

    if format:
        data = jmespath.search(format, data)

    # pretty-print or just print the dict
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
