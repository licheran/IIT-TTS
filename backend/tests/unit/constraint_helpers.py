"""Checks shared by the tests of every declared constraint type (spec 04 section 4)."""

from typing import Any

from tts.core.model import Constraint, Dataset, Ref, Result
from tts.core.run import RunParams
from tts.core.verifier import hard_violations, verify
from tts.solver.explain import explain
from tts.solver.solve import SolveOutcome, solve

ONE = RunParams(time_limit_s=30, num_workers=1, seed=0)


def rule(
    type_name: str,
    scope: str = "all",
    hard: bool = False,
    weight: int = 1,
    code: str = "C",
    **params: Any,
) -> Constraint:
    return Constraint(
        code=code, type=type_name, scope=scope, params=params, hard=hard, weight=weight
    )


def penalty(dataset: Dataset, result: Result, code: str = "C") -> int:
    """The verifier's penalty for one constraint instance."""
    found = [v for v in verify(dataset, result) if v.constraint_code == code]
    assert all(v.code != "invalid_constraint" for v in found), found
    return sum(v.penalty for v in found)


def solve_and_compare(dataset: Dataset, code: str = "C") -> tuple[SolveOutcome, int]:
    """Solve to optimality and check the solver's term equals the verifier's penalty.

    Returns the outcome and the penalty.
    """
    outcome = solve(dataset, ONE)
    assert outcome.status == "optimal", outcome
    assert outcome.result is not None
    assert hard_violations(verify(dataset, outcome.result)) == []
    verified = penalty(dataset, outcome.result, code)
    assert outcome.penalties.get(code, 0) == verified
    return outcome, verified


def assert_infeasible_and_named(dataset: Dataset, code: str = "C") -> None:
    """The hard version is infeasible and the explanation names this instance."""
    outcome = solve(dataset, ONE)
    assert outcome.status == "infeasible", outcome.status
    diagnostic = explain(dataset)
    assert diagnostic is not None
    assert Ref(kind="constraint", code=code) in diagnostic.refs, diagnostic
