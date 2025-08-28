from dom.cli import console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from jinja2 import Environment, PackageLoader, select_autoescape
from dom.infrastructure.secrets.manager import generate_random_password


def initialize_infrastructure():
    env = Environment(
        loader=PackageLoader("dom", "templates"),
        autoescape=select_autoescape()
    )

    template = env.get_template("init/infra.yml.j2")

    # Infrastructure section
    console.print("\n[bold cyan]Infrastructure Configuration[/bold cyan]")
    console.print("Configure the platform settings for your contest environment")
    
    while True:
        port = Prompt.ask("Port number", default="8080", console=console)
        if port.isdigit() and 1 <= int(port) <= 65535:
            port = int(port)
            break
        console.print("[red]Please enter a valid port number (1-65535).[/red]")

    while True:
        judges = Prompt.ask("Number of judges", default="2", console=console)
        if judges.isdigit() and int(judges) > 0:
            judges = int(judges)
            break
        console.print("[red]Please enter a positive integer for judges.[/red]")

    password = Prompt.ask("Admin password", password=True, console=console)
    if not password:
        password = generate_random_password(22)
    
    # Show infrastructure summary
    infra_table = Table(title="Infrastructure Configuration")
    infra_table.add_column("Setting", style="cyan")
    infra_table.add_column("Value", style="green")
    infra_table.add_row("Port", str(port))
    infra_table.add_row("Judges", str(judges))
    infra_table.add_row("Password", "****")
    console.print(infra_table)

    rendered = template.render(
        port=port,
        judges=judges,
        password=password
    )

    return rendered
