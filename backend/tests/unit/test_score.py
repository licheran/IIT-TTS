"""The weighted score of a result (spec 04 section 0)."""

from constraint_helpers import rule

from fixtures import at, ev, make_dataset, make_result, res
from tts.core.model import Ref, Violation
from tts.core.score import score
from tts.core.verifier import verify


def v(code: str, penalty: int, severity: str = "soft") -> Violation:
    return Violation(code="x", constraint_code=code, severity=severity, penalty=penalty)  # type: ignore[arg-type]


def test_the_score_weights_each_soft_penalty() -> None:
    ds = make_dataset(
        constraints=[
            rule("max_days", code="A", weight=5, max=1),
            rule("max_days", code="B", weight=2, max=1),
        ]
    )
    result = score(ds, [v("A", 2), v("B", 3), v("A", 1)])
    assert result.total == 5 * 3 + 2 * 3
    assert result.breakdown["A"].model_dump() == {"penalty": 3, "weight": 5, "score": 15}


def test_hard_violations_and_warnings_do_not_count() -> None:
    ds = make_dataset(constraints=[rule("max_days", code="A", max=1)])
    assert score(ds, [v("A", 4, "hard"), v("H1", 1, "hard"), v("A", 0, "warning")]).total == 0
    assert score(ds, []).breakdown == {}


def test_the_score_of_a_real_result_comes_from_the_verifier() -> None:
    ds = make_dataset(
        days=2,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        constraints=[rule("max_days", "code:t1", code="DAYS", weight=4, max=1)],
    )
    result = make_result(at("e1", "d1", "p1"), at("e2", "d2", "p1"))
    found = score(ds, verify(ds, result))
    assert found.total == 4
    assert Ref(kind="constraint", code="DAYS") in verify(ds, result)[0].refs
