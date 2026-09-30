"""Registry of constraint modules, keyed by type name.

Implicit constraints (H0 ... H5) always run, in catalogue order. Declared types are added to
`DECLARED` as their modules are written (Phase 8), one line each. An explicit table, not module
scanning, so what the verifier supports is visible in one place.
"""

from tts.core.constraints import (
    capacity,
    max_days,
    max_gaps,
    max_per_day,
    no_overlap,
    pin,
    placement,
    requirement_match,
    unavailable,
)
from tts.core.constraints.base import ConstraintType

IMPLICIT: dict[str, ConstraintType] = {
    placement.TYPE: placement,
    no_overlap.TYPE: no_overlap,
    unavailable.TYPE: unavailable,
    capacity.TYPE: capacity,
    requirement_match.TYPE: requirement_match,
    pin.TYPE: pin,
}

DECLARED: dict[str, ConstraintType] = {
    max_days.TYPE: max_days,
    max_gaps.TYPE: max_gaps,
    max_per_day.TYPE: max_per_day,
}


def implicit_types() -> list[ConstraintType]:
    """The implicit constraint modules in catalogue order (H0 first)."""
    return list(IMPLICIT.values())


def declared_type(type_name: str) -> ConstraintType | None:
    """The module implementing a declared constraint type, or None if there is none yet."""
    return DECLARED.get(type_name)
