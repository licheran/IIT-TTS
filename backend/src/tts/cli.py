"""`tts` command-line entry point. Commands are stubs until their phases land."""

import typer

app = typer.Typer(name="tts", help="IIT-TTS scheduling engine.", no_args_is_help=True)


def _not_implemented(command: str) -> None:
    typer.echo(f"tts {command}: not implemented", err=True)
    raise typer.Exit(code=1)


@app.command()
def solve() -> None:
    """Solve a workbook and write the result workbook."""
    _not_implemented("solve")


@app.command()
def validate() -> None:
    """Run the verifier on a workbook that contains assignments."""
    _not_implemented("validate")


@app.command("import-fet")
def import_fet() -> None:
    """Convert a FET groups HTML export into a workbook."""
    _not_implemented("import-fet")


@app.command()
def export() -> None:
    """Export a dataset as a workbook."""
    _not_implemented("export")
