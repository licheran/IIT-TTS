"""Explaining why a configured dataset has no timetable (spec 05 section 5, ADR-0007)."""

from constraint_helpers import ONE

from fixtures import demand, make_dataset, res, unavailable
from tts.core.model import Dataset
from tts.solver.explain import explain
from tts.solver.solve import solve


def groups(n: int) -> list:  # type: ignore[type-arg]
    return [res(f"g{i}", "G", capacity=10) for i in range(1, n + 1)]


def dataset(n: int, periods: int, days: int = 1, availability=(), room: int = 20, **kw) -> Dataset:  # type: ignore[no-untyped-def]
    gs = groups(n)
    return make_dataset(
        days=days,
        periods=periods,
        resources=[*gs, res("r1", "R", capacity=room)],
        demands=[demand(participants=[g.code for g in gs], **kw)],
        availability=availability,
        validate=False,
    )


def test_a_participant_with_too_many_sessions_is_named() -> None:
    ds = dataset(2, periods=4, limit=2, repeat=5)
    assert solve(ds, ONE).status == "infeasible"
    found = explain(ds)
    assert found is not None
    assert "5 events of 1 periods for g1" in found.message
    assert any(r.code == "g1" for r in found.refs)


def test_the_blocks_that_cannot_be_formed_are_named_with_their_demand() -> None:
    """g1, g2 and g3 can only meet in p1, so two blocks of two put two sessions in p1 and p2
    for the same single room: no split of the groups works."""
    only_p1 = [unavailable(g, "d1", p) for g in ("g1", "g2", "g3") for p in ("p2",)]
    ds = dataset(4, periods=2, limit=2, availability=only_p1)
    assert solve(ds, ONE).status == "infeasible"
    found = explain(ds)
    assert found is not None
    assert "d1" in found.message
    assert "block" in found.message


def test_an_edit_that_cannot_belong_to_a_valid_split_is_an_infeasible_reason() -> None:
    from fixtures import ev

    kept = ev("kept").model_copy(update={"demand": "d1"})
    gs = groups(5)
    ds = make_dataset(
        resources=[*gs, res("r1", "R", capacity=50)],
        events=[kept],
        fixed=[("kept", "g1"), ("kept", "g2"), ("kept", "g3")],
        demands=[demand(participants=[g.code for g in gs], limit=2)],
        validate=False,
    )
    outcome = solve(ds, ONE)
    assert outcome.status == "infeasible"
    assert any("edited block" in p for p in outcome.problems)


def test_a_feasible_configured_dataset_has_nothing_to_explain() -> None:
    assert explain(dataset(4, periods=4, days=2, limit=2)) is None
