"""L6 written as templates: a version 1 file whose template rows are expanded once on import
(P9.4, ADR-0007). The imported dataset holds the activities and no templates."""

from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from tts.core.model import Dataset
from tts.expand.templates import expand
from tts.io.workbook import import_xlsx
from tts.presets import expansion_options
from tts.presets.academic_weekly import types

WORKBOOK = Path(__file__).parent / "templates.xlsx"


@pytest.fixture(scope="module")
def imported() -> Dataset:
    outcome = import_xlsx(WORKBOOK)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data is not None
    return outcome.data.dataset


def test_the_workbook_is_what_the_script_writes(l6_dataset: Dataset, imported: Dataset) -> None:
    from make_templates import as_templates  # type: ignore[import-not-found]

    templated = as_templates(l6_dataset)
    made = expand(templated, **expansion_options(templated.preset)).dataset  # type: ignore[arg-type]
    cleaned = made.model_copy(
        update={
            "templates": (),
            "events": tuple(e.model_copy(update={"template": None}) for e in made.events),
        }
    )
    assert cleaned == imported


def test_the_import_keeps_activities_and_no_templates(imported: Dataset) -> None:
    assert imported.templates == () and imported.events
    assert all(e.template is None for e in imported.events)
    assert imported.kind == "hand_made"


def test_the_import_covers_each_module_like_the_fixture(
    imported: Dataset, l6_expected: dict[str, Any]
) -> None:
    ds = imported
    kinds = {r.code: r.type for r in ds.resources}
    groups: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for event in ds.events:
        counts[str(event.reference)][event.kind] += 1
    for f in ds.fixed:
        event = next(e for e in ds.events if e.code == f.event)
        if kinds[f.resource] == types.STUDENT_GROUP:
            groups[str(event.reference)].add(f.resource)
    expected = l6_expected["modules"]
    assert set(counts) == set(expected)
    for module, figures in expected.items():
        assert set(figures["groups"]) == groups[module], module
        assert counts[module].get("LEC", 0) == figures["LEC"], module
        assert counts[module].get("TUT", 0) == figures["TUT"], module
        assert sum(counts[module].values()) == figures["events"], module
    assert len(ds.events) == l6_expected["counts"]["events"]


def test_the_online_lecture_stays_online(imported: Dataset) -> None:
    assert len([e for e in imported.events if e.delivery == "online"]) == 1


def test_the_imported_timetable_solves(imported: Dataset) -> None:
    from tts.core.run import RunParams
    from tts.core.verifier import hard_violations, verify
    from tts.solver.solve import solve

    outcome = solve(imported, RunParams(time_limit_s=30, num_workers=4, seed=0))
    assert outcome.result is not None
    assert hard_violations(verify(imported, outcome.result)) == []
