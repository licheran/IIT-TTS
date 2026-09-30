"""Default soft constraints of the exams preset: spread each cohort's exams over the days."""

from tts.core.model import Constraint, Dataset
from tts.presets.exams import types

SPREAD_DAYS = 2  # at least one free day between two exams of a cohort
SPREAD_WEIGHT = 1


def default_constraints(dataset: Dataset) -> tuple[Constraint, ...]:
    cohorts = [r.code for r in dataset.resources if r.type == types.COHORT]
    return tuple(
        Constraint(
            code=f"EX-SPREAD-{cohort}",
            type="min_days_between",
            scope=f'uses:(code:"{cohort}")',
            params={"min": SPREAD_DAYS},
            hard=False,
            weight=SPREAD_WEIGHT,
        )
        for cohort in cohorts
    )


def with_defaults(dataset: Dataset) -> Dataset:
    taken = {c.code for c in dataset.constraints}
    extra = [c for c in default_constraints(dataset) if c.code not in taken]
    merged = tuple(sorted((*dataset.constraints, *extra), key=lambda c: c.code))
    return dataset.model_copy(update={"constraints": merged})
