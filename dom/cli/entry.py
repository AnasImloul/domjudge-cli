import typer

app = typer.Typer()

@app.command()
def init():
    """Initialize the config and Docker files."""
    ## setup_domjudge(init_only=True)
    pass

@app.command()
def up():
    """Start the DOMjudge containers."""
    ## setup_domjudge()
    pass


if __name__ == "__main__":
    app()
