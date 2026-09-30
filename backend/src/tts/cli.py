"""`tts` command-line entry point: solve, validate, preflight, import-fet and export."""

import json
from pathlib import Path
from typing import Annotated

import typer

from tts.core.model import Dataset, Result, Violation
from tts.core.run import RunParams
from tts.core.score import Score, score
from tts.core.verifier import hard_violations, verify
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
from tts.preflight.checks import Issue, run_preflight
from tts.presets import labeller, with_defaults
from tts.solver.compile import compile_model
from tts.solver.explain import explain
from tts.solver.registry import UnsupportedConstraintError
from tts.solver.solve import solve_model

app = typer.Typer(name="tts", help="IIT-TTS scheduling engine.", no_args_is_help=True)


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


def _summarise(violations: list[Violation]) -> str:
    hard = len(hard_violations(violations))
    soft = sum(v.severity == "soft" for v in violations)
    warnings = sum(v.severity == "warning" for v in violations)
    return f"{hard} hard violation(s), {soft} soft, {warnings} warning(s)"


def _print_score(result: Score) -> None:
    """The weighted score and its largest parts."""
    parts = sorted(result.breakdown.items(), key=lambda item: (-item[1].score, item[0]))
    detail = ", ".join(
        f"{code} {line.score} ({line.penalty} x {line.weight})" for code, line in parts
    )
    typer.echo(f"Score: {result.total}" + (f" ({detail})" if detail else "") + ".")


def _preflight(command: str, dataset: Dataset) -> list[Issue]:
    """Run the pre-flight checks and print them. Exit with code 4 if any is an error."""
    issues = run_preflight(dataset, labeller(dataset.preset))
    for issue in issues:
        line = f"{issue.severity.upper()} {issue.kind}: {issue.message}"
        typer.echo(line, err=issue.severity == "error")
    errors = sum(i.severity == "error" for i in issues)
    typer.echo(f"Pre-flight: {errors} error(s), {len(issues) - errors} warning(s).")
    if errors:
        raise _fail(command, f"{errors} pre-flight error(s); nothing was solved", code=4)
    return issues


@app.command()
def preflight(
    workbook: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="A workbook (.xlsx or CSV .zip).")
    ],
) -> None:
    """Run the pre-flight checks on a workbook, without solving.

    Finds what makes a timetable impossible before the solver starts: unknown references, events
    with no possible start, requirements no room can meet, resources that need more periods than
    they have, and pins that collide. Warnings (pressure on a pool, unused resources, empty
    scopes) are printed but do not fail.

    Exit codes: 0 no errors, 1 the workbook could not be read, 4 at least one error.
    """
    data = _report("preflight", _read_workbook("preflight", workbook))
    _preflight("preflight", data.dataset)


@app.command()
def solve(
    workbook: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="A workbook (.xlsx or CSV .zip).")
    ],
    out: Annotated[Path, typer.Option("--out", "-o", help="Result file: .xlsx or .zip (CSV).")],
    time_limit: Annotated[float, typer.Option(help="Seconds the search may take.")] = 120.0,
    workers: Annotated[
        int | None, typer.Option(help="Search workers (default: one per CPU).")
    ] = None,
    seed: Annotated[
        int, typer.Option(help="Random seed. Same seed and 1 worker: same result.")
    ] = 0,
) -> None:
    """Solve a workbook and write it back with an Assignments sheet.

    The pre-flight checks run first (see `tts preflight`); an error stops the solve. Every result
    is re-checked by the independent verifier. Exit codes: 0 a valid timetable was written, 1 the
    workbook could not be read or solved, 2 no timetable exists (or none was found in time),
    3 the solver's result broke a hard rule and was not written, 4 pre-flight found an error.
    When no timetable exists, the rules that conflict are named (the infeasibility explanation).
    """
    data = _report("solve", _read_workbook("solve", workbook))
    if data.result is not None:
        typer.echo("Note: the workbook's Assignments are ignored; they are solved again.")
    _preflight("solve", data.dataset)
    params = RunParams(time_limit_s=time_limit, num_workers=workers, seed=seed)
    try:
        outcome = solve_model(compile_model(data.dataset), params)
    except UnsupportedConstraintError as error:
        raise _fail("solve", str(error)) from error

    stats = outcome.stats
    typer.echo(
        f"Solver: {outcome.status} in {stats.wall_time_s:.2f} s "
        f"({stats.workers} worker(s), seed {stats.seed}, {stats.conflicts} conflicts)."
    )
    for warning in outcome.warnings:
        typer.echo(f"Warning: {warning}")
    if outcome.result is None:
        for problem in outcome.problems:
            typer.echo(f"Problem: {problem}", err=True)
        if outcome.status == "infeasible":
            diagnostic = explain(data.dataset, labeller(data.dataset.preset))
            if diagnostic is not None:
                typer.echo(f"Explanation: {diagnostic.message}", err=True)
        reason = "no timetable exists" if outcome.status == "infeasible" else "none found in time"
        raise _fail("solve", f"no result ({outcome.status}): {reason}", code=2)

    violations = verify(data.dataset, outcome.result)
    typer.echo(f"Verifier: {_summarise(violations)}.")
    _print_score(score(data.dataset, violations))
    if hard_violations(violations):
        for violation in hard_violations(violations):
            typer.echo(f"Violation: {violation.message}", err=True)
        raise _fail("solve", "the result breaks a hard rule and was not written (a bug)", code=3)
    result_data = WorkbookData(
        data.dataset, outcome.result, meta=data.meta, notes=data.notes, run=f"seed-{seed}"
    )
    _write_workbook("solve", result_data, out)
    typer.echo(f"Wrote {out}.")


@app.command()
def validate(
    workbook: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, help="A workbook with an Assignments sheet."),
    ],
) -> None:
    """Check the assignments in a workbook with the independent verifier.

    Exit codes: 0 no hard violation, 1 the workbook could not be read or has no assignments,
    3 at least one hard violation.
    """
    data = _report("validate", _read_workbook("validate", workbook))
    if data.result is None:
        raise _fail("validate", "the workbook has no Assignments sheet to check")
    violations = verify(data.dataset, data.result)
    for violation in violations:
        typer.echo(f"{violation.severity.upper()} {violation.constraint_code}: {violation.message}")
    typer.echo(f"Verifier: {_summarise(violations)}.")
    _print_score(score(data.dataset, violations))
    if hard_violations(violations):
        raise typer.Exit(code=3)


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
    no_defaults: Annotated[
        bool,
        typer.Option("--no-defaults", help="Leave out the preset's default soft constraints."),
    ] = False,
) -> None:
    """Convert a FET groups HTML export into a workbook.

    The preset's default soft constraints (fewer gaps, no Saturday teaching, ...) are added to
    the Constraints sheet unless `--no-defaults` is given.

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
    if not no_defaults:
        dataset = with_defaults(dataset)

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
