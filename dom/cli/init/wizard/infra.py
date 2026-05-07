from rich.table import Table

from dom import ui
from dom.infrastructure.secrets.manager import generate_random_string
from dom.templates.init import infra_template
from dom.validation import ValidationRules, for_prompt


def initialize_infrastructure():
    ui.header("Infrastructure Configuration")
    ui.info("Configure the platform settings for your contest environment")

    port = ui.ask(
        "Port number",
        default="8080",
        parser=for_prompt(ValidationRules.port()),
    )

    judges = ui.ask(
        "Number of judges",
        default="2",
        parser=for_prompt(ValidationRules.judges_count()),
    )

    password = ui.ask(
        "Admin password",
        password=True,
        default=generate_random_string(length=16),
        show_default=False,
        parser=for_prompt(ValidationRules.password()),
    )

    infra_table = Table(title="Infrastructure Configuration")
    infra_table.add_column("Setting", style="cyan")
    infra_table.add_column("Value", style="green")
    infra_table.add_row("Port", str(port))
    infra_table.add_row("Judges", str(judges))
    infra_table.add_row("Password", "****")
    ui.render(infra_table)

    return infra_template.render(port=port, judges=judges, password=password)
