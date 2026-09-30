"""C11 `preferred_times` (spec 04 section 2)."""

from constraint_helpers import assert_infeasible_and_named, penalty, rule, solve_and_compare

from fixtures import at, ev, make_dataset, make_result, res
from tts.preflight.checks import run_preflight


def dataset(scope: str = "code:e1,e2", slots=("d1:p1",), hard: bool = False):
    """e1 and e2 share t1, so only one of them can take the single preferred slot."""
    return make_dataset(
        days=2,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        constraints=[rule("preferred_times", scope, hard=hard, slots=list(slots))],
    )


def test_verify_accepts_an_event_at_a_preferred_time() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d2", "p2"))
    assert penalty(dataset("code:e1"), result) == 0


def test_verify_counts_the_event_elsewhere() -> None:
    result = make_result(at("e1", "d1", "p1"), at("e2", "d1", "p2"))
    assert penalty(dataset(), result) == 1


def test_verify_counts_every_event_elsewhere() -> None:
    result = make_result(at("e1", "d2", "p1"), at("e2", "d1", "p2"))
    assert penalty(dataset(), result) == 2


def test_solver_uses_the_preferred_slots_it_can() -> None:
    _, found = solve_and_compare(dataset())
    assert found == 1


def test_solver_meets_every_preference_when_it_can() -> None:
    _, found = solve_and_compare(dataset(slots=("d1:p1", "d2:p2")))
    assert found == 0


def test_hard_preference_that_cannot_hold_is_infeasible_and_named() -> None:
    assert_infeasible_and_named(dataset(hard=True))


def test_preflight_reports_an_unknown_slot() -> None:
    issues = run_preflight(dataset(slots=("d1:p1", "d9:p1", "nonsense")))
    assert [i.kind for i in issues] == ["invalid_constraint", "invalid_constraint"]
