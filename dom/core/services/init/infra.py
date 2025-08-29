from dom.cli import console
from rich.table import Table
from dom.templates.init import infra_template
from dom.infrastructure.secrets.manager import generate_random_string

from dom.utils.prompt import ask
from dom.utils.validators import ValidatorBuilder


def initialize_infrastructure():
    # Infrastructure section
    console.print("\n[bold cyan]Infrastructure Configuration[/bold cyan]")
    console.print("Configure the platform settings for your contest environment")

    port = ask(
        "Port number",
        console=console,
        default="8080",
        parser=ValidatorBuilder.integer().min(1).max(65535).build(),
    )

    judges = ask(
        "Number of judges",
        console=console,
        default="2",
        parser=ValidatorBuilder.integer().min(1).max(16).build(),
    )

    password = ask(
        "Admin password",
        console=console,
        password=True,
        default=generate_random_string(length=16),
        show_default=False,
        parser=ValidatorBuilder.string().min_length(8).max_length(32).build(),
    )

    # Show infrastructure summary
    infra_table = Table(title="Infrastructure Configuration")
    infra_table.add_column("Setting", style="cyan")
    infra_table.add_column("Value", style="green")
    infra_table.add_row("Port", str(port))
    infra_table.add_row("Judges", str(judges))
    infra_table.add_row("Password", "****")
    console.print(infra_table)

    rendered = infra_template.render(
        port=port,
        judges=judges,
        password=password,
    )

    return rendered
