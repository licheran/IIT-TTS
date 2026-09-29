"""The independent verifier (spec 05 section 6).

Checks any result against a dataset: the implicit rules H0 to H5, then every active declared
constraint whose type has a registered implementation. It never imports the solver, so it can
judge a solver's output, a hand-made timetable or an imported one (FR-14).
"""

from collections.abc import Iterable

from tts.core.constraints.context import VerifyContext
from tts.core.constraints.registry import declared_type, implicit_types
from tts.core.model import Dataset, Ref, Result, Violation

UNSUPPORTED = "unsupported_constraint"


def verify(dataset: Dataset, result: Result) -> list[Violation]:
    """Every violation, in a deterministic order: implicit rules H0 to H5, then declared types.

    A declared constraint whose type has no verifier yet gives one warning and is not checked.
    Inactive constraints are ignored.
    """
    context = VerifyContext(dataset, result)
    found: list[Violation] = []
    for implicit in implicit_types():
        found.extend(implicit.verify(dataset, result, context))

    checked: set[str] = set()
    for constraint in dataset.constraints:  # sorted by code
        if not constraint.active:
            continue
        implementation = declared_type(constraint.type)
        if implementation is None:
            found.append(
                Violation(
                    code=UNSUPPORTED,
                    constraint_code=constraint.code,
                    severity="warning",
                    refs=(Ref(kind="constraint", code=constraint.code),),
                    message=f'constraint "{constraint.code}": type "{constraint.type}" is not'
                    " checked by the verifier",
                )
            )
        elif constraint.type not in checked:
            checked.add(constraint.type)
            found.extend(implementation.verify(dataset, result, context))
    return found


def hard_violations(violations: Iterable[Violation]) -> list[Violation]:
    """The violations that make a result invalid."""
    return [v for v in violations if v.severity == "hard"]
