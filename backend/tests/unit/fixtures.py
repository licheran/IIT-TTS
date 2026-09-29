"""Builders for small datasets in neutral vocabulary (no domain words).

Standard resource types, all named by a letter:

- `N`: not exclusive (a container, for example a grouping parent)
- `G`: exclusive, has capacity (a fixed resource, for example a cohort)
- `R`: exclusive, has capacity (a pooled resource)
- `T`: exclusive, no capacity

Standard time: days `d1..dN` and periods `p1..pM` of one hour, plus a start pattern `all`
allowing every period. Periods listed in `breaks` (1-based) are breaks.
"""

from collections.abc import Iterable, Sequence
from datetime import time

from tts.core.model import (
    Assignment,
    Availability,
    CapacityRule,
    Constraint,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    Pin,
    PooledChoice,
    PooledRequirement,
    Resource,
    ResourceType,
    Result,
    StartPattern,
    TimeModel,
)

STANDARD_TYPES = (
    ResourceType(code="N", exclusive=False),
    ResourceType(code="G", exclusive=True, has_capacity=True),
    ResourceType(code="R", exclusive=True, has_capacity=True),
    ResourceType(code="T", exclusive=True),
)


def make_time(
    days: int = 2,
    periods: int = 4,
    breaks: Iterable[int] = (),
    patterns: Sequence[StartPattern] | None = None,
) -> TimeModel:
    breaks = set(breaks)
    return TimeModel(
        days=tuple(Day(code=f"d{i}", order=i) for i in range(1, days + 1)),
        periods=tuple(
            Period(
                code=f"p{i}",
                start=time(7 + i, 0),
                end=time(8 + i, 0),
                order=i,
                is_break=i in breaks,
            )
            for i in range(1, periods + 1)
        ),
        start_patterns=tuple(patterns)
        if patterns is not None
        else (
            StartPattern(
                code="all",
                duration=1,
                start_periods=tuple(f"p{i}" for i in range(1, periods + 1)),
            ),
        ),
    )


def res(
    code: str,
    type: str = "G",  # noqa: A002
    parent: str | None = None,
    capacity: int | None = None,
    **tags: str,
) -> Resource:
    return Resource(code=code, type=type, parent=parent, capacity=capacity, tags=tags)


def ev(code: str, duration: int = 1, pattern: str = "all", kind: str = "K") -> Event:
    return Event(code=code, kind=kind, duration=duration, start_pattern=pattern)


def pool(
    event: str,
    type: str = "R",  # noqa: A002
    count: int = 1,
    filter: str = "all",  # noqa: A002
    rule: str = "none",
    ordinal: int = 0,
) -> PooledRequirement:
    return PooledRequirement(
        event=event,
        resource_type=type,
        count=count,
        filter=filter,
        capacity_rule=CapacityRule.parse(rule),
        ordinal=ordinal,
    )


def unavailable(resource: str, day: str, period: str, status: str = "unavailable") -> Availability:
    return Availability(resource=resource, day=day, period=period, status=status)  # type: ignore[arg-type]


def make_dataset(
    *,
    resources: Iterable[Resource] = (),
    events: Iterable[Event] = (),
    fixed: Iterable[tuple[str, str]] = (),
    pooled: Iterable[PooledRequirement] = (),
    availability: Iterable[Availability] = (),
    pins: Iterable[Pin] = (),
    constraints: Iterable[Constraint] = (),
    days: int = 2,
    periods: int = 4,
    breaks: Iterable[int] = (),
    patterns: Sequence[StartPattern] | None = None,
    validate: bool = True,
) -> Dataset:
    """A dataset with the standard types and time. `validate` asserts it has no invariant issues."""
    ds = Dataset(
        resource_types=STANDARD_TYPES,
        resources=tuple(resources),
        time=make_time(days, periods, breaks, patterns),
        events=tuple(events),
        fixed=tuple(FixedRequirement(event=e, resource=r) for e, r in fixed),
        pooled=tuple(pooled),
        availability=tuple(availability),
        pins=tuple(pins),
        constraints=tuple(constraints),
    )
    if validate:
        assert ds.validate_invariants() == []
    return ds


def pick(ordinal: int, *resources: str) -> PooledChoice:
    return PooledChoice(ordinal=ordinal, resources=resources)


def at(event: str, day: str, period: str, *choices: PooledChoice) -> Assignment:
    return Assignment(event=event, day=day, start_period=period, chosen=choices)


def make_result(*assignments: Assignment) -> Result:
    return Result(assignments=assignments)
