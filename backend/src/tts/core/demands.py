"""Demands made concrete (ADR-0007, spec 02 sections 1 and 3).

A demand says how a set of participants is divided into blocks and how often each block meets.
The solver decides who is in which block. What it returns is a `Result` with `created` events.
`realise` turns those into ordinary events, so the verifier, the grids and the exports work on
them like on declared events and need no other change.
"""

from tts.core.model import (
    CreatedEvent,
    Dataset,
    Demand,
    Event,
    FixedRequirement,
    PooledRequirement,
    Result,
)


def block_sizes(count: int, blocks: int) -> tuple[int, ...]:
    """Sizes of `blocks` blocks holding `count` participants: they differ by at most one, and
    the larger blocks come first (10 participants in 4 blocks give 3, 3, 2, 2)."""
    if blocks == 0:
        return ()
    base, extra = divmod(count, blocks)
    return tuple(base + 1 if i < extra else base for i in range(blocks))


def created_event(demand: Demand, code: str) -> Event:
    """The event a demand makes: the demand's properties under a new code."""
    return Event(
        code=code,
        kind=demand.kind,
        duration=demand.duration,
        start_pattern=demand.start_pattern,
        reference=demand.reference,
        delivery=demand.delivery,
        tags=demand.tags,
        demand=demand.code,
    )


def rejected_created(dataset: Dataset, result: Result) -> list[tuple[CreatedEvent, str]]:
    """The created events of `result` that cannot be made real, with the reason.

    A created event is rejected when its demand is unknown, its code is already an event of the
    dataset or of an earlier created event, or a participant is not one of its demand's.
    """
    demands = {d.code: d for d in dataset.demands}
    taken = {e.code for e in dataset.events}
    found: list[tuple[CreatedEvent, str]] = []
    for created in result.created:
        demand = demands.get(created.demand)
        if demand is None:
            found.append((created, f'unknown demand "{created.demand}"'))
        elif created.code in taken:
            found.append((created, f'code "{created.code}" is already an event'))
        else:
            outsider = next((p for p in created.participants if p not in demand.participants), None)
            if outsider is not None:
                found.append(
                    (
                        created,
                        f'participant "{outsider}" is not a participant of demand "{demand.code}"',
                    )
                )
                continue
            taken.add(created.code)
    return found


def realise(dataset: Dataset, result: Result) -> Dataset:
    """`dataset` plus the events `result` created, as ordinary events.

    Each becomes an event with its demand's properties, its participants as fixed resources and
    its demand's pooled requirements. Rejected created events (see `rejected_created`) are left
    out; the verifier reports them. The input is not changed.
    """
    if not result.created:
        return dataset
    bad = {id(c) for c, _ in rejected_created(dataset, result)}
    demands = {d.code: d for d in dataset.demands}
    events: list[Event] = list(dataset.events)
    fixed: list[FixedRequirement] = list(dataset.fixed)
    pooled: list[PooledRequirement] = list(dataset.pooled)
    for created in result.created:
        if id(created) in bad:
            continue
        demand = demands[created.demand]
        events.append(created_event(demand, created.code))
        fixed.extend(FixedRequirement(event=created.code, resource=p) for p in created.participants)
        pooled.extend(
            PooledRequirement(event=created.code, **spec.model_dump()) for spec in demand.pooled
        )
    return dataset.model_copy(
        update={
            "events": tuple(sorted(events, key=lambda e: e.code)),
            "fixed": tuple(sorted(fixed, key=lambda f: (f.event, f.resource))),
            "pooled": tuple(sorted(pooled, key=lambda q: (q.event, q.ordinal))),
        }
    )
