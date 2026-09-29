"""What every constraint module provides (backend/CLAUDE.md, spec 04).

Each type has a module `core/constraints/<type>.py` exposing:

- `Params`: a frozen Pydantic model for the constraint's parameters. Implicit constraints take
  none and use `NoParams`.
- `verify(dataset, result, context=None) -> list[Violation]`: every violation of every active
  instance of the type in `dataset`. The verifier passes one shared `context`. A standalone call
  builds its own.

Implicit constraints (spec 04 section 1) are always checked and also expose `CODE`, their
catalogue code (`H0` ... `H5`).
"""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from tts.core.constraints.context import VerifyContext
from tts.core.model import Dataset, Ref, Result, Violation


class NoParams(BaseModel):
    """Parameters of a constraint that has none."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ConstraintType(Protocol):
    @property
    def Params(self) -> type[BaseModel]: ...  # noqa: N802

    def verify(
        self, dataset: Dataset, result: Result, context: VerifyContext | None = None
    ) -> list[Violation]: ...


def hard(code: str, constraint_code: str, message: str, *refs: Ref) -> Violation:
    """A violation of an implicit (always hard) rule. Each counts as one unit of penalty."""
    return Violation(
        code=code,
        constraint_code=constraint_code,
        severity="hard",
        penalty=1,
        refs=refs,
        message=message,
    )


def event_ref(code: str) -> Ref:
    return Ref(kind="event", code=code)


def resource_ref(code: str) -> Ref:
    return Ref(kind="resource", code=code)
