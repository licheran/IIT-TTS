"""Hand-built cases for the implicit rules H0 to H5, each with the exact expected refs."""

from collections.abc import Callable

import pytest

from fixtures import (
    at,
    ev,
    make_dataset,
    make_result,
    pick,
    pool,
    res,
    unavailable,
)
from tts.core.constraints import (
    capacity,
    no_overlap,
    pin,
    placement,
    requirement_match,
)
from tts.core.constraints import (
    unavailable as unavailable_rule,
)
from tts.core.constraints.base import ConstraintType, NoParams
from tts.core.constraints.context import VerifyContext
from tts.core.constraints.registry import (
    DECLARED,
    IMPLICIT,
    declared_type,
    implicit_types,
)
from tts.core.model import Dataset, Pin, Result, Violation


def refs(violation: Violation) -> list[tuple[str, str]]:
    return [(r.kind, r.code) for r in violation.refs]


def only(violations: list[Violation]) -> Violation:
    assert len(violations) == 1, [v.message for v in violations]
    return violations[0]


# --- H0 placement ---------------------------------------------------------------------------


def simple() -> Dataset:
    return make_dataset(resources=[res("g1")], events=[ev("e1")], fixed=[("e1", "g1")])


def test_a_correct_placement_has_no_violations() -> None:
    ds = simple()
    assert placement.verify(ds, make_result(at("e1", "d1", "p1"))) == []


def test_an_unplaced_event_is_reported() -> None:
    v = only(placement.verify(simple(), make_result()))
    assert (v.code, v.constraint_code, v.severity) == ("placement", "H0", "hard")
    assert refs(v) == [("event", "e1")]
    assert "no assignment" in v.message


def test_an_assignment_for_an_unknown_event_is_reported() -> None:
    ds = simple()
    v = only(placement.verify(ds, make_result(at("e1", "d1", "p1"), at("ghost", "d1", "p1"))))
    assert refs(v) == [("event", "ghost")]


def test_two_assignments_for_one_event_are_reported() -> None:
    ds = simple()
    v = only(placement.verify(ds, make_result(at("e1", "d1", "p1"), at("e1", "d2", "p1"))))
    assert refs(v) == [("event", "e1")]
    assert "2 assignments" in v.message


@pytest.mark.parametrize(("day", "period", "what"), [("dX", "p1", "day"), ("d1", "pX", "period")])
def test_an_unknown_day_or_period_is_reported(day: str, period: str, what: str) -> None:
    v = only(placement.verify(simple(), make_result(at("e1", day, period))))
    assert f"unknown {what}" in v.message
    assert refs(v) == [("event", "e1")]


def test_a_start_that_crosses_the_end_of_the_day_is_reported() -> None:
    ds = make_dataset(resources=[res("g1")], events=[ev("e1", duration=2)], fixed=[("e1", "g1")])
    v = only(placement.verify(ds, make_result(at("e1", "d1", "p4"))))
    assert "not an allowed start" in v.message
    assert refs(v) == [("event", "e1"), ("slot", "d1/p4")]


def test_a_start_that_covers_a_break_is_reported() -> None:
    ds = make_dataset(
        resources=[res("g1")], events=[ev("e1", duration=2)], fixed=[("e1", "g1")], breaks=[3]
    )
    assert placement.verify(ds, make_result(at("e1", "d1", "p1"))) == []
    v = only(placement.verify(ds, make_result(at("e1", "d1", "p2"))))
    assert refs(v) == [("event", "e1"), ("slot", "d1/p2")]


def pooled_dataset(count: int = 1) -> Dataset:
    return make_dataset(
        resources=[res("g1"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1", count=count)],
    )


def test_a_correct_pooled_choice_has_no_violations() -> None:
    assert (
        placement.verify(pooled_dataset(), make_result(at("e1", "d1", "p1", pick(0, "r1")))) == []
    )
    assert (
        placement.verify(pooled_dataset(2), make_result(at("e1", "d1", "p1", pick(0, "r1", "r2"))))
        == []
    )


@pytest.mark.parametrize(
    ("count", "choice", "have"),
    [(1, (), 0), (1, ("r1", "r2"), 2), (2, ("r1",), 1)],
)
def test_the_wrong_number_of_pooled_resources_is_reported(
    count: int, choice: tuple[str, ...], have: int
) -> None:
    result = make_result(at("e1", "d1", "p1", pick(0, *choice)) if choice else at("e1", "d1", "p1"))
    v = only(placement.verify(pooled_dataset(count), result))
    assert f"needs {count} resource(s) but has {have}" in v.message
    assert refs(v) == [("event", "e1")]


def test_a_repeated_pooled_resource_is_reported() -> None:
    ds = pooled_dataset(2)
    result = make_result(at("e1", "d1", "p1", pick(0, "r1", "r1")))
    messages = [v.message for v in placement.verify(ds, result)]
    assert any("repeats a resource" in m for m in messages)
    assert any("needs 2 resource(s) but has 1" in m for m in messages)


def test_an_unknown_pooled_resource_is_reported() -> None:
    ds = pooled_dataset()
    v = only(placement.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "zz")))))
    assert refs(v) == [("event", "e1"), ("resource", "zz")]


def test_choices_for_an_unknown_or_repeated_requirement_are_reported() -> None:
    ds = pooled_dataset()
    unknown = placement.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "r1"), pick(5, "r2"))))
    assert "unknown requirement #5" in only(unknown).message
    twice = placement.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "r1"), pick(0, "r1"))))
    assert "chooses requirement #0 twice" in only(twice).message


# --- H1 no_overlap --------------------------------------------------------------------------


def test_two_events_on_one_resource_in_one_slot_clash() -> None:
    ds = make_dataset(
        resources=[res("g1")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "g1"), ("e2", "g1")],
    )
    v = only(no_overlap.verify(ds, make_result(at("e1", "d1", "p1"), at("e2", "d1", "p1"))))
    assert (v.code, v.constraint_code) == ("no_overlap", "H1")
    assert refs(v) == [("resource", "g1"), ("event", "e1"), ("event", "e2"), ("slot", "d1/p1")]


def test_back_to_back_events_do_not_clash() -> None:
    ds = make_dataset(
        resources=[res("g1")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "g1"), ("e2", "g1")],
    )
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"))
    assert no_overlap.verify(ds, result) == []
    assert no_overlap.verify(ds, make_result(at("e1", "d1", "p1"), at("e2", "d2", "p1"))) == []


def test_a_partial_overlap_lists_only_the_shared_slots() -> None:
    ds = make_dataset(
        resources=[res("g1")],
        events=[ev("e1", 2), ev("e2", 2)],
        fixed=[("e1", "g1"), ("e2", "g1")],
    )
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"))
    v = only(no_overlap.verify(ds, result))
    assert refs(v) == [("resource", "g1"), ("event", "e1"), ("event", "e2"), ("slot", "d1/p2")]
    full = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p1"))
    assert [r for r in refs(only(no_overlap.verify(ds, full))) if r[0] == "slot"] == [
        ("slot", "d1/p1"),
        ("slot", "d1/p2"),
    ]


def hierarchy_dataset() -> Dataset:
    return make_dataset(
        resources=[
            res("top", "N"),
            res("c1", "G", "top"),
            res("c2", "G", "top"),
            res("shared", "N"),
        ],
        events=[ev("whole"), ev("part1"), ev("part2")],
        fixed=[("whole", "top"), ("part1", "c1"), ("part2", "c2")],
    )


def test_an_event_on_a_parent_clashes_with_an_event_on_its_child() -> None:
    result = make_result(at("whole", "d1", "p1"), at("part1", "d1", "p1"), at("part2", "d2", "p1"))
    v = only(no_overlap.verify(hierarchy_dataset(), result))
    assert refs(v) == [
        ("resource", "c1"),
        ("event", "part1"),
        ("event", "whole"),
        ("slot", "d1/p1"),
    ]


def test_sibling_children_do_not_clash_through_their_parent() -> None:
    result = make_result(at("whole", "d2", "p1"), at("part1", "d1", "p1"), at("part2", "d1", "p1"))
    assert no_overlap.verify(hierarchy_dataset(), result) == []


def test_a_parent_event_clashes_on_every_shared_child() -> None:
    ds = make_dataset(
        resources=[res("top", "N"), res("c1", "G", "top"), res("c2", "G", "top")],
        events=[ev("a"), ev("b")],
        fixed=[("a", "top"), ("b", "top")],
    )
    found = no_overlap.verify(ds, make_result(at("a", "d1", "p1"), at("b", "d1", "p1")))
    assert [refs(v)[0] for v in found] == [("resource", "c1"), ("resource", "c2")]


def test_a_non_exclusive_resource_may_be_shared() -> None:
    ds = make_dataset(
        resources=[res("shared", "N")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "shared"), ("e2", "shared")],
    )
    assert no_overlap.verify(ds, make_result(at("e1", "d1", "p1"), at("e2", "d1", "p1"))) == []


def test_a_pooled_resource_cannot_be_double_booked() -> None:
    ds = make_dataset(
        resources=[res("g1"), res("g2"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "g1"), ("e2", "g2")],
        pooled=[pool("e1"), pool("e2")],
    )
    clash = make_result(at("e1", "d1", "p1", pick(0, "r1")), at("e2", "d1", "p1", pick(0, "r1")))
    assert refs(only(no_overlap.verify(ds, clash)))[0] == ("resource", "r1")
    apart = make_result(at("e1", "d1", "p1", pick(0, "r1")), at("e2", "d1", "p1", pick(0, "r2")))
    assert no_overlap.verify(ds, apart) == []


def test_three_events_in_one_slot_give_three_pairs() -> None:
    ds = make_dataset(
        resources=[res("g1")],
        events=[ev("a"), ev("b"), ev("c")],
        fixed=[("a", "g1"), ("b", "g1"), ("c", "g1")],
    )
    found = no_overlap.verify(
        ds, make_result(at("a", "d1", "p1"), at("b", "d1", "p1"), at("c", "d1", "p1"))
    )
    assert [tuple(r[1] for r in refs(v)[1:3]) for v in found] == [
        ("a", "b"),
        ("a", "c"),
        ("b", "c"),
    ]


def test_events_with_an_undecodable_start_are_left_to_the_placement_rule() -> None:
    ds = make_dataset(
        resources=[res("g1")], events=[ev("e1"), ev("e2")], fixed=[("e1", "g1"), ("e2", "g1")]
    )
    assert no_overlap.verify(ds, make_result(at("e1", "d1", "p1"), at("e2", "dX", "p1"))) == []


# --- H2 unavailable -------------------------------------------------------------------------


def unavailable_dataset(duration: int = 1) -> Dataset:
    return make_dataset(
        resources=[res("top", "N"), res("c1", "G", "top"), res("r1", "R")],
        events=[ev("e1", duration)],
        fixed=[("e1", "c1")],
        pooled=[pool("e1")],
        availability=[
            unavailable("c1", "d1", "p2"),
            unavailable("r1", "d2", "p1"),
            unavailable("c1", "d2", "p4", status="avoid"),
        ],
    )


def test_occupying_a_fixed_resource_while_unavailable_is_reported() -> None:
    result = make_result(at("e1", "d1", "p2", pick(0, "r1")))
    v = only(unavailable_rule.verify(unavailable_dataset(), result))
    assert (v.code, v.constraint_code) == ("unavailable", "H2")
    assert refs(v) == [("event", "e1"), ("resource", "c1"), ("slot", "d1/p2")]


def test_any_covered_slot_counts_not_only_the_start() -> None:
    result = make_result(at("e1", "d1", "p1", pick(0, "r1")))
    v = only(unavailable_rule.verify(unavailable_dataset(duration=2), result))
    assert refs(v)[-1] == ("slot", "d1/p2")


def test_a_chosen_pooled_resource_can_be_unavailable() -> None:
    result = make_result(at("e1", "d2", "p1", pick(0, "r1")))
    v = only(unavailable_rule.verify(unavailable_dataset(), result))
    assert refs(v) == [("event", "e1"), ("resource", "r1"), ("slot", "d2/p1")]


def test_unavailability_of_a_child_blocks_an_event_on_its_parent() -> None:
    ds = make_dataset(
        resources=[res("top", "N"), res("c1", "G", "top")],
        events=[ev("e1")],
        fixed=[("e1", "top")],
        availability=[unavailable("c1", "d1", "p1")],
    )
    v = only(unavailable_rule.verify(ds, make_result(at("e1", "d1", "p1"))))
    assert refs(v)[:2] == [("event", "e1"), ("resource", "c1")]


def test_avoid_status_is_not_a_hard_violation() -> None:
    result = make_result(at("e1", "d2", "p4", pick(0, "r1")))
    assert unavailable_rule.verify(unavailable_dataset(), result) == []


# --- H3 capacity ----------------------------------------------------------------------------


def capacity_dataset(room_capacity: int | None = 60, rule: str = "sum_of_fixed:G") -> Dataset:
    return make_dataset(
        resources=[
            res("top", "N"),
            res("c1", "G", "top", capacity=30),
            res("c2", "G", "top", capacity=30),
            res("c3", "G", "top", capacity=10),
            res("r1", "R", capacity=room_capacity),
        ],
        events=[ev("two"), ev("parent"), ev("dup")],
        fixed=[("two", "c1"), ("two", "c2"), ("parent", "top"), ("dup", "top"), ("dup", "c1")],
        pooled=[pool("two", rule=rule), pool("parent", rule=rule), pool("dup", rule=rule)],
    )


def test_capacity_equal_to_the_sum_of_fixed_resources_is_enough() -> None:
    result = make_result(at("two", "d1", "p1", pick(0, "r1")))
    assert [v for v in capacity.verify(capacity_dataset(60), result)] == []


def test_capacity_below_the_sum_is_reported() -> None:
    result = make_result(at("two", "d1", "p1", pick(0, "r1")))
    v = only(capacity.verify(capacity_dataset(59), result))
    assert (v.code, v.constraint_code) == ("capacity", "H3")
    assert refs(v) == [("event", "two"), ("resource", "r1")]
    assert "capacity 59" in v.message
    assert "needs 60" in v.message


def test_a_grouping_node_stands_for_its_exclusive_children() -> None:
    ds = capacity_dataset(70)
    assert capacity.verify(ds, make_result(at("parent", "d1", "p1", pick(0, "r1")))) == []
    short = capacity.verify(
        capacity_dataset(69), make_result(at("parent", "d1", "p1", pick(0, "r1")))
    )
    assert "needs 70" in only(short).message


def test_a_resource_reached_twice_is_counted_once() -> None:
    # "dup" is fixed on the parent and on one of its children: 30 + 30 + 10, not 100.
    result = make_result(at("dup", "d1", "p1", pick(0, "r1")))
    assert capacity.verify(capacity_dataset(70), result) == []


def test_a_missing_capacity_counts_as_zero() -> None:
    result = make_result(at("two", "d1", "p1", pick(0, "r1")))
    v = only(capacity.verify(capacity_dataset(None), result))
    assert "capacity 0" in v.message


def test_no_capacity_rule_means_no_check() -> None:
    result = make_result(at("two", "d1", "p1", pick(0, "r1")))
    assert capacity.verify(capacity_dataset(1, rule="none"), result) == []


def test_required_capacity_is_zero_without_fixed_resources_of_the_type() -> None:
    ds = make_dataset(
        resources=[res("t1", "T"), res("r1", "R", capacity=1)],
        events=[ev("e1")],
        fixed=[("e1", "t1")],
        pooled=[pool("e1", rule="sum_of_fixed:G")],
    )
    assert capacity.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "r1")))) == []


# --- H4 requirement_match -------------------------------------------------------------------


def match_dataset(filter_text: str = "tag:kind=lab") -> Dataset:
    return make_dataset(
        resources=[
            res("g1"),
            res("lab1", "R", kind="lab"),
            res("hall1", "R", kind="hall"),
            res("seat", "T", kind="lab"),
        ],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1", filter=filter_text)],
    )


def test_a_resource_of_the_right_type_matching_the_filter_is_accepted() -> None:
    assert (
        requirement_match.verify(
            match_dataset(), make_result(at("e1", "d1", "p1", pick(0, "lab1")))
        )
        == []
    )


def test_a_resource_failing_the_filter_is_reported() -> None:
    v = only(
        requirement_match.verify(
            match_dataset(), make_result(at("e1", "d1", "p1", pick(0, "hall1")))
        )
    )
    assert (v.code, v.constraint_code) == ("requirement_match", "H4")
    assert refs(v) == [("event", "e1"), ("resource", "hall1")]
    assert 'does not match filter "tag:kind=lab"' in v.message


def test_a_resource_of_the_wrong_type_is_reported_even_if_the_filter_matches() -> None:
    v = only(
        requirement_match.verify(
            match_dataset(), make_result(at("e1", "d1", "p1", pick(0, "seat")))
        )
    )
    assert 'is of type "T"' in v.message
    assert refs(v) == [("event", "e1"), ("resource", "seat")]


def test_an_invalid_filter_is_reported_once_per_requirement() -> None:
    ds = match_dataset("bogus:x")
    found = requirement_match.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "lab1"))))
    v = only(found)
    assert "is invalid" in v.message
    assert refs(v) == [("event", "e1")]


def test_filters_can_use_hierarchy_selectors() -> None:
    ds = make_dataset(
        resources=[res("g1"), res("bldg", "N"), res("r1", "R", "bldg"), res("r2", "R")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1", filter="under:bldg")],
    )
    assert requirement_match.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "r1")))) == []
    v = only(requirement_match.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "r2")))))
    assert refs(v) == [("event", "e1"), ("resource", "r2")]


# --- H5 pin ---------------------------------------------------------------------------------


def pin_dataset(the_pin: Pin) -> Dataset:
    return make_dataset(
        resources=[res("g1"), res("r1", "R"), res("r2", "R")],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1")],
        pins=[the_pin],
    )


def test_an_assignment_matching_its_pin_is_accepted() -> None:
    ds = pin_dataset(Pin(event="e1", day="d2", start_period="p3", resources=("r2",)))
    assert pin.verify(ds, make_result(at("e1", "d2", "p3", pick(0, "r2")))) == []


def test_only_the_fields_a_pin_sets_are_checked() -> None:
    ds = pin_dataset(Pin(event="e1", day="d2"))
    assert pin.verify(ds, make_result(at("e1", "d2", "p1", pick(0, "r1")))) == []


@pytest.mark.parametrize(
    ("assignment", "fragment"),
    [
        (at("e1", "d1", "p3", pick(0, "r2")), 'day is "d1", pinned to "d2"'),
        (at("e1", "d2", "p1", pick(0, "r2")), 'start is "p1", pinned to "p3"'),
        (at("e1", "d2", "p3", pick(0, "r1")), 'missing pinned "r2"'),
    ],
)
def test_a_deviation_from_the_pin_is_reported(assignment: object, fragment: str) -> None:
    ds = pin_dataset(Pin(event="e1", day="d2", start_period="p3", resources=("r2",)))
    v = only(pin.verify(ds, make_result(assignment)))  # type: ignore[arg-type]
    assert (v.code, v.constraint_code) == ("pin", "H5")
    assert fragment in v.message
    assert refs(v)[0] == ("event", "e1")


def test_every_deviation_of_one_pin_is_listed_together() -> None:
    ds = pin_dataset(Pin(event="e1", day="d2", start_period="p3", resources=("r2",), source="lock"))
    v = only(pin.verify(ds, make_result(at("e1", "d1", "p1", pick(0, "r1")))))
    assert "lock pin" in v.message
    assert v.message.count(";") == 2
    assert refs(v) == [("event", "e1"), ("resource", "r2")]


def test_an_unplaced_pinned_event_is_left_to_the_placement_rule() -> None:
    ds = pin_dataset(Pin(event="e1", day="d2"))
    assert pin.verify(ds, make_result()) == []


# --- Shared context and registry ------------------------------------------------------------


def test_a_shared_context_gives_the_same_answer_as_a_standalone_call() -> None:
    ds = hierarchy_dataset()
    result = make_result(at("whole", "d1", "p1"), at("part1", "d1", "p1"), at("part2", "d2", "p1"))
    ctx = VerifyContext(ds, result)
    assert no_overlap.verify(ds, result, ctx) == no_overlap.verify(ds, result)


def test_the_context_skips_events_it_cannot_decode() -> None:
    ds = simple()
    ctx = VerifyContext(ds, make_result(at("e1", "dX", "p1")))
    assert ctx.placements == {}
    assert VerifyContext(ds, make_result(at("e1", "d2", "p3"))).placements["e1"].slots == (6,)


def test_the_implicit_constraints_are_registered_in_catalogue_order() -> None:
    codes = [m.CODE for m in implicit_types()]  # type: ignore[attr-defined]
    assert codes == ["H0", "H1", "H2", "H3", "H4", "H5"]
    assert list(IMPLICIT) == [
        "placement",
        "no_overlap",
        "unavailable",
        "capacity",
        "requirement_match",
        "pin",
    ]


@pytest.mark.parametrize("module", list(IMPLICIT.values()))
def test_every_implicit_module_follows_the_module_convention(module: ConstraintType) -> None:
    assert module.Params is NoParams
    verify: Callable[..., list[Violation]] = module.verify
    empty = Dataset()
    assert verify(empty, Result()) == []


def test_no_declared_types_are_registered_yet() -> None:
    assert DECLARED == {}
    assert declared_type("max_days") is None
