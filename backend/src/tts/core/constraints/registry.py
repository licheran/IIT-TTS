"""Registry of constraint modules, keyed by type name.

Implicit constraints (H0 ... H6) always run, in catalogue order. Declared types are added to
`DECLARED` as their modules are written (Phase 8), one line each. An explicit table, not module
scanning, so what the verifier supports is visible in one place.
"""

from tts.core.constraints import (
    avoid,
    capacity,
    consecutive,
    demand_cover,
    max_days,
    max_gaps,
    max_per_day,
    max_span,
    min_days_between,
    no_overlap,
    not_overlapping,
    order,
    pin,
    placement,
    preferred_resources,
    preferred_times,
    requirement_match,
    same_day,
    same_start,
    travel_gap,
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
    demand_cover.TYPE: demand_cover,
}

DECLARED: dict[str, ConstraintType] = {  # catalogue order (spec 04 section 2)
    max_per_day.TYPE: max_per_day,
    max_gaps.TYPE: max_gaps,
    max_days.TYPE: max_days,
    min_days_between.TYPE: min_days_between,
    same_start.TYPE: same_start,
    same_day.TYPE: same_day,
    order.TYPE: order,
    consecutive.TYPE: consecutive,
    not_overlapping.TYPE: not_overlapping,
    travel_gap.TYPE: travel_gap,
    preferred_times.TYPE: preferred_times,
    preferred_resources.TYPE: preferred_resources,
    avoid.TYPE: avoid,
    max_span.TYPE: max_span,
}


def implicit_types() -> list[ConstraintType]:
    """The implicit constraint modules in catalogue order (H0 first)."""
    return list(IMPLICIT.values())


def declared_type(type_name: str) -> ConstraintType | None:
    """The module implementing a declared constraint type, or None if there is none yet."""
    return DECLARED.get(type_name)
