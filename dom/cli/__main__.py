import typer
from dom.cli.infra import infra_command
from dom.cli.contest import contest_command

app = typer.Typer(help="dom-cli: Manage DOMjudge infrastructure and contests.")

# Register commands
app.add_typer(infra_command, name="infra", help="Manage infrastructure & platform")
app.add_typer(contest_command, name="contest", help="Manage contests")

def main() -> None:
    app()
