"""Demands made concrete (ADR-0007, spec 02 sections 1 and 3).

A demand says how a set of participants is divided into blocks and how often each block meets.
The solver decides who is in which block. What it returns is a `Result` with `created` events.
`realise` turns those into ordinary events, so the verifier, the grids and the exports work on
them like on declared events and need no other change.
"""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from tts.core.hierarchy import Hierarchy
from tts.core.model import (
    CreatedEvent,
    Dataset,
    Demand,
    Event,
    FixedRequirement,
    PooledRequirement,
    Resource,
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


def participant_size(
    hierarchy: Hierarchy, resources: Mapping[str, Resource], code: str, resource_type: str
) -> int:
    """What one participant adds to a `sum_of_fixed:<resource_type>` rule (spec 04 section 1, H3).

    The participant's own capacity if it is of that type, else the sum over its exclusive
    descendants of that type. A missing capacity counts as 0.
    """
    resource = resources.get(code)
    if resource is None:
        return 0
    if resource.type == resource_type:
        return resource.capacity or 0
    return sum(
        resources[d].capacity or 0
        for d in hierarchy.exclusive_descendants(code)
        if resources[d].type == resource_type
    )


def complete_edits(dataset: Dataset) -> Dataset:
    """Give each declared event of a demand that has no pooled requirements the demand's own.

    An edit only has to store its participants and its pins; what it needs (a room, a teacher)
    is the same as for the sessions the solver creates.
    """
    if not dataset.demands:
        return dataset
    owners = {d.code: d for d in dataset.demands}
    have = {q.event for q in dataset.pooled}
    added = [
        PooledRequirement(event=e.code, **spec.model_dump())
        for e in dataset.events
        if e.demand in owners and e.code not in have
        for spec in owners[e.demand].pooled
    ]
    if not added:
        return dataset
    pooled = sorted((*dataset.pooled, *added), key=lambda q: (q.event, q.ordinal))
    return dataset.model_copy(update={"pooled": tuple(pooled)})


@dataclass(frozen=True, slots=True)
class Block:
    """The sessions of one block of a demand.

    `events` are the codes of all its events (declared edits and the ones the solver creates),
    `made` only the ones the solver creates. `fixed` is the block's participants when they are
    known before solving (an edit, or the only possible split), and None when the solver chooses.
    """

    demand: str
    index: int
    events: tuple[str, ...]
    made: tuple[str, ...]
    fixed: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class Materialised:
    """A dataset with its demands made concrete, ready for the solver (ADR-0007).

    `dataset` holds every event: declared ones, and a placeholder for each session the solver
    creates. Placeholders of a block with known participants have them as fixed resources; the
    others have none yet. `free` lists, for each demand with blocks to fill, the participants the
    solver places, and `bounds` the smallest and largest size a block may have. `problems` are
    reasons no solution exists (an edit that cannot be part of any valid split).
    """

    dataset: Dataset
    blocks: tuple[Block, ...] = ()
    free: Mapping[str, tuple[str, ...]] = None  # type: ignore[assignment]
    bounds: Mapping[str, tuple[int, int]] = None  # type: ignore[assignment]
    problems: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.free is None:
            object.__setattr__(self, "free", {})
        if self.bounds is None:
            object.__setattr__(self, "bounds", {})


def placeholder_code(demand: str, block: int, repetition: int) -> str:
    """The internal code of a session the solver creates. The final code is given when the
    solution is read back."""
    return f"{demand}@{block}.{repetition}"


def materialise(dataset: Dataset) -> Materialised:
    """Make a dataset's demands concrete (ADR-0007, spec 05 section 2.2).

    For each demand: its declared events (edits) are grouped into blocks by their participants;
    each edited block gets the repetitions it lacks. The participants left over fill the other
    blocks. When only one split is possible (one block left, or blocks of one participant each)
    those blocks get their participants here; otherwise the solver chooses them (`free`).
    """
    if not dataset.demands:
        return Materialised(dataset)
    base = complete_edits(dataset)
    declared_fixed: dict[str, set[str]] = defaultdict(set)
    for f in base.fixed:
        declared_fixed[f.event].add(f.resource)
    taken = {e.code for e in base.events}

    events: list[Event] = list(base.events)
    fixed: list[FixedRequirement] = list(base.fixed)
    pooled: list[PooledRequirement] = list(base.pooled)
    blocks: list[Block] = []
    free: dict[str, tuple[str, ...]] = {}
    bounds: dict[str, tuple[int, int]] = {}
    problems: list[str] = []

    for d in base.demands:
        count = len(d.participants)
        if count == 0:
            continue
        wanted = d.blocks
        low, high = count // wanted, -(-count // wanted)
        bounds[d.code] = (low, high)
        allowed = set(d.participants)

        by_who: dict[frozenset[str], list[str]] = defaultdict(list)
        for e in base.events:
            if e.demand != d.code:
                continue
            who = frozenset(declared_fixed[e.code] & allowed)
            if who:
                by_who[who].append(e.code)
            else:
                problems.append(f'event "{e.code}" of demand "{d.code}" has no participants')
        edited = sorted(by_who.items(), key=lambda item: min(item[0]))
        placed: set[str] = set()
        for who, codes in edited:
            for participant in sorted(who):
                if participant in placed:
                    problems.append(f'"{participant}" is in two edited blocks of demand "{d.code}"')
                placed.add(participant)
            if not low <= len(who) <= high:
                sizes = f"{low}" if low == high else f"{low} or {high}"
                problems.append(
                    f'edited block {", ".join(sorted(who))} of demand "{d.code}" has size '
                    f"{len(who)}, but blocks must have size {sizes}"
                )
            if len(codes) > d.repeat:
                problems.append(
                    f'edited block {", ".join(sorted(who))} of demand "{d.code}" has '
                    f"{len(codes)} events, more than the {d.repeat} repetition(s) of the demand"
                )
        if len(edited) > wanted:
            problems.append(
                f'demand "{d.code}" has {len(edited)} edited blocks, more than the {wanted} '
                "it needs"
            )

        index = 0

        def add_block(
            participants: tuple[str, ...] | None,
            declared: list[str],
            demand: Demand = d,
            position: int | None = None,
        ) -> None:
            nonlocal index
            block = index if position is None else position
            made = []
            for repetition in range(len(declared), demand.repeat):
                code = placeholder_code(demand.code, block, repetition)
                while code in taken:
                    code += "'"
                taken.add(code)
                made.append(code)
                events.append(created_event(demand, code))
                pooled.extend(
                    PooledRequirement(event=code, **spec.model_dump()) for spec in demand.pooled
                )
                if participants is not None:
                    fixed.extend(FixedRequirement(event=code, resource=p) for p in participants)
            blocks.append(Block(demand.code, block, (*declared, *made), tuple(made), participants))
            index += 1

        for who, codes in edited:
            add_block(tuple(sorted(who)), list(codes))

        rest = [p for p in d.participants if p not in placed]
        open_blocks = wanted - len(edited)
        if not rest:
            continue
        if open_blocks <= 0:
            problems.append(f'demand "{d.code}": no block is left for {", ".join(rest)}')
        elif not open_blocks * low <= len(rest) <= open_blocks * high:
            problems.append(
                f'demand "{d.code}": {len(rest)} participants cannot fill {open_blocks} '
                f"block(s) of size {low} to {high}"
            )
        elif open_blocks == 1:
            add_block(tuple(rest), [])
        elif high == 1:
            for participant in rest:
                add_block((participant,), [])
        else:
            free[d.code] = tuple(rest)
            for _ in range(open_blocks):
                add_block(None, [])

    result = base.model_copy(
        update={
            "events": tuple(sorted(events, key=lambda e: e.code)),
            "fixed": tuple(sorted(fixed, key=lambda f: (f.event, f.resource))),
            "pooled": tuple(sorted(pooled, key=lambda q: (q.event, q.ordinal))),
        }
    )
    return Materialised(result, tuple(blocks), free, bounds, tuple(problems))


def realise(dataset: Dataset, result: Result) -> Dataset:
    """`dataset` plus the events `result` created, as ordinary events.

    Each becomes an event with its demand's properties, its participants as fixed resources and
    its demand's pooled requirements. Rejected created events (see `rejected_created`) are left
    out; the verifier reports them. The input is not changed.
    """
    dataset = complete_edits(dataset)
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
