from datetime import time

import pytest
from pydantic import ValidationError

from tts.core.model import (
    Assignment,
    Availability,
    CapacityRule,
    Constraint,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    ModelIssue,
    Period,
    Pin,
    PooledChoice,
    PooledRequirement,
    Ref,
    Resource,
    ResourceType,
    Result,
    StartPattern,
    TimeModel,
    Violation,
)


def sound_dataset() -> Dataset:
    """A small valid dataset in neutral vocabulary."""
    return Dataset(
        resource_types=(
            ResourceType(code="A", exclusive=True, has_capacity=True),
            ResourceType(code="B", exclusive=True, has_capacity=True),
            ResourceType(code="X", exclusive=False),
        ),
        resources=(
            Resource(code="x1", type="X"),
            Resource(code="a1", type="A", parent="x1", capacity=10),
            Resource(code="b1", type="B", capacity=20),
            Resource(code="b2", type="B", capacity=5),
        ),
        time=TimeModel(
            days=(Day(code="d1", order=1), Day(code="d2", order=2)),
            periods=(
                Period(code="p1", start=time(8, 0), end=time(9, 0), order=1),
                Period(code="p2", start=time(9, 0), end=time(10, 0), order=2),
                Period(code="p3", start=time(10, 0), end=time(11, 0), order=3, is_break=True),
            ),
            start_patterns=(StartPattern(code="s1", duration=1, start_periods=("p1", "p2")),),
        ),
        events=(Event(code="e1", kind="K", duration=1, start_pattern="s1"),),
        fixed=(FixedRequirement(event="e1", resource="a1"),),
        pooled=(
            PooledRequirement(
                event="e1",
                resource_type="B",
                capacity_rule=CapacityRule(kind="sum_of_fixed", resource_type="A"),
            ),
        ),
    )


def kinds(issues: list[ModelIssue]) -> list[str]:
    return sorted(i.kind for i in issues)


def test_sound_dataset_has_no_issues() -> None:
    assert sound_dataset().validate_invariants() == []


def test_datasets_built_in_different_orders_are_equal() -> None:
    a = sound_dataset()
    b = a.model_copy(update={})
    reordered = Dataset(
        resource_types=tuple(reversed(a.resource_types)),
        resources=tuple(reversed(a.resources)),
        time=TimeModel(
            days=tuple(reversed(a.time.days)),
            periods=tuple(reversed(a.time.periods)),
            start_patterns=a.time.start_patterns,
        ),
        events=a.events,
        fixed=a.fixed,
        pooled=a.pooled,
    )
    assert reordered == a == b
    assert reordered.model_dump_json() == a.model_dump_json()


def test_tags_and_attributes_are_normalised_to_sorted_pairs() -> None:
    r = Resource(code="r", type="A", tags={"z": "1", "a": "2"}, attributes={"n": 3, "flag": True})
    assert r.tags == (("a", "2"), ("z", "1"))
    assert r.attributes == (("flag", True), ("n", 3))
    assert r.tag("a") == "2"
    assert r.tag("missing") is None
    assert r.attribute("n") == 3


def test_models_are_frozen() -> None:
    event = Event(code="e", kind="K", duration=1, start_pattern="s")
    with pytest.raises(ValidationError):
        event.duration = 2  # type: ignore[misc]


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Event(code="e", kind="K", duration=1, start_pattern="s", colour="red")  # type: ignore[call-arg]


@pytest.mark.parametrize("duration", [0, -1])
def test_event_duration_must_be_at_least_one(duration: int) -> None:
    with pytest.raises(ValidationError):
        Event(code="e", kind="K", duration=duration, start_pattern="s")


def test_start_pattern_duration_must_be_at_least_one() -> None:
    with pytest.raises(ValidationError):
        StartPattern(code="s", duration=0, start_periods=("p1",))


def test_period_must_end_after_it_starts() -> None:
    with pytest.raises(ValidationError):
        Period(code="p", start=time(9, 0), end=time(9, 0), order=1)


def test_pooled_count_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        PooledRequirement(event="e", resource_type="B", count=0)


def test_negative_weight_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Constraint(code="c", type="max_days", weight=-1)


def test_periods_and_days_sort_by_order() -> None:
    tm = TimeModel(
        days=(Day(code="late", order=2), Day(code="early", order=1)),
        periods=(
            Period(code="b", start=time(9), end=time(10), order=2),
            Period(code="a", start=time(8), end=time(9), order=1),
        ),
    )
    assert [d.code for d in tm.days] == ["early", "late"]
    assert [p.code for p in tm.periods] == ["a", "b"]
    assert tm.periods_per_day == 2


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("", CapacityRule()),
        ("none", CapacityRule()),
        ("sum_of_fixed:A", CapacityRule(kind="sum_of_fixed", resource_type="A")),
        (" sum_of_fixed: Big Type ", CapacityRule(kind="sum_of_fixed", resource_type="Big Type")),
    ],
)
def test_capacity_rule_parses(text: str, rule: CapacityRule) -> None:
    assert CapacityRule.parse(text) == rule


def test_capacity_rule_round_trips_through_text() -> None:
    rule = CapacityRule(kind="sum_of_fixed", resource_type="A")
    assert CapacityRule.parse(str(rule)) == rule
    assert str(CapacityRule()) == "none"


def test_capacity_rule_rejects_unknown_text() -> None:
    with pytest.raises(ValueError, match="unknown capacity rule"):
        CapacityRule.parse("half_of_fixed:A")


def test_capacity_rule_requires_a_type_exactly_for_sum_of_fixed() -> None:
    with pytest.raises(ValidationError):
        CapacityRule(kind="sum_of_fixed")
    with pytest.raises(ValidationError):
        CapacityRule(kind="none", resource_type="A")


def test_result_and_pin_sort_their_members() -> None:
    result = Result(
        assignments=(
            Assignment(event="e2", day="d1", start_period="p1"),
            Assignment(
                event="e1",
                day="d1",
                start_period="p1",
                chosen=(
                    PooledChoice(ordinal=1, resources=("b2", "b1")),
                    PooledChoice(ordinal=0, resources=("b1",)),
                ),
            ),
        )
    )
    assert [a.event for a in result.assignments] == ["e1", "e2"]
    assert [c.ordinal for c in result.assignments[0].chosen] == [0, 1]
    assert result.assignments[0].chosen[1].resources == ("b1", "b2")
    assert Pin(event="e1", resources=("b2", "b1")).resources == ("b1", "b2")


def test_violation_defaults_and_refs() -> None:
    v = Violation(
        code="no_overlap",
        constraint_code="H1",
        severity="hard",
        refs=(Ref(kind="resource", code="a1"), Ref(kind="event", code="e1")),
    )
    assert v.penalty == 0
    assert v.message == ""
    with pytest.raises(ValidationError):
        Ref(kind="bogus", code="x")  # type: ignore[arg-type]


# --- Global invariants ---------------------------------------------------------------------------


def with_changes(**changes: object) -> Dataset:
    return sound_dataset().model_copy(update=changes)


def test_duplicate_codes_are_reported_per_table() -> None:
    ds = with_changes(
        resources=(*sound_dataset().resources, Resource(code="a1", type="A")),
        events=(
            *sound_dataset().events,
            Event(code="e1", kind="K", duration=1, start_pattern="s1"),
        ),
    )
    issues = ds.validate_invariants()
    assert kinds(issues) == ["duplicate_code", "duplicate_code"]
    assert {(i.table, i.key) for i in issues} == {("resource", "a1"), ("event", "e1")}


def test_unknown_references_are_all_reported() -> None:
    base = sound_dataset()
    ds = with_changes(
        resources=(*base.resources, Resource(code="c1", type="NOPE", parent="ghost")),
        events=(Event(code="e1", kind="K", duration=1, start_pattern="ghost", reference="ref"),),
        fixed=(
            FixedRequirement(event="e9", resource="a1"),
            FixedRequirement(event="e1", resource="zz"),
        ),
        availability=(Availability(resource="a1", day="dX", period="pX", status="unavailable"),),
        pins=(Pin(event="e1", day="dY", start_period="pY", resources=("qq",)),),
    )
    issues = ds.validate_invariants()
    messages = {i.message for i in issues}
    assert 'unknown resource type "NOPE"' in messages
    assert 'unknown parent "ghost"' in messages
    assert 'unknown start pattern "ghost"' in messages
    assert 'unknown reference "ref"' in messages
    assert 'unknown event "e9"' in messages
    assert 'unknown resource "zz"' in messages
    assert 'unknown day "dX"' in messages
    assert 'unknown period "pX"' in messages
    assert 'unknown day "dY"' in messages
    assert 'unknown period "pY"' in messages
    assert 'unknown resource "qq"' in messages
    assert all(i.kind == "unknown_reference" for i in issues)


def test_pooled_requirement_must_use_an_exclusive_type() -> None:
    ds = with_changes(pooled=(PooledRequirement(event="e1", resource_type="X"),))
    assert kinds(ds.validate_invariants()) == ["pooled_not_exclusive"]


def test_duplicate_pooled_ordinal_is_reported() -> None:
    ds = with_changes(
        pooled=(
            PooledRequirement(event="e1", resource_type="B"),
            PooledRequirement(event="e1", resource_type="B"),
        )
    )
    assert kinds(ds.validate_invariants()) == ["duplicate_code"]


def test_capacity_on_a_type_without_capacity_is_reported() -> None:
    ds = with_changes(
        resources=(*sound_dataset().resources, Resource(code="x2", type="X", capacity=3))
    )
    assert kinds(ds.validate_invariants()) == ["unexpected_capacity"]


def test_attributes_are_checked_against_the_type_schema() -> None:
    from tts.core.model import AttributeDef

    types = (
        ResourceType(
            code="A",
            exclusive=True,
            attribute_schema=(AttributeDef(name="size", kind="int"),),
        ),
    )
    ok = Dataset(
        resource_types=types, resources=(Resource(code="a", type="A", attributes={"size": 3}),)
    )
    assert ok.validate_invariants() == []
    bad = Dataset(
        resource_types=types,
        resources=(
            Resource(code="a", type="A", attributes={"size": "big"}),
            Resource(code="b", type="A", attributes={"colour": "red"}),
        ),
    )
    assert kinds(bad.validate_invariants()) == ["bad_attribute", "unknown_attribute"]
