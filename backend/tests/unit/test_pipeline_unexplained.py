"""An infeasible run always says something: a fallback message when no core was found."""

from constraint_helpers import rule

from fixtures import ev, make_dataset, res
from tts.core.run import RunParams
from tts.worker import pipeline


def impossible():
    return make_dataset(
        days=3,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "t1"), ("e2", "t1"), ("e3", "t1")],
        constraints=[rule("max_days", "code:t1", hard=True, max=1)],
        validate=False,
    )


def test_an_infeasible_run_names_the_conflicting_rules() -> None:
    outcome = pipeline.run_pipeline(impossible(), RunParams(time_limit_s=10, num_workers=1))
    assert outcome.status == "infeasible"
    kinds = [d.kind for d in outcome.diagnostics]
    assert "infeasible_core" in kinds and "infeasible_unexplained" not in kinds


def test_an_infeasible_run_whose_reason_was_not_found_says_so(monkeypatch) -> None:
    monkeypatch.setattr(pipeline, "explain", lambda dataset, label: None)
    outcome = pipeline.run_pipeline(impossible(), RunParams(time_limit_s=10, num_workers=1))
    assert outcome.status == "infeasible"
    found = [d for d in outcome.diagnostics if d.kind == "infeasible_unexplained"]
    assert len(found) == 1 and found[0].severity == "error"
    assert "hard constraints soft" in found[0].message
