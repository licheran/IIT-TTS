"""`tts preflight`: the checks on their own, with the preset's labels and exit code 4."""

from pathlib import Path

from test_cli_solve import edited, import_to
from typer.testing import CliRunner

from tts.cli import app
from tts.presets import labeller

runner = CliRunner()


def test_a_clean_workbook_passes_with_exit_code_0(tmp_path: Path) -> None:
    result = runner.invoke(app, ["preflight", str(import_to(tmp_path, "l6.xlsx"))])
    assert result.exit_code == 0, result.output
    assert "Pre-flight: 0 error(s), 0 warning(s)." in result.output


def test_an_error_gives_exit_code_4_and_names_the_entity_with_preset_labels(
    tmp_path: Path,
) -> None:
    def block_a_teacher(workbook: object) -> None:
        availability = workbook["Availability"]  # type: ignore[index]
        periods = [c.value for c in workbook["Periods"]["A"][1:]]  # type: ignore[index]
        for day in [c.value for c in workbook["Days"]["A"][1:]]:  # type: ignore[index]
            for period in periods:
                availability.append(["HAWE", day, period, "unavailable"])

    broken = edited(import_to(tmp_path, "l6.xlsx"), tmp_path / "broken.xlsx", block_a_teacher)
    result = runner.invoke(app, ["preflight", str(broken)])
    assert result.exit_code == 4
    assert "ERROR over_demand: Teacher HAWE: needs 16 periods, 0 available" in result.output
    assert "Pre-flight: 1 error(s), 0 warning(s)." in result.output


def test_warnings_alone_do_not_fail(tmp_path: Path) -> None:
    def add_empty_scope(workbook: object) -> None:
        row = ["C1", "max_gaps", "type:Nothing", '{"max": 2}', False, 1, True]
        workbook["Constraints"].append(row)  # type: ignore[index]

    source = edited(import_to(tmp_path, "l6.xlsx"), tmp_path / "warn.xlsx", add_empty_scope)
    result = runner.invoke(app, ["preflight", str(source)])
    assert result.exit_code == 0
    assert "WARNING empty_scope: C1: scope matches nothing" in result.output


def test_a_workbook_with_problems_is_reported_and_exits_with_1(tmp_path: Path) -> None:
    def break_capacity(workbook: object) -> None:
        workbook["Rooms"].cell(row=2, column=4, value="thirty")  # type: ignore[index]

    bad = edited(import_to(tmp_path, "l6.xlsx"), tmp_path / "bad.xlsx", break_capacity)
    result = runner.invoke(app, ["preflight", str(bad)])
    assert result.exit_code == 1
    assert 'Rooms!R2C4 [capacity]: expected integer ≥ 0, got "thirty"' in result.output


def test_it_needs_a_workbook_extension_it_knows(tmp_path: Path) -> None:
    other = tmp_path / "book.txt"
    other.write_text("x", "utf-8")
    result = runner.invoke(app, ["preflight", str(other)])
    assert result.exit_code == 2
    assert "use .xlsx or .zip" in result.output


def test_the_labeller_of_a_preset_words_its_types_and_others_pass_through() -> None:
    label = labeller("academic_weekly")
    assert label("Teacher") == "Teacher"
    assert label("StudentGroup") == "Group"
    assert label("Room") == "Room"
    assert labeller("no_such_preset")("StudentGroup") == "StudentGroup"
    assert labeller("")("anything") == "anything"
