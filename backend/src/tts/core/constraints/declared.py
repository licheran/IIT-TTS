"""Shared helpers of the declared constraint types (spec 04 section 2).

Every declared module turns the active instances of its type into violations the same way:
parameters are validated with the module's `Params`, the scope is evaluated to the resources or
events it selects, and each violation is `hard` or `soft` as the instance says, with the penalty
`p` of spec 04. An instance whose parameters or scope are invalid is not checked: it gives one
`invalid_constraint` warning (pre-flight reports it as an error before any solve).
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ValidationError

from tts.core.constraints.catalogue import CATALOGUE
from tts.core.constraints.context import VerifyContext
from tts.core.model import Constraint, Dataset, Ref, Violation
from tts.core.selectors import SelectorError, Selectors, check_target
from tts.core.timegrid import TimeGrid, TimeGridError

INVALID = "invalid_constraint"


class InvalidConstraintError(ValueError):
    """A declared constraint whose parameters, scope or references are not valid."""

    def __init__(self, constraint: Constraint, problem: str) -> None:
        super().__init__(f'constraint "{constraint.code}" ({constraint.type}): {problem}')
        self.constraint = constraint
        self.problem = problem


@dataclass(frozen=True, slots=True)
class Instance[P: BaseModel]:
    """One active declared constraint, with its parameters and the targets its scope selects."""

    constraint: Constraint
    params: P
    targets: tuple[str, ...]  # resources or events, sorted by code

    @property
    def code(self) -> str:
        return self.constraint.code

    def violation(self, penalty: int, message: str, *refs: Ref) -> Violation:
        return Violation(
            code=self.constraint.type,
            constraint_code=self.constraint.code,
            severity="hard" if self.constraint.hard else "soft",
            penalty=penalty,
            refs=(Ref(kind="constraint", code=self.constraint.code), *refs),
            message=f"{self.constraint.code}: {message}",
        )


def parse_instance[P: BaseModel](
    dataset: Dataset,
    constraint: Constraint,
    params_model: type[P],
    selectors: Selectors | None = None,
) -> Instance[P]:
    """Validate one constraint. Raises `InvalidConstraintError` with a readable problem."""
    try:
        params = params_model.model_validate(constraint.params)
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "params"
        raise InvalidConstraintError(constraint, f"{where}: {first['msg']}") from None
    target = CATALOGUE.get(constraint.type, "event")
    selectors = selectors or Selectors(dataset)
    try:
        check_target(constraint.scope, target)
        selected = (
            selectors.resources(constraint.scope)
            if target == "resource"
            else selectors.events(constraint.scope)
        )
    except SelectorError as error:
        raise InvalidConstraintError(constraint, f"scope: {error}") from None
    return Instance(constraint, params, tuple(sorted(selected)))


def instances[P: BaseModel](
    ctx: VerifyContext, type_name: str, params_model: type[P]
) -> tuple[list[Instance[P]], list[Violation]]:
    """The valid active instances of a type, and a warning for each invalid one."""
    found: list[Instance[P]] = []
    warnings: list[Violation] = []
    for constraint in ctx.dataset.constraints:
        if not constraint.active or constraint.type != type_name:
            continue
        try:
            found.append(parse_instance(ctx.dataset, constraint, params_model, ctx.selectors))
        except InvalidConstraintError as error:
            warnings.append(
                Violation(
                    code=INVALID,
                    constraint_code=constraint.code,
                    severity="warning",
                    refs=(Ref(kind="constraint", code=constraint.code),),
                    message=f"{error}; it was not checked",
                )
            )
    return found, warnings


def parse_slot(grid: TimeGrid, text: str) -> int:
    """A `Day:Period` slot (C11). Raises `ValueError` for a malformed or unknown slot."""
    day, sep, period = text.partition(":")
    if not sep:
        raise ValueError(f'slot "{text}" is not written as Day:Period')
    try:
        return grid.slot(day.strip(), period.strip())
    except TimeGridError:
        raise ValueError(f'slot "{text}" names an unknown day or period') from None


Target = Literal["resource", "event"]
