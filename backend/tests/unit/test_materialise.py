"""Making demands concrete for the solver (`core/demands.py`: `materialise`, `complete_edits`)."""

from fixtures import demand, ev, make_dataset, res
from tts.core.demands import complete_edits, materialise, participant_size
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Event

GROUPS = tuple(res(f"g{i}", "G", capacity=10 * i) for i in (1, 2, 3, 4, 5))


def configured(*demands, events=(), fixed=()) -> Dataset:  # type: ignore[no-untyped-def]
    return make_dataset(
        resources=(*GROUPS, res("r1", "R", capacity=100)),
        events=events,
        fixed=fixed,
        demands=demands,
        validate=False,
    )


def edit(code: str, demand_code: str = "d1") -> Event:
    return ev(code).model_copy(update={"demand": demand_code})


def fixed_of(ds: Dataset, event: str) -> tuple[str, ...]:
    return tuple(sorted(f.resource for f in ds.fixed if f.event == event))


def test_a_dataset_without_demands_is_returned_unchanged() -> None:
    ds = make_dataset(resources=GROUPS, events=(ev("e1"),))
    m = materialise(ds)
    assert m.dataset is ds
    assert m.blocks == ()
    assert m.problems == ()


def test_a_demand_with_no_participants_makes_nothing() -> None:
    m = materialise(configured(demand(participants=())))
    assert m.dataset.events == ()
    assert m.blocks == ()


def test_free_blocks_get_placeholder_events_with_no_fixed_participants() -> None:
    m = materialise(configured(demand(participants=("g1", "g2", "g3"), limit=2)))
    assert [b.fixed for b in m.blocks] == [None, None]  # 3 participants, limit 2: two blocks
    assert m.free == {"d1": ("g1", "g2", "g3")}
    assert m.bounds == {"d1": (1, 2)}
    assert len(m.dataset.events) == 2
    assert all(e.demand == "d1" for e in m.dataset.events)
    assert m.dataset.fixed == ()
    assert len(m.dataset.pooled) == 2  # the demand's room requirement, once per event


def test_each_block_has_repeat_events() -> None:
    m = materialise(configured(demand(participants=("g1", "g2", "g3"), limit=2, repeat=3)))
    assert [len(b.events) for b in m.blocks] == [3, 3]
    assert len(m.dataset.events) == 6
    assert sorted(e for b in m.blocks for e in b.events) == sorted(e.code for e in m.dataset.events)


def test_one_block_for_everyone_is_constant() -> None:
    m = materialise(configured(demand(participants=("g1", "g2", "g3"), limit=None, repeat=2)))
    assert [b.fixed for b in m.blocks] == [("g1", "g2", "g3")]
    assert m.free == {}
    for e in m.dataset.events:
        assert fixed_of(m.dataset, e.code) == ("g1", "g2", "g3")


def test_blocks_of_one_participant_are_constant_one_per_participant() -> None:
    m = materialise(configured(demand(participants=("g1", "g2", "g3"), limit=1)))
    assert [b.fixed for b in m.blocks] == [("g1",), ("g2",), ("g3",)]
    assert m.free == {}


def test_an_edit_fixes_its_block_and_the_missing_repetition_is_made() -> None:
    d = demand(participants=("g1", "g2", "g3", "g4", "g5"), limit=2, repeat=2)
    ds = configured(d, events=(edit("kept"),), fixed=(("kept", "g1"), ("kept", "g2")))
    m = materialise(ds)
    assert m.problems == ()
    by_fixed = {b.fixed: b for b in m.blocks}
    edited = by_fixed[("g1", "g2")]
    assert "kept" in edited.events
    assert len(edited.events) == 2
    assert len(edited.made) == 1  # the solver creates the second repetition
    assert fixed_of(m.dataset, edited.made[0]) == ("g1", "g2")
    # 5 participants, limit 2: 3 blocks; two free ones share g3, g4, g5
    assert m.free == {"d1": ("g3", "g4", "g5")}
    assert sum(1 for b in m.blocks if b.fixed is None) == 2


def test_the_last_free_block_becomes_constant() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2)
    ds = configured(d, events=(edit("kept"),), fixed=(("kept", "g1"), ("kept", "g2")))
    m = materialise(ds)
    assert sorted(b.fixed for b in m.blocks) == [("g1", "g2"), ("g3",)]
    assert m.free == {}


def test_a_declared_event_of_a_demand_gets_the_demands_requirements() -> None:
    d = demand(participants=("g1", "g2"), limit=2)
    ds = configured(d, events=(edit("kept"),), fixed=(("kept", "g1"), ("kept", "g2")))
    assert [(q.event, q.resource_type) for q in complete_edits(ds).pooled] == [("kept", "R")]


def test_an_edit_that_already_has_requirements_keeps_them() -> None:
    from fixtures import pool

    d = demand(participants=("g1", "g2"), limit=2)
    ds = make_dataset(
        resources=(*GROUPS, res("r1", "R", capacity=100)),
        events=(edit("kept"),),
        fixed=(("kept", "g1"), ("kept", "g2")),
        pooled=(pool("kept", filter="code:r1"),),
        demands=(d,),
        validate=False,
    )
    assert [q.filter for q in complete_edits(ds).pooled] == ["code:r1"]


def test_an_edited_block_of_the_wrong_size_is_a_problem() -> None:
    d = demand(participants=("g1", "g2", "g3", "g4", "g5"), limit=2)  # 3 blocks of 1 or 2
    ds = configured(
        d, events=(edit("kept"),), fixed=(("kept", "g1"), ("kept", "g2"), ("kept", "g3"))
    )
    assert any("edited block" in p and "size" in p for p in materialise(ds).problems)


def test_a_participant_in_two_edited_blocks_is_a_problem() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2)
    ds = configured(
        d,
        events=(edit("a"), edit("b")),
        fixed=(("a", "g1"), ("a", "g2"), ("b", "g2"), ("b", "g3")),
    )
    assert any('"g2" is in two edited blocks' in p for p in materialise(ds).problems)


def test_more_edited_blocks_than_the_demand_needs_is_a_problem() -> None:
    d = demand(participants=("g1", "g2"), limit=2)  # one block
    ds = configured(d, events=(edit("a"), edit("b")), fixed=(("a", "g1"), ("b", "g2")))
    assert any("more than the 1" in p for p in materialise(ds).problems)


def test_an_edit_without_participants_is_a_problem() -> None:
    d = demand(participants=("g1", "g2"), limit=2)
    assert any(
        "has no participants" in p for p in materialise(configured(d, events=(edit("a"),))).problems
    )


def test_an_edited_block_with_too_many_events_is_a_problem() -> None:
    d = demand(participants=("g1", "g2"), limit=2, repeat=1)
    ds = configured(
        d, events=(edit("a"), edit("b")), fixed=(("a", "g1"), ("a", "g2"), ("b", "g1"), ("b", "g2"))
    )
    assert any("more than the 1 repetition" in p for p in materialise(ds).problems)


def test_internal_codes_do_not_clash_with_declared_events() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2)
    ds = configured(d, events=(edit("d1@0.0"),), fixed=(("d1@0.0", "g1"), ("d1@0.0", "g2")))
    codes = [e.code for e in materialise(ds).dataset.events]
    assert len(codes) == len(set(codes))


def test_participant_size_is_the_capacity_of_the_participant() -> None:
    ds = configured(demand())
    h = Hierarchy(ds)
    resources = {r.code: r for r in ds.resources}
    assert participant_size(h, resources, "g3", "G") == 30


def test_participant_size_of_a_grouping_node_is_the_sum_of_its_parts() -> None:
    parent = res("p", "N")
    kids = (res("k1", "G", parent="p", capacity=10), res("k2", "G", parent="p", capacity=20))
    ds = make_dataset(resources=(parent, *kids), validate=False)
    h = Hierarchy(ds)
    resources = {r.code: r for r in ds.resources}
    assert participant_size(h, resources, "p", "G") == 30
