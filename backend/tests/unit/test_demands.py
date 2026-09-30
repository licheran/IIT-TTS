"""Created events in a result, and making them real (`core/demands.py`, ADR-0007)."""

import pytest
from pydantic import ValidationError

from fixtures import demand, ev, make_dataset, res
from tts.core.demands import block_sizes, realise, rejected_created
from tts.core.hierarchy import Hierarchy
from tts.core.model import CreatedEvent, Dataset, Result

GROUPS = tuple(res(f"g{i}", "G", capacity=10) for i in (1, 2, 3))


def configured(*demands, events=(), fixed=()) -> Dataset:  # type: ignore[no-untyped-def]
    return make_dataset(
        resources=(*GROUPS, res("r1", "R", capacity=40)),
        events=events,
        fixed=fixed,
        demands=demands or (demand(),),
    )


def result_of(*created: CreatedEvent) -> Result:
    return Result(created=created)


def made(code: str, *participants: str, of: str = "d1") -> CreatedEvent:
    return CreatedEvent(code=code, demand=of, participants=participants)


# --- The result type -------------------------------------------------------------------------


def test_created_events_are_sorted_by_code_and_their_participants_too() -> None:
    r = result_of(made("b", "g2", "g1"), made("a", "g3"))
    assert [c.code for c in r.created] == ["a", "b"]
    assert r.created[1].participants == ("g1", "g2")


def test_a_created_event_needs_participants_that_are_listed_once() -> None:
    with pytest.raises(ValidationError):
        made("a")
    with pytest.raises(ValidationError):
        made("a", "g1", "g1")


def test_a_result_with_created_events_survives_its_json() -> None:
    r = result_of(made("a", "g1", "g2"), made("b", "g3"))
    assert Result.model_validate_json(r.model_dump_json()) == r


def test_a_result_without_created_events_is_unchanged() -> None:
    assert Result().created == ()


# --- block sizes -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("count", "blocks", "sizes"),
    [(10, 4, (3, 3, 2, 2)), (9, 3, (3, 3, 3)), (7, 1, (7,)), (5, 5, (1, 1, 1, 1, 1)), (0, 0, ())],
)
def test_block_sizes_differ_by_at_most_one_larger_first(
    count: int, blocks: int, sizes: tuple[int, ...]
) -> None:
    assert block_sizes(count, blocks) == sizes


# --- realise ---------------------------------------------------------------------------------


def test_realising_adds_each_created_event_with_the_demands_properties() -> None:
    ds = configured(demand(duration=2, kind="TUT"))
    real = realise(ds, result_of(made("e1", "g1", "g2"), made("e2", "g3")))
    events = {e.code: e for e in real.events}
    assert set(events) == {"e1", "e2"}
    assert events["e1"].kind == "TUT"
    assert events["e1"].duration == 2
    assert events["e1"].demand == "d1"
    assert events["e1"].start_pattern == "all"


def test_realising_makes_the_participants_fixed_resources() -> None:
    real = realise(configured(), result_of(made("e1", "g1", "g2")))
    assert {(f.event, f.resource) for f in real.fixed} == {("e1", "g1"), ("e1", "g2")}


def test_realising_copies_the_demands_pooled_requirements() -> None:
    real = realise(configured(), result_of(made("e1", "g1"), made("e2", "g2")))
    assert [(q.event, q.resource_type, str(q.capacity_rule)) for q in real.pooled] == [
        ("e1", "R", "sum_of_fixed:G"),
        ("e2", "R", "sum_of_fixed:G"),
    ]


def test_a_realised_dataset_is_sound_and_keeps_its_declared_events() -> None:
    edit = ev("edit")
    edit = edit.model_copy(update={"demand": "d1"})
    ds = configured(events=(edit,), fixed=(("edit", "g1"),))
    real = realise(ds, result_of(made("e1", "g2", "g3")))
    assert real.validate_invariants() == []
    assert [e.code for e in real.events] == ["e1", "edit"]
    assert ("edit", "g1") in {(f.event, f.resource) for f in real.fixed}


def test_a_created_event_occupies_its_participants_and_their_descendants() -> None:
    parent = res("p", "G", capacity=10)
    kids = (res("k1", "G", parent="p", capacity=5), res("k2", "G", parent="p", capacity=5))
    ds = make_dataset(
        resources=(parent, *kids, res("r1", "R", capacity=40)),
        demands=(demand(participants=("p",), limit=None),),
    )
    real = realise(ds, result_of(made("e1", "p")))
    assert Hierarchy(real).occupied_exclusive("e1") == {"p", "k1", "k2"}


def test_realising_leaves_the_input_unchanged() -> None:
    ds = configured()
    realise(ds, result_of(made("e1", "g1")))
    assert ds.events == ()


# --- rejected created events -----------------------------------------------------------------


def test_a_created_event_of_an_unknown_demand_is_rejected_and_not_realised() -> None:
    ds = configured()
    r = result_of(made("e1", "g1", of="nope"))
    assert [(c.code, why) for c, why in rejected_created(ds, r)] == [
        ("e1", 'unknown demand "nope"')
    ]
    assert realise(ds, r).events == ()


def test_a_created_event_that_reuses_a_declared_code_is_rejected() -> None:
    edit = ev("e1").model_copy(update={"demand": "d1"})
    ds = configured(events=(edit,), fixed=(("e1", "g1"),))
    r = result_of(made("e1", "g2"))
    assert [why for _, why in rejected_created(ds, r)] == ['code "e1" is already an event']


def test_a_created_event_with_a_participant_outside_its_demand_is_rejected() -> None:
    ds = configured(demand(participants=("g1", "g2")))
    r = result_of(made("e1", "g1", "g3"))
    assert [why for _, why in rejected_created(ds, r)] == [
        'participant "g3" is not a participant of demand "d1"'
    ]


def test_a_sound_result_has_no_rejected_events() -> None:
    assert rejected_created(configured(), result_of(made("e1", "g1"), made("e2", "g2"))) == []


def test_a_created_code_used_twice_is_rejected_the_second_time() -> None:
    ds = configured()
    r = result_of(made("e1", "g1"), made("e1", "g2"))
    assert [c.participants for c, _ in rejected_created(ds, r)] == [("g2",)]
    assert [e.code for e in realise(ds, r).events] == ["e1"]
