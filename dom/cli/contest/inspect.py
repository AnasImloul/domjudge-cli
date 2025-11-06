"""Contest inspect command."""

import json
from datetime import datetime
from pathlib import Path

import jmespath
import typer

from dom.cli.contest.helpers import load_config_with_secrets
from dom.cli.helpers import add_global_options, cli_command
from dom.cli.validators import validate_file_path


@add_global_options
@cli_command
def inspect_command(
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
    # Load configuration
    config, _ = load_config_with_secrets(file, verbose)
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
