"""`tts` command-line entry point. Commands are stubs until their phases land."""

import json
from pathlib import Path
from typing import Annotated

import typer

from tts.io.fet_html import (
    Assumptions,
    FetConversionError,
    FetParseError,
    parse_fet_groups_html,
    to_dataset,
)

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
def import_fet(
    html: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="A FET groups HTML export.")
    ],
    out: Annotated[Path, typer.Option("--out", "-o", help="File to write.")],
) -> None:
    """Convert a FET groups HTML export into a dataset.

    Writes JSON for now: the workbook writer arrives in Phase 3, after which this command writes
    the .xlsx workbook instead. The JSON holds the dataset, the original placements, the
    assumptions made for values the export lacks, and any label/grid anomalies.
    """
    assumptions = Assumptions()
    try:
        fet = parse_fet_groups_html(html)
        dataset, result = to_dataset(fet, assumptions=assumptions)
    except (FetParseError, FetConversionError) as error:
        typer.echo(f"tts import-fet: {error}", err=True)
        raise typer.Exit(code=1) from error

    payload = {
        "format": "tts-import-json",
        "assumptions": assumptions.describe().splitlines(),
        "anomalies": list(fet.anomalies),
        "dataset": dataset.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    typer.echo(
        f"Read {len(fet.groups)} groups and {len(dataset.events)} events; wrote JSON to {out} "
        "(workbook output arrives in Phase 3)."
    )
    for anomaly in fet.anomalies:
        typer.echo(f"Anomaly: {anomaly}")


@app.command()
def export() -> None:
    """Export a dataset as a workbook."""
    _not_implemented("export")
