"""Phase 9 acceptance: L6 written as templates expands back to the fixture's structure (P9.4)."""

from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from tts.core.model import Dataset, Event, FixedRequirement
from tts.expand.templates import expand
from tts.io.workbook import import_xlsx
from tts.presets import expansion_options
from tts.presets.academic_weekly import types

WORKBOOK = Path(__file__).parent / "templates.xlsx"


@pytest.fixture(scope="module")
def templated() -> Dataset:
    outcome = import_xlsx(WORKBOOK)
    assert [e.format() for e in outcome.errors] == []
    assert outcome.data is not None
    dataset = outcome.data.dataset
    assert dataset.events == () and dataset.templates
    return dataset


def expanded(dataset: Dataset) -> Dataset:
    out = expand(dataset, **expansion_options(dataset.preset))  # type: ignore[arg-type]
    assert out.problems == ()
    return out.dataset


def test_the_workbook_is_what_the_script_writes(l6_dataset: Dataset, templated: Dataset) -> None:
    from make_templates import as_templates  # type: ignore[import-not-found]

    assert as_templates(l6_dataset) == templated


def test_expansion_covers_each_module_like_the_fixture(
    templated: Dataset, l6_expected: dict[str, Any]
) -> None:
    ds = expanded(templated)
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


def test_the_online_lecture_stays_online(templated: Dataset) -> None:
    online = [e for e in expanded(templated).events if e.delivery == "online"]
    assert len(online) == 1


def test_expanding_twice_changes_nothing(templated: Dataset) -> None:
    once = expanded(templated)
    again = expand(once, **expansion_options(once.preset))  # type: ignore[arg-type]
    assert again.dataset == once and again.diff.empty


def test_hand_made_activities_are_left_alone(templated: Dataset) -> None:
    extra = Event(code="EXTRA-01", kind="LEC", duration=2, start_pattern="2H")
    group = next(r.code for r in templated.resources if r.type == types.STUDENT_GROUP)
    with_extra = templated.model_copy(
        update={
            "events": (extra,),
            "fixed": (FixedRequirement(event="EXTRA-01", resource=group),),
        }
    )
    ds = expanded(with_extra)
    assert extra in ds.events
    assert FixedRequirement(event="EXTRA-01", resource=group) in ds.fixed


def test_the_expanded_timetable_solves(templated: Dataset) -> None:
    from tts.core.run import RunParams
    from tts.core.verifier import hard_violations, verify
    from tts.solver.solve import solve

    ds = expanded(templated)
    outcome = solve(ds, RunParams(time_limit_s=30, num_workers=4, seed=0))
    assert outcome.result is not None
    assert hard_violations(verify(ds, outcome.result)) == []
