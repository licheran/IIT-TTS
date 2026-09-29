"""`import(export(ds)) == ds` and `export(import(wb)) == canonical(wb)`, for both containers."""

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from generators import academic_datasets
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tts.core.model import Dataset, Result
from tts.io.csvzip import export_csvzip, import_csvzip
from tts.io.fet_html import parse_fet_groups_html, to_dataset
from tts.io.importer import ImportOutcome
from tts.io.tables import WorkbookData, build_tables
from tts.io.workbook import export_xlsx, import_xlsx
from tts.presets.academic_weekly.preset import PRESET

L6_HTML = Path(__file__).resolve().parents[1] / "fixtures" / "l6" / "fet-groups-export.html"

Writer = Callable[[WorkbookData, Any], None]
Reader = Callable[[bytes], ImportOutcome]
CONTAINERS: dict[str, tuple[Writer, Reader]] = {
    "xlsx": (export_xlsx, import_xlsx),
    "csvzip": (export_csvzip, import_csvzip),
}


def roundtrip(container: str, data: WorkbookData) -> ImportOutcome:
    write, read = CONTAINERS[container]
    buffer = io.BytesIO()
    write(data, buffer)
    return read(buffer.getvalue())


@pytest.fixture(scope="module")
def l6() -> tuple[Dataset, Result]:
    return to_dataset(parse_fet_groups_html(L6_HTML))


@pytest.mark.parametrize("container", CONTAINERS)
def test_l6_round_trips(container: str, l6: tuple[Dataset, Result]) -> None:
    data = WorkbookData(l6[0], l6[1], meta={"institution": "IIT", "assumptions": "a\nb"}, run="fet")
    outcome = roundtrip(container, data)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data == data


@pytest.mark.parametrize("container", CONTAINERS)
def test_l6_exports_the_same_tables_after_a_round_trip(
    container: str, l6: tuple[Dataset, Result]
) -> None:
    data = WorkbookData(l6[0], l6[1])
    again = roundtrip(container, data).data
    assert again is not None
    assert build_tables(again, PRESET) == build_tables(data, PRESET)


def test_an_xlsx_and_a_csv_zip_of_the_same_data_read_back_the_same(
    l6: tuple[Dataset, Result],
) -> None:
    data = WorkbookData(l6[0], l6[1])
    assert roundtrip("xlsx", data).data == roundtrip("csvzip", data).data


NOTES: dict[tuple[str, str], dict[str, str]] = {
    ("Teachers", "HAWE"): {"x_comment": "head of dept"},
    ("Teachers", "HARR"): {"x_comment": "part time", "x_phone": "123"},
    ("Rooms", "Auditorium"): {"x_owner": "estates"},
    ("Groups", "L6 SE / G1"): {"x_rep": "Ann"},
    ("Activities", "6SENG010W-LEC-01"): {"x_note": "keep on Tuesday"},
    ("ActivityTeachers", "6SENG010W-LEC-01\x1fSALIP"): {"x_why": "lead"},
    ("Constraints", "C1"): {"x_ignored": "row does not exist"},
}


@pytest.mark.parametrize("container", CONTAINERS)
def test_x_columns_survive_and_stay_out_of_the_dataset(
    container: str, l6: tuple[Dataset, Result]
) -> None:
    plain = WorkbookData(l6[0], l6[1])
    noted = WorkbookData(l6[0], l6[1], notes=NOTES)
    outcome = roundtrip(container, noted)
    assert outcome.data is not None
    assert outcome.data.dataset == plain.dataset
    kept = {k: v for k, v in NOTES.items() if k[0] != "Constraints"}  # that row does not exist
    assert dict(outcome.data.notes) == kept


@pytest.mark.parametrize("container", CONTAINERS)
def test_notes_are_exported_the_same_after_a_round_trip(
    container: str, l6: tuple[Dataset, Result]
) -> None:
    noted = WorkbookData(l6[0], l6[1], notes=NOTES)
    again = roundtrip(container, noted).data
    assert again is not None
    first = [t for t in build_tables(noted, PRESET)]
    assert build_tables(again, PRESET) == first


def test_whole_day_availability_survives_with_notes() -> None:
    from tts.core.model import Availability

    ds = to_dataset(parse_fet_groups_html(L6_HTML))[0]
    periods = [p.code for p in ds.time.periods]
    ds = ds.model_copy(
        update={
            "availability": tuple(
                Availability(resource="HAWE", day="Tue", period=p, status="unavailable")
                for p in periods
            )
        }
    )
    notes = {("Availability", "HAWE\x1fTue\x1f*\x1funavailable"): {"x_reason": "away"}}
    for container in CONTAINERS:
        outcome = roundtrip(container, WorkbookData(ds, notes=notes))
        assert outcome.data is not None
        assert outcome.data.dataset == ds
        assert dict(outcome.data.notes) == notes


PROPERTY = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


@PROPERTY
@given(academic_datasets(), st.sampled_from(sorted(CONTAINERS)))
def test_random_datasets_round_trip(dataset: Dataset, container: str) -> None:
    data = WorkbookData(dataset)
    outcome = roundtrip(container, data)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data == data
    assert outcome.data is not None
    assert build_tables(outcome.data, PRESET) == build_tables(data, PRESET)


@PROPERTY
@given(academic_datasets(), st.data())
def test_random_datasets_keep_their_notes(dataset: Dataset, data: st.DataObject) -> None:
    teachers = [r.code for r in dataset.resources if r.type == "Teacher"]
    picked = data.draw(st.lists(st.sampled_from(teachers), unique=True))
    text = st.text("abc 019", min_size=1, max_size=5).map(str.strip).filter(bool)
    notes = {("Teachers", t): {"x_a": data.draw(text)} for t in picked}
    container = data.draw(st.sampled_from(sorted(CONTAINERS)))
    outcome = roundtrip(container, WorkbookData(dataset, notes=notes))
    assert outcome.data is not None
    assert dict(outcome.data.notes) == notes
