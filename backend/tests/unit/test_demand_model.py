"""The demand concept in the core model (ADR-0007, spec 02 section 1 and invariants 6 and 7)."""

import pytest
from pydantic import ValidationError

from fixtures import demand, ev, make_dataset, res
from tts.core.model import Dataset, Event, ModelIssue, PooledSpec, Template


def kinds(issues: list[ModelIssue]) -> list[str]:
    return sorted(i.kind for i in issues)


GROUPS = tuple(res(f"g{i}", "G", capacity=10) for i in (1, 2, 3))


def configured(*demands, events=(), fixed=(), resources=GROUPS, **more) -> Dataset:  # type: ignore[no-untyped-def]
    resources = (*resources, res("r1", "R", capacity=40), res("n1", "N"))
    return make_dataset(
        resources=resources, events=events, fixed=fixed, demands=demands, validate=False, **more
    )


def test_a_configured_dataset_with_one_demand_is_sound() -> None:
    assert configured(demand()).validate_invariants() == []


def test_demands_are_sorted_by_code() -> None:
    ds = configured(demand("d2"), demand("d1"))
    assert [d.code for d in ds.demands] == ["d1", "d2"]


def test_participants_are_sorted() -> None:
    assert demand(participants=("g3", "g1", "g2")).participants == ("g1", "g2", "g3")


def test_the_same_participant_twice_is_refused() -> None:
    with pytest.raises(ValidationError):
        demand(participants=("g1", "g1"))


@pytest.mark.parametrize("bad", [0, -1])
def test_max_participants_must_be_at_least_one(bad: int) -> None:
    with pytest.raises(ValidationError):
        demand(limit=bad)


@pytest.mark.parametrize("bad", [0, -2])
def test_repeat_must_be_at_least_one(bad: int) -> None:
    with pytest.raises(ValidationError):
        demand(repeat=bad)


@pytest.mark.parametrize(
    ("count", "limit", "blocks"),
    [(10, 3, 4), (9, 3, 3), (1, 3, 1), (30, 1, 30), (7, None, 1), (0, 3, 0), (0, None, 0)],
)
def test_the_block_count_is_the_participants_over_the_limit_rounded_up(
    count: int, limit: int | None, blocks: int
) -> None:
    d = demand(participants=tuple(f"g{i:02d}" for i in range(count)), limit=limit)
    assert d.blocks == blocks


def test_a_participant_that_does_not_exist_is_reported() -> None:
    issues = configured(demand(participants=("g1", "nope"))).validate_invariants()
    assert kinds(issues) == ["unknown_reference"]
    assert issues[0].table == "demand"


def test_a_participant_that_is_not_exclusive_is_reported() -> None:
    issues = configured(demand(participants=("g1", "n1"))).validate_invariants()
    assert "demand_participant_not_exclusive" in kinds(issues)


def test_participants_of_different_types_are_reported() -> None:
    issues = configured(demand(participants=("g1", "r1"))).validate_invariants()
    assert "demand_mixed_participants" in kinds(issues)


def test_an_unknown_start_pattern_is_reported() -> None:
    assert kinds(configured(demand(pattern="nope")).validate_invariants()) == ["unknown_reference"]


def test_an_unknown_reference_is_reported() -> None:
    bad = demand().model_copy(update={"reference": "nope"})
    assert kinds(configured(bad).validate_invariants()) == ["unknown_reference"]


def test_a_pooled_spec_of_a_non_exclusive_type_is_reported() -> None:
    bad = demand(pooled=(PooledSpec(resource_type="N"),))
    assert kinds(configured(bad).validate_invariants()) == ["pooled_not_exclusive"]


def test_duplicate_demand_codes_are_reported() -> None:
    assert kinds(configured(demand(), demand()).validate_invariants()) == ["duplicate_code"]


def edit(code: str = "e1", demand_code: str = "d1") -> Event:
    return Event(code=code, kind="K", duration=1, start_pattern="all", demand=demand_code)


def test_an_event_of_an_unknown_demand_is_reported() -> None:
    issues = configured(demand(), events=(edit(demand_code="nope"),)).validate_invariants()
    assert "unknown_reference" in kinds(issues)


def test_an_edit_may_fix_participants_of_its_demand() -> None:
    ds = configured(demand(), events=(edit(),), fixed=(("e1", "g1"),))
    assert ds.validate_invariants() == []


def test_an_edit_may_not_fix_a_resource_outside_the_demand_of_the_participants_type() -> None:
    outsider = (*GROUPS, res("g9", "G", capacity=10))
    ds = configured(
        demand(), events=(edit(),), fixed=(("e1", "g1"), ("e1", "g9")), resources=outsider
    )
    assert kinds(ds.validate_invariants()) == ["edit_outside_demand"]


def test_an_edit_may_fix_resources_of_other_types() -> None:
    """A fixed resource of another type (a teacher, say) is fine; only participants are checked."""
    extra = (*GROUPS, res("t1", "T"))
    ds = configured(demand(), events=(edit(),), fixed=(("e1", "g1"), ("e1", "t1")), resources=extra)
    assert ds.validate_invariants() == []


def test_an_edit_larger_than_the_limit_is_reported() -> None:
    ds = configured(
        demand(limit=2),
        events=(edit(),),
        fixed=(("e1", "g1"), ("e1", "g2"), ("e1", "g3")),
    )
    assert kinds(ds.validate_invariants()) == ["edit_too_large"]


def test_hand_made_events_and_demands_do_not_mix() -> None:
    ds = configured(demand(), events=(ev("loose"),))
    assert "mixed_dataset" in kinds(ds.validate_invariants())


def test_the_kind_of_a_dataset_follows_its_events() -> None:
    from fixtures import ev

    assert Dataset().kind == "configured"  # nothing typed by hand
    assert make_dataset(resources=GROUPS, events=(ev("e1"),)).kind == "hand_made"
    assert configured(demand()).kind == "configured"
    assert configured(demand(), events=(edit(),), fixed=(("e1", "g1"),)).kind == "configured"
    templated = Dataset(
        templates=(Template(code="t", kind="K", mode="joint", duration=1, start_pattern="all"),)
    )
    assert templated.kind == "hand_made"
