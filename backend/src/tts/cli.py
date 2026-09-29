"""`tts` command-line entry point. Commands are stubs until their phases land."""

import json
from pathlib import Path
from typing import Annotated

import typer

from tts.core.model import Dataset, Result
from tts.io.csvzip import export_csvzip, import_csvzip
from tts.io.fet_html import (
    Assumptions,
    FetConversionError,
    FetParseError,
    parse_fet_groups_html,
    to_dataset,
)
from tts.io.importer import ImportOutcome
from tts.io.tables import WorkbookData, WorkbookError
from tts.io.workbook import export_xlsx, import_xlsx

app = typer.Typer(name="tts", help="IIT-TTS scheduling engine.", no_args_is_help=True)


def _not_implemented(command: str) -> None:
    typer.echo(f"tts {command}: not implemented", err=True)
    raise typer.Exit(code=1)


def _fail(command: str, message: str, code: int = 1) -> typer.Exit:
    typer.echo(f"tts {command}: {message}", err=True)
    return typer.Exit(code=code)


def _write_workbook(command: str, data: WorkbookData, out: Path) -> None:
    """Write `.xlsx` or a CSV `.zip`, chosen by the file's extension."""
    suffix = out.suffix.lower()
    try:
        if suffix == ".xlsx":
            export_xlsx(data, out)
        elif suffix == ".zip":
            export_csvzip(data, out)
        else:
            raise _fail(command, f'cannot tell the format of "{out}": use .xlsx or .zip', code=2)
    except WorkbookError as error:
        raise _fail(command, str(error)) from error


def _read_workbook(command: str, path: Path) -> ImportOutcome:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return import_xlsx(path)
    if suffix == ".zip":
        return import_csvzip(path)
    raise _fail(command, f'cannot tell the format of "{path}": use .xlsx or .zip', code=2)


def _report(command: str, outcome: ImportOutcome) -> WorkbookData:
    """The data of a successful import, or every problem printed and an exit with code 1."""
    if outcome.data is None:
        for issue in outcome.errors:
            typer.echo(issue.format(), err=True)
        raise _fail(command, f"{len(outcome.errors)} problem(s) found; nothing was read")
    return outcome.data


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
    out: Annotated[
        Path, typer.Option("--out", "-o", help="File to write: .xlsx, .zip (CSV) or .json.")
    ],
    with_assignments: Annotated[
        bool, typer.Option("--with-assignments", help="Also write the export's own placements.")
    ] = False,
) -> None:
    """Convert a FET groups HTML export into a workbook.

    Values the export lacks (group sizes, room capacities, ...) are assumptions. They are written
    to the workbook's `_meta` sheet as `assumptions`. A `.json` file holds the dataset, the
    placements, the assumptions and any label/grid anomalies instead.
    """
    assumptions = Assumptions()
    try:
        fet = parse_fet_groups_html(html)
        dataset, result = to_dataset(fet, assumptions=assumptions)
    except (FetParseError, FetConversionError) as error:
        raise _fail("import-fet", str(error)) from error

    if out.suffix.lower() == ".json":
        payload = {
            "format": "tts-import-json",
            "assumptions": assumptions.describe().splitlines(),
            "anomalies": list(fet.anomalies),
            "dataset": dataset.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
        }
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        data = WorkbookData(
            dataset,
            result if with_assignments else None,
            meta={"institution": fet.institution, "assumptions": assumptions.describe()},
            run="fet" if with_assignments else "",
        )
        _write_workbook("import-fet", data, out)
    typer.echo(f"Read {len(fet.groups)} groups and {len(dataset.events)} events; wrote {out}.")
    for anomaly in fet.anomalies:
        typer.echo(f"Anomaly: {anomaly}")


@app.command()
def export(
    source: Annotated[
        Path,
        typer.Argument(
            exists=True, dir_okay=False, help="A workbook (.xlsx or CSV .zip) or an import .json."
        ),
    ],
    out: Annotated[Path, typer.Option("--out", "-o", help="File to write: .xlsx or .zip (CSV).")],
    with_assignments: Annotated[
        bool,
        typer.Option("--with-assignments", help="From an import .json: include the placements."),
    ] = False,
) -> None:
    """Rewrite a workbook in canonical form, in either format.

    Reads the whole workbook first, so a workbook with problems is reported, not converted.
    Assignments the input holds are kept.
    """
    if source.suffix.lower() == ".json":
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            dataset = Dataset.model_validate(payload["dataset"])
            result = Result.model_validate(payload["result"]) if with_assignments else None
            meta = {"assumptions": "\n".join(payload.get("assumptions", []))}
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise _fail("export", f"{source} is not an import .json ({error})") from error
        data = WorkbookData(dataset, result, meta={k: v for k, v in meta.items() if v})
    else:
        data = _report("export", _read_workbook("export", source))
    _write_workbook("export", data, out)
    typer.echo(f"Wrote {out}.")
