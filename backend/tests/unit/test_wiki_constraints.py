"""The constraints section of the wiki (`docs/wiki/constraints/`) matches the catalogue."""

import json
import re
import typing
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import BaseModel

from tts.core.constraints.catalogue import CATALOGUE
from tts.core.constraints.registry import DECLARED
from tts.core.hierarchy import Hierarchy
from tts.core.model import Constraint, Dataset, Day, Period, TimeModel
from tts.core.selectors import Selectors
from tts.core.selectors import parse as parse_selector
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx, import_xlsx
from tts.preflight.checks import run_preflight
from tts.presets import get_preset
from tts.presets.academic_weekly.defaults import default_constraints as academic_defaults
from tts.presets.exams import types as exam_types
from tts.presets.exams.defaults import default_constraints as exams_defaults

ROOT = Path(__file__).resolve().parents[3]
WIKI = ROOT / "docs" / "wiki" / "constraints"
L6 = ROOT / "backend" / "tests" / "fixtures" / "l6" / "l6.xlsx"


def page_of(name: str) -> str:
    return (WIKI / f"{name}.md").read_text("utf-8")


def parameter_rows(text: str) -> dict[str, list[str]]:
    body = text[text.index("## Parameters") :].split("\n## ", 1)[0]
    rows = {}
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0].startswith("`"):
            rows[cells[0].strip("`")] = cells
    return rows


def type_word(annotation: object, metadata: list[object]) -> str:
    if typing.get_origin(annotation) is typing.Literal:
        return "one of " + ", ".join(f"`{a}`" for a in typing.get_args(annotation))
    if typing.get_origin(annotation) is list:
        return "list of text"
    if annotation is int:
        ge = next((m.ge for m in metadata if hasattr(m, "ge")), None)
        return "whole number" if ge is None else f"whole number ≥ {ge}"
    return "true/false" if annotation is bool else "text"


@pytest.mark.parametrize("name", list(CATALOGUE))
def test_every_constraint_type_has_a_page_that_matches_its_parameters(name: str) -> None:
    assert (WIKI / f"{name}.md").is_file(), f"no wiki page for {name}"
    text = page_of(name)
    assert f"`{name}`" in text.splitlines()[0]
    params: type[BaseModel] = DECLARED[name].Params  # type: ignore[assignment]
    fields = params.model_fields
    shown = parameter_rows(text)
    assert list(shown) == list(fields), f"{name}: parameters, in order"
    for pname, field in fields.items():
        cells = shown[pname]
        assert cells[2] == type_word(field.annotation, field.metadata), f"{name}.{pname}: type"
        assert cells[3] == ("yes" if field.is_required() else "no"), f"{name}.{pname}: required"
        assert cells[1] not in ("", "—"), f"{name}.{pname}: meaning"
    if not fields:
        assert "has no parameters" in text
    noun = "resources" if CATALOGUE[name] == "resource" else "activities"
    assert f"selects **{noun}" in text, f"{name}: scope kind"
    for heading in ("What it does", "How the penalty is counted", "Hard or soft?"):
        assert f"## {heading}" in text, f"{name}: {heading}"


def test_the_catalogue_overview_lists_every_type_once_in_order() -> None:
    text = (WIKI / "README.md").read_text("utf-8")
    links = re.findall(r"^\| \[`([a-z_]+)`\]\(([a-z_]+)\.md\) \|", text, re.M)
    assert set(DECLARED) == set(CATALOGUE)
    assert [a for a, _ in links] == list(CATALOGUE) == [b for _, b in links]


def test_the_defaults_page_lists_every_default_constraint() -> None:
    text = (WIKI / "defaults.md").read_text("utf-8")
    days = tuple(Day(code=c, label=c, order=i) for i, c in enumerate(("Mon", "Sat"), 1))
    periods = (Period(code="P01", start="09:00", end="10:00", order=1),)  # type: ignore[arg-type]
    time = TimeModel(days=days, periods=periods)
    for constraint in academic_defaults(time):
        assert f"`{constraint.code}`" in text, constraint.code
    example = Dataset(
        preset="exams",
        resource_types=get_preset("exams").resource_types,
        resources=(
            {"code": "BSC-1", "type": exam_types.COHORT, "capacity": 10},  # type: ignore[arg-type]
        ),
    )
    for constraint in exams_defaults(example):
        assert constraint.code.replace("BSC-1", "<cohort>") in text.replace("`", "")
    assert "AUTO-ORDER:" in text


def example_row(text: str) -> dict[str, typing.Any]:
    block = re.search(r"```json\n(.*?)\n```", text, re.S)
    assert block is not None
    return json.loads(block.group(1))  # type: ignore[no-any-return]


@pytest.fixture(scope="module")
def l6() -> Dataset:
    outcome = import_xlsx(L6)
    assert outcome.data is not None
    return outcome.data.dataset


@pytest.mark.parametrize("name", list(CATALOGUE))
def test_the_example_row_of_each_type_is_accepted_by_the_importer(name: str, l6: Dataset) -> None:
    row = example_row(page_of(name))
    assert row["type"] == name
    constraint = Constraint(**row)
    dataset = l6.model_copy(update={"constraints": (constraint,)})

    buffer = BytesIO()
    export_xlsx(WorkbookData(dataset), buffer, get_preset("academic_weekly"))
    outcome = import_xlsx(buffer.getvalue())
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data is not None and outcome.data.dataset.constraints == (constraint,)

    errors = [i for i in run_preflight(dataset) if i.severity == "error"]
    assert errors == [], [i.message for i in errors]


EVENT_CLAUSES = {"kind", "ref", "uses"}


def test_the_selector_examples_parse_and_the_l6_counts_are_right(l6: Dataset) -> None:
    text = (WIKI / "selectors.md").read_text("utf-8")
    selectors = Selectors(l6, Hierarchy(l6))
    checked = 0
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 3 or not cells[0].startswith("`") or cells[0] == "`all`":
            continue
        counted = re.match(r"^(\d+) ", cells[2])
        if counted is None:
            continue
        selector = cells[0][1:-1]
        parsed = parse_selector(selector)
        about_events = any(
            type(c).__name__.removesuffix("Clause").lower() in EVENT_CLAUSES for c in parsed.clauses
        )
        found = selectors.events(selector) if about_events else selectors.resources(selector)
        assert len(found) == int(counted.group(1)), selector
        checked += 1
    assert checked >= 12
