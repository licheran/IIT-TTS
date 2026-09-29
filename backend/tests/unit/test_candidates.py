"""The resources that can ever serve a pooled requirement: type, filter and capacity."""

import pytest

from fixtures import ev, make_dataset, pool, res
from tts.core.candidates import Candidates
from tts.core.selectors import SelectorError


def dataset_with(*requirements, fixed=(("e1", "g1"), ("e1", "g2"))):  # type: ignore[no-untyped-def]
    return make_dataset(
        resources=[
            res("g1", capacity=20),
            res("g2", capacity=25),
            res("r3", "R", capacity=60, kind="a"),
            res("r1", "R", capacity=30, kind="a"),
            res("r2", "R", capacity=50, kind="b"),
            res("t1", "T"),
        ],
        events=[ev("e1")],
        fixed=fixed,
        pooled=requirements,
    )


def test_every_resource_of_the_type_is_a_candidate_when_nothing_restricts_it() -> None:
    ds = dataset_with(pool("e1"))
    found = Candidates(ds).of(ds.pooled[0])
    assert found.codes == ("r1", "r2", "r3")  # sorted by code, only type R
    assert found.needed == 0


def test_the_filter_narrows_the_candidates() -> None:
    ds = dataset_with(pool("e1", filter="tag:kind=a"))
    assert Candidates(ds).of(ds.pooled[0]).codes == ("r1", "r3")


def test_the_capacity_rule_sets_the_capacity_needed_and_drops_small_resources() -> None:
    ds = dataset_with(pool("e1", rule="sum_of_fixed:G"))  # 20 + 25 = 45
    found = Candidates(ds).of(ds.pooled[0])
    assert found.needed == 45
    assert found.codes == ("r2", "r3")  # r1 offers only 30


def test_a_resource_without_capacity_does_not_meet_a_capacity_rule() -> None:
    ds = make_dataset(
        resources=[res("g1", capacity=5), res("r1", "R"), res("r2", "R", capacity=5)],
        events=[ev("e1")],
        fixed=[("e1", "g1")],
        pooled=[pool("e1", rule="sum_of_fixed:G")],
    )
    assert Candidates(ds).of(ds.pooled[0]).codes == ("r2",)


def test_an_invalid_filter_raises_a_selector_error() -> None:
    ds = dataset_with(pool("e1", filter="nonsense:x"))
    with pytest.raises(SelectorError):
        Candidates(ds).of(ds.pooled[0])


def test_the_capacity_needed_is_available_even_when_the_filter_is_invalid() -> None:
    ds = dataset_with(pool("e1", filter="nonsense:x", rule="sum_of_fixed:G"))
    assert Candidates(ds).needed(ds.pooled[0]) == 45


def test_no_candidate_is_found_for_a_type_with_no_resources() -> None:
    ds = dataset_with(pool("e1", type="T", rule="none"))
    assert Candidates(ds).of(ds.pooled[0]).codes == ("t1",)
    ds = make_dataset(resources=[res("g1")], events=[ev("e1")], pooled=[pool("e1")])
    assert Candidates(ds).of(ds.pooled[0]).codes == ()
