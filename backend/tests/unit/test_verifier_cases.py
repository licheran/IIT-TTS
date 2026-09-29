"""One hand-made case per kind of violation, checked through the public `verify`.

Every case has a broken result that must yield exactly the listed violations (rule code and
refs, nothing else), and a corrected twin that must verify clean.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from fixtures import at, ev, make_dataset, make_result, pick, pool, res, unavailable
from tts.core.model import Dataset, Pin, Result
from tts.core.verifier import verify

Expected = list[tuple[str, list[tuple[str, str]]]]


@dataclass(frozen=True)
class Case:
    dataset: Dataset
    broken: Result
    fixed: Result
    expected: Expected


def clash_through_the_parent() -> Case:
    ds = make_dataset(
        resources=[res("top", "N"), res("c1", "G", "top"), res("c2", "G", "top")],
        events=[ev("whole"), ev("part")],
        fixed=[("whole", "top"), ("part", "c1")],
    )
    return Case(
        ds,
        broken=make_result(at("whole", "d1", "p1"), at("part", "d1", "p1")),
        fixed=make_result(at("whole", "d1", "p1"), at("part", "d1", "p2")),
        expected=[
            (
                "H1",
                [("resource", "c1"), ("event", "part"), ("event", "whole"), ("slot", "d1/p1")],
            )
        ],
    )


def pooled_double_booking() -> Case:
    ds = make_dataset(
        resources=[res("g1"), res("g2"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "g1"), ("e2", "g2")],
        pooled=[pool("e1"), pool("e2")],
    )
    return Case(
        ds,
        broken=make_result(
            at("e1", "d1", "p1", pick(0, "r1")), at("e2", "d1", "p1", pick(0, "r1"))
        ),
        fixed=make_result(at("e1", "d1", "p1", pick(0, "r1")), at("e2", "d1", "p1", pick(0, "r2"))),
        expected=[
            (
                "H1",
                [("resource", "r1"), ("event", "e1"), ("event", "e2"), ("slot", "d1/p1")],
            )
        ],
    )


def too_small_for_the_cohort() -> Case:
    ds = make_dataset(
        resources=[
            res("g1", capacity=30),
            res("g2", capacity=30),
            res("small", "R", capacity=59),
            res("big", "R", capacity=60),
        ],
        events=[ev("e1")],
        fixed=[("e1", "g1"), ("e1", "g2")],
        pooled=[pool("e1", rule="sum_of_fixed:G")],
    )
    return Case(
        ds,
        broken=make_result(at("e1", "d1", "p1", pick(0, "small"))),
        fixed=make_result(at("e1", "d1", "p1", pick(0, "big"))),
        expected=[("H3", [("event", "e1"), ("resource", "small")])],
    )


def resource_fails_the_filter() -> Case:
    ds = make_dataset(
        resources=[res("g1"), res("lab", "R", kind="lab"), res("hall", "R", kind="hall")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1", filter="tag:kind=lab")],
    )
    return Case(
        ds,
        broken=make_result(at("e1", "d1", "p1", pick(0, "hall"))),
        fixed=make_result(at("e1", "d1", "p1", pick(0, "lab"))),
        expected=[("H4", [("event", "e1"), ("resource", "hall")])],
    )


def resource_is_unavailable() -> Case:
    ds = make_dataset(
        resources=[res("g1")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        availability=[unavailable("g1", "d1", "p2")],
    )
    return Case(
        ds,
        broken=make_result(at("e1", "d1", "p2")),
        fixed=make_result(at("e1", "d1", "p3")),
        expected=[("H2", [("event", "e1"), ("resource", "g1"), ("slot", "d1/p2")])],
    )


def pin_is_ignored() -> Case:
    ds = make_dataset(
        resources=[res("g1"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1")],
        pins=[Pin(event="e1", day="d2", start_period="p3", resources=("r2",))],
    )
    return Case(
        ds,
        broken=make_result(at("e1", "d2", "p3", pick(0, "r1"))),
        fixed=make_result(at("e1", "d2", "p3", pick(0, "r2"))),
        expected=[("H5", [("event", "e1"), ("resource", "r2")])],
    )


def start_not_allowed() -> Case:
    ds = make_dataset(resources=[res("g1")], events=[ev("e1", duration=2)], fixed=[("e1", "g1")])
    return Case(
        ds,
        broken=make_result(at("e1", "d1", "p4")),
        fixed=make_result(at("e1", "d1", "p3")),
        expected=[("H0", [("event", "e1"), ("slot", "d1/p4")])],
    )


def start_covers_a_break() -> Case:
    ds = make_dataset(
        resources=[res("g1")], events=[ev("e1", duration=2)], fixed=[("e1", "g1")], breaks=[3]
    )
    return Case(
        ds,
        broken=make_result(at("e1", "d1", "p2")),
        fixed=make_result(at("e1", "d1", "p1")),
        expected=[("H0", [("event", "e1"), ("slot", "d1/p2")])],
    )


def event_not_placed() -> Case:
    ds = make_dataset(resources=[res("g1")], events=[ev("e1")], fixed=[("e1", "g1")])
    return Case(
        ds,
        broken=make_result(),
        fixed=make_result(at("e1", "d1", "p1")),
        expected=[("H0", [("event", "e1")])],
    )


def pooled_resource_missing() -> Case:
    ds = make_dataset(
        resources=[res("g1"), res("r1", "R")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1")],
    )
    return Case(
        ds,
        broken=make_result(at("e1", "d1", "p1")),
        fixed=make_result(at("e1", "d1", "p1", pick(0, "r1"))),
        expected=[("H0", [("event", "e1")])],
    )


CASES: dict[str, Callable[[], Case]] = {
    "clash_through_the_parent": clash_through_the_parent,
    "pooled_double_booking": pooled_double_booking,
    "too_small_for_the_cohort": too_small_for_the_cohort,
    "resource_fails_the_filter": resource_fails_the_filter,
    "resource_is_unavailable": resource_is_unavailable,
    "pin_is_ignored": pin_is_ignored,
    "start_not_allowed": start_not_allowed,
    "start_covers_a_break": start_covers_a_break,
    "event_not_placed": event_not_placed,
    "pooled_resource_missing": pooled_resource_missing,
}


@pytest.mark.parametrize("name", CASES)
def test_the_broken_result_yields_exactly_the_expected_violations(name: str) -> None:
    case = CASES[name]()
    found = [
        (v.constraint_code, [(r.kind, r.code) for r in v.refs])
        for v in verify(case.dataset, case.broken)
    ]
    assert found == case.expected


@pytest.mark.parametrize("name", CASES)
def test_the_corrected_result_has_no_violations(name: str) -> None:
    case = CASES[name]()
    assert verify(case.dataset, case.fixed) == []


def test_every_hard_rule_is_covered_by_a_case() -> None:
    covered = {code for build in CASES.values() for code, _ in build().expected}
    assert covered == {"H0", "H1", "H2", "H3", "H4", "H5"}
