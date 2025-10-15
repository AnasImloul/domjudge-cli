from rich.console import Console
from rich.table import Table

from dom.infrastructure.secrets.manager import generate_random_string
from dom.templates.init import infra_template
from dom.utils.prompt import ask
from dom.validation import ValidationRules, for_prompt

console = Console()


def initialize_infrastructure():
    # Infrastructure section
    console.print("\n[bold cyan]Infrastructure Configuration[/bold cyan]")
    console.print("Configure the platform settings for your contest environment")

    # Use centralized validation rules - SINGLE SOURCE OF TRUTH
    port = ask(
        "Port number",
        console=console,
        default="8080",
        parser=for_prompt(ValidationRules.port()),
    )

    judges = ask(
        "Number of judges",
        console=console,
        default="2",
        parser=for_prompt(ValidationRules.judges_count()),
    )

    password = ask(
        "Admin password",
        console=console,
        password=True,
        default=generate_random_string(length=16),
        show_default=False,
        parser=for_prompt(ValidationRules.password()),
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
