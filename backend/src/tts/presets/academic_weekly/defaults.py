"""The academic preset's default soft constraints (spec 04 section 3). Data, not logic.

`AC-TRAVEL` is included but inactive: the institute needs no free period for a change of building
(answered on 2026-09-30), and it can be switched on in the Constraints sheet. `AC-SAT` lists every
non-Saturday start slot, so it exists only when the time model has a Saturday.
"""

from tts.core.model import Constraint, Dataset, TimeModel
from tts.presets.academic_weekly import types


def _is_saturday(code: str, label: str) -> bool:
    return code.lower().startswith("sat") or label.lower().startswith("sat")


def default_constraints(time: TimeModel) -> tuple[Constraint, ...]:
    found = [
        Constraint(
            code="AC-GAPS",
            type="max_gaps",
            scope=f"type:{types.STUDENT_GROUP}",
            params={"max": 2, "per": "day"},
            hard=False,
            weight=5,
        ),
        Constraint(
            code="AC-TGAPS",
            type="max_gaps",
            scope=f"type:{types.TEACHER}",
            params={"max": 3, "per": "day"},
            hard=False,
            weight=2,
        ),
        Constraint(
            code="AC-TRAVEL",
            type="travel_gap",
            scope=f"type:{types.STUDENT_GROUP}",
            params={"min_periods": 1, "level": types.BUILDING},
            hard=False,
            weight=10,
            active=False,
        ),
    ]
    weekdays = [d for d in time.days if not _is_saturday(d.code, d.label)]
    if weekdays and len(weekdays) < len(time.days):
        slots: list[str] = [
            f"{d.code}:{p.code}" for d in weekdays for p in time.periods if not p.is_break
        ]
        found.append(
            Constraint(
                code="AC-SAT",
                type="preferred_times",
                scope=f"kind:{types.LECTURE},{types.TUTORIAL}",
                params={"slots": list(slots)},
                hard=False,
                weight=3,
            )
        )
    return tuple(found)


def with_defaults(dataset: Dataset) -> Dataset:
    """The dataset plus every default whose code it does not already use."""
    taken = {c.code for c in dataset.constraints}
    extra = [c for c in default_constraints(dataset.time) if c.code not in taken]
    # `model_copy` skips the validators, so keep the canonical order (by code) by hand.
    merged = tuple(sorted((*dataset.constraints, *extra), key=lambda c: c.code))
    return dataset.model_copy(update={"constraints": merged})
