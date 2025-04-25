import typer
from dom.cli.plan import plan_command
from dom.cli.apply import apply_command
from dom.cli.destroy import destroy_command

app = typer.Typer(help="dom-cli: Manage DOMjudge infrastructure and contests.")

# Register commands
app.add_typer(plan_command, help="Preview changes")
app.add_typer(apply_command, help="Apply configuration")
app.add_typer(destroy_command, help="Destroy infrastructure and platform resources")

def main() -> None:
    app()
