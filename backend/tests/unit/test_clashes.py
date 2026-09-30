"""Clashes between timetables of different datasets (P10.3)."""

import sys
from pathlib import Path

from typer.testing import CliRunner

from fixtures import at, ev, make_dataset, make_result, res
from tts.cli import app
from tts.core.clashes import cross_clashes
from tts.core.model import Dataset, Event, FixedRequirement
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.presets.academic_weekly import PRESET_NAME, types

sys.path.insert(0, str(Path(__file__).parent.parent / "scale"))
from generate import time_model  # noqa: E402


def one(event: str, teacher: str = "t1") -> Dataset:
    return make_dataset(
        days=1, periods=3, resources=[res(teacher, "T")], events=[ev(event, duration=2)],
        fixed=[(event, teacher)],
    )  # fmt: skip


def test_a_shared_resource_used_at_once_by_two_timetables_is_a_clash() -> None:
    found = cross_clashes(
        [
            ("A", one("a1"), make_result(at("a1", "d1", "p1"))),
            ("B", one("b1"), make_result(at("b1", "d1", "p2"))),
        ]
    )
    assert [(c.resource, c.day, c.period, c.uses) for c in found] == [
        ("t1", "d1", "p2", (("A", "a1"), ("B", "b1")))
    ]


def test_separate_times_or_resources_do_not_clash() -> None:
    apart = [
        ("A", one("a1"), make_result(at("a1", "d1", "p1"))),
        ("B", one("b1", teacher="t2"), make_result(at("b1", "d1", "p1"))),
    ]
    assert cross_clashes(apart) == []
    assert cross_clashes([("A", one("a1"), make_result(at("a1", "d1", "p1")))]) == []


def test_the_command_reports_clashes_between_workbooks(tmp_path: Path) -> None:
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    runner = CliRunner()
    for path, dataset, result in (
        (a, l6_like("a1"), make_result(at("a1", "Mon", "P01"))),
        (b, l6_like("b1"), make_result(at("b1", "Mon", "P01"))),
    ):
        export_xlsx(WorkbookData(dataset, result), path)
    out = runner.invoke(app, ["clashes", str(a), str(b)])
    assert out.exit_code == 3, out.output
    assert "CLASH ABC on Mon P01: a1 (a.xlsx), b1 (b.xlsx)" in out.output
    assert "Clashes: 2 across 2 workbooks." in out.output  # P01 and P02
    assert runner.invoke(app, ["clashes", str(a)]).exit_code == 2


def l6_like(event: str) -> Dataset:
    """A one-event academic dataset (the workbook format needs the academic sheets)."""
    return Dataset(
        preset=PRESET_NAME,
        resource_types=types.RESOURCE_TYPES,
        reference_types=types.REFERENCE_TYPES,
        resources=(res("ABC", types.TEACHER),),
        time=time_model(("Mon", "Tue")),
        events=(Event(code=event, kind="LEC", duration=2, start_pattern="2H", delivery="online"),),
        fixed=(FixedRequirement(event=event, resource="ABC"),),
    )
