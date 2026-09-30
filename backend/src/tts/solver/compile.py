"""Building the CP-SAT model from a dataset (spec 05 section 4).

The implicit rules become structure rather than constraints to be checked afterwards:

- H0: each event has one `start` variable whose domain is its allowed starts, and each pooled
  requirement picks exactly `count` of its candidate resources.
- H1: one no-overlap set per exclusive resource, holding every interval that occupies it. The
  occupancy rule itself comes from `core.hierarchy`, the same code the verifier uses.
- H2: slots where a fixed resource is unavailable are removed from the start domain. For a pooled
  candidate, choosing it forbids the starts that overlap its unavailable slots.
- H3, H4: candidates are filtered at compile time by capacity and by the filter selector.
- H5: pins narrow the start domain and force the pinned resources.

With `explain=True` (spec 05 section 5) the same rules are built, but nothing is pruned up front:
each availability row, pin, no-overlap set and pooled requirement becomes a constraint guarded by
its own assumption literal (`CompileContext.guard`), so the solver can name the rule sets that
conflict. The model is otherwise identical, so the two modes agree on feasibility.
"""

from collections import defaultdict
from collections.abc import Iterable

from ortools.sat.python import cp_model

from tts.core.candidates import Candidates
from tts.core.demands import block_sizes, materialise, participant_size
from tts.core.model import Availability, Dataset, Pin, PooledRequirement
from tts.core.selectors import SelectorError
from tts.core.timegrid import TimeGridError, covered_slots
from tts.solver.context import CompileContext
from tts.solver.registry import compile_declared


def compile_model(
    dataset: Dataset, explain: bool = False, times_only: bool = False, greedy: bool = False
) -> CompileContext:
    """The model of `dataset`. A dataset with no possible solution still compiles: the context
    records why in `problems`, and the model is infeasible.

    `explain=True` builds the guarded model used to explain infeasibility. `times_only=True`
    builds the first half of the decomposition (spec 05 section 7, `solver/decompose.py`): start
    times only, with each pool's capacity as the only rule on pooled resources.
    `greedy=True` gives every demand its default split instead of leaving it to the solver.
    """
    materialised = materialise(dataset, greedy)  # demands become events and blocks
    ctx = CompileContext(materialised.dataset, explain=explain)
    ctx.materialised = materialised
    ctx.times_only = times_only
    pins: dict[str, list[Pin]] = defaultdict(list)
    for pin in ctx.dataset.pins:
        pins[pin.event].append(pin)
    unavailable = _unavailable_rows(ctx)
    for problem in materialised.problems:
        ctx.declare_infeasible(problem)

    _start_variables(ctx, pins, unavailable)
    _pooled_variables(ctx, pins, unavailable)
    _demand_membership(ctx, unavailable)
    _no_overlap(ctx)
    _pool_capacity(ctx)
    compile_declared(ctx)
    _objective(ctx)
    return ctx


# Interchangeable blocks of a demand are ordered by their lowest participant (spec 05 4.1a). The
# switch exists so a test can show the optimum does not depend on it.
BREAK_SYMMETRY = True

Blocked = dict[str, list[tuple[int, Availability]]]  # resource -> (slot, row) it is unavailable


def _unavailable_rows(ctx: CompileContext) -> Blocked:
    found: Blocked = defaultdict(list)
    for a in ctx.dataset.availability:
        if a.status != "unavailable":
            continue
        try:
            found[a.resource].append((ctx.grid.slot(a.day, a.period), a))
        except TimeGridError:
            continue
    return found


def _slots(rows: list[tuple[int, Availability]]) -> frozenset[int]:
    return frozenset(slot for slot, _ in rows)


def _pin_allows(ctx: CompileContext, pin: Pin, t: int) -> bool:
    if pin.day is not None and ctx.grid.day_index(t) != ctx.grid.day_number(pin.day):
        return False
    return pin.start_period is None or ctx.grid.period_index(t) == ctx.grid.period_number(
        pin.start_period
    )


def _forbid(
    ctx: CompileContext,
    start: cp_model.IntVar,
    bad: list[int],
    *conditions: cp_model.IntVar | None,
) -> None:
    """`start` avoids the `bad` values whenever every condition holds (`None` = always)."""
    if not bad:
        return
    literals = [c for c in conditions if c is not None]
    constraint = ctx.model.add_linear_expression_in_domain(
        start, cp_model.Domain.from_values(bad).complement()
    )
    if literals:
        constraint.only_enforce_if(literals)


def _start_variables(ctx: CompileContext, pins: dict[str, list[Pin]], unavailable: Blocked) -> None:
    model = ctx.model
    for code, event in ctx.events.items():
        allowed = ctx.grid.allowed_starts(event)
        if ctx.explain:
            domain = list(allowed)  # availability and pins become guarded constraints below
        else:
            blocked: set[int] = set()
            for resource in ctx.hierarchy.occupied_resources(code):
                blocked |= _slots(unavailable.get(resource, []))
            domain = [
                t
                for t in allowed
                if blocked.isdisjoint(covered_slots(t, event.duration))
                and all(_pin_allows(ctx, pin, t) for pin in pins.get(code, ()))
            ]
        ctx.domains[code] = tuple(domain)
        if not domain:
            reason = (
                f'event "{code}" has no allowed start for duration {event.duration}'
                if ctx.explain
                else f'event "{code}" has no start left after availability and pins'
            )
            ctx.declare_infeasible(reason, ctx.guard("starts", code))
            start = model.new_constant(0)
        else:
            start = model.new_int_var_from_domain(
                cp_model.Domain.from_values(domain), f"start_{code}"
            )
        ctx.start[code] = start
        ctx.iv[code] = model.new_fixed_size_interval_var(start, event.duration, f"iv_{code}")

    if ctx.explain:
        _guarded_availability(ctx, unavailable)
        _guarded_pin_times(ctx, pins)


def _bad_starts(domain: tuple[int, ...], duration: int, slot: int) -> list[int]:
    return [t for t in domain if slot in covered_slots(t, duration)]


def _guarded_availability(ctx: CompileContext, unavailable: Blocked) -> None:
    """Explain mode: each unavailability row of a fixed resource is its own guarded rule set."""
    for code, event in ctx.events.items():
        for resource in sorted(ctx.hierarchy.occupied_resources(code)):
            for slot, row in unavailable.get(resource, []):
                bad = _bad_starts(ctx.domains[code], event.duration, slot)
                if bad:
                    guard = ctx.guard("availability", row.resource, row.day, row.period)
                    _forbid(ctx, ctx.start[code], bad, guard)


def _guarded_pin_times(ctx: CompileContext, pins: dict[str, list[Pin]]) -> None:
    """Explain mode: each pin's day and start is its own guarded rule set."""
    for code, event_pins in pins.items():
        if code not in ctx.events:
            continue
        for index, pin in enumerate(event_pins):
            guard = ctx.guard("pin", code, str(index))
            assert guard is not None
            domain = ctx.domains[code]
            allowed = [t for t in domain if _pin_allows(ctx, pin, t)]
            if not allowed:
                ctx.model.add_bool_or([guard.Not()])
            elif len(allowed) < len(domain):
                ctx.model.add_linear_expression_in_domain(
                    ctx.start[code], cp_model.Domain.from_values(allowed)
                ).only_enforce_if(guard)


def _pooled_variables(
    ctx: CompileContext, pins: dict[str, list[Pin]], unavailable: Blocked
) -> None:
    model = ctx.model
    static = Candidates(ctx.dataset, ctx.hierarchy, ctx.selectors)
    bad_filters: set[str] = set()

    for q in ctx.dataset.pooled:
        event = ctx.events.get(q.event)
        if event is None:
            continue
        label = f"{q.event}#{q.ordinal}"
        needed = static.needed(q)
        requirement_guard = ctx.guard("requirement", q.event, str(q.ordinal))
        try:
            eligible = static.of(q).codes
        except SelectorError as error:
            eligible = ()
            if q.filter not in bad_filters and not ctx.explain:
                bad_filters.add(q.filter)
                ctx.declare_infeasible(
                    f'filter "{q.filter}" of requirement {label}: {error.message}'
                )
        domain = ctx.domains[q.event]
        pinned = _pinned_choice(ctx, pins.get(q.event, ()), q, eligible)
        if pinned is not None:
            eligible = pinned
        candidates: list[str] = []
        for code in eligible:
            rows = unavailable.get(code, [])
            if not ctx.explain:
                bad_slots = _slots(rows)
                usable = [
                    t for t in domain if bad_slots.isdisjoint(covered_slots(t, event.duration))
                ]
                if not usable:
                    continue
            if ctx.times_only:
                candidates.append(code)
                continue
            literal = model.new_bool_var(f"use_{label}_{code}")
            ctx.use[(q.event, q.ordinal, code)] = literal
            ctx.oiv[(q.event, q.ordinal, code)] = model.new_optional_fixed_size_interval_var(
                ctx.start[q.event], event.duration, literal, f"oiv_{label}_{code}"
            )
            if ctx.explain:
                for slot, row in rows:
                    guard = ctx.guard("availability", row.resource, row.day, row.period)
                    _forbid(
                        ctx, ctx.start[q.event], _bad_starts(domain, event.duration, slot),
                        literal, guard,
                    )  # fmt: skip
            elif len(usable) < len(domain):
                # Choosing this resource forbids the starts that overlap its unavailable slots.
                model.add_linear_expression_in_domain(
                    ctx.start[q.event], cp_model.Domain.from_values(usable)
                ).only_enforce_if(literal)
            candidates.append(code)
        ctx.candidates[(q.event, q.ordinal)] = tuple(candidates)
        if len(candidates) < q.count and not ctx.explain:
            ctx.declare_infeasible(
                f"requirement {label} needs {q.count} {q.resource_type} resource(s) but only "
                f"{len(candidates)} can serve it (type, filter, capacity {needed}, availability)"
            )
        if ctx.times_only:
            continue
        chosen = sum(ctx.use[(q.event, q.ordinal, code)] for code in candidates)
        constraint = model.add(chosen == q.count)
        if requirement_guard is not None:
            constraint.only_enforce_if(requirement_guard)

    if not ctx.times_only:
        _pinned_resources(ctx, pins)


def _demand_membership(ctx: CompileContext, unavailable: Blocked) -> None:
    """Who is in which block of each demand the solver splits (spec 05 section 4.1a).

    A literal `x[p, b]` says participant `p` is in block `b`. Each participant is in exactly one
    block, block sizes stay within the bounds (so they differ by at most one), and every event of
    a block occupies a participant exactly when the participant is in the block (H1), is
    unavailable under the same condition (H2), and needs a room that seats its members (H3).
    """
    mat = ctx.materialised
    if mat is None or not mat.free:
        return
    model = ctx.model
    requirements: dict[str, list[PooledRequirement]] = defaultdict(list)
    for q in ctx.dataset.pooled:
        requirements[q.event].append(q)

    for code in sorted(mat.free):
        participants = mat.free[code]
        low, high = mat.bounds[code]
        blocks = [b for b in mat.blocks if b.demand == code and b.fixed is None]
        count = len(participants)
        x = [[model.new_bool_var(f"x_{code}_{p}_{b.index}") for b in blocks] for p in participants]

        size_guard = ctx.guard("demand", code, "sizes")
        for i, p in enumerate(participants):
            once = model.add(sum(x[i]) == 1)
            guard = ctx.guard("demand", code, p)
            if guard is not None:
                once.only_enforce_if(guard)
        for bi in range(len(blocks)):
            total = sum(x[i][bi] for i in range(count))
            for bound in (total >= low, total <= high):
                constraint = model.add(bound)
                if size_guard is not None:
                    constraint.only_enforce_if(size_guard)

        # Blocks are interchangeable, so order them by their lowest participant.
        for bi in range(1, len(blocks) if BREAK_SYMMETRY else 0):
            for i in range(count):
                model.add_bool_or([x[i][bi].Not(), *(x[j][bi - 1] for j in range(i))])
        cursor = 0
        for bi, size in enumerate(block_sizes(count, len(blocks))):
            for i in range(count):
                model.add_hint(x[i][bi], 1 if cursor <= i < cursor + size else 0)
            cursor += size

        for bi, block in enumerate(blocks):
            ctx.block_members[(code, block.index)] = [
                (p, x[i][bi]) for i, p in enumerate(participants)
            ]
            for i, p in enumerate(participants):
                literal = x[i][bi]
                occupied = sorted({p} | set(ctx.hierarchy.exclusive_descendants(p)))
                for event in block.events:
                    duration = ctx.events[event].duration
                    for resource in occupied:
                        ctx.members[resource].append((event, literal))
                        for slot, row in unavailable.get(resource, []):
                            bad = _bad_starts(ctx.domains[event], duration, slot)
                            guard = ctx.guard("availability", row.resource, row.day, row.period)
                            _forbid(ctx, ctx.start[event], bad, literal, guard)
            for event in block.events:
                for q in requirements.get(event, ()):
                    rule = q.capacity_rule
                    if rule.resource_type is None:
                        continue
                    sizes = [
                        participant_size(ctx.hierarchy, ctx.resources, p, rule.resource_type)
                        for p in participants
                    ]
                    if not any(sizes):
                        continue
                    load = sum(s * x[i][bi] for i, s in enumerate(sizes) if s)
                    candidates = ctx.candidates.get((event, q.ordinal), ())
                    biggest = max((ctx.resources[r].capacity or 0 for r in candidates), default=0)
                    if candidates and sum(sizes) > biggest and not ctx.explain:
                        model.add(load <= biggest)  # no room is bigger: a block must fit it
                    if ctx.times_only:
                        continue  # the rooms are chosen in the second step
                    requirement_guard = ctx.guard("requirement", event, str(q.ordinal))
                    for resource in candidates:
                        capacity = ctx.resources[resource].capacity or 0
                        if sum(sizes) <= capacity:
                            continue  # it seats everyone, whatever the block
                        conditions = [ctx.use[(event, q.ordinal, resource)]]
                        if requirement_guard is not None:
                            conditions.append(requirement_guard)
                        model.add(load <= capacity).only_enforce_if(conditions)


def _pinned_choice(
    ctx: CompileContext, event_pins: Iterable[Pin], q: PooledRequirement, eligible: Iterable[str]
) -> tuple[str, ...] | None:
    """The only possible choice for a requirement, when pins already make it; else None.

    When an event has one pooled requirement and its pins name exactly `count` resources that
    can serve it, every solution uses those (H5), so the other candidates need no variables.
    This keeps locked events of earlier stages small (P10.5). Not used when explaining.
    """
    if ctx.explain or sum(1 for other in ctx.dataset.pooled if other.event == q.event) != 1:
        return None
    named = {r for pin in event_pins for r in pin.resources}
    usable = tuple(code for code in eligible if code in named)
    return usable if named and len(usable) == q.count else None


def _pinned_resources(ctx: CompileContext, pins: dict[str, list[Pin]]) -> None:
    """A pinned resource is forced into the first requirement of the event that can use it."""
    for code, event_pins in pins.items():
        ordinals = sorted(o for (e, o) in ctx.candidates if e == code)
        for index, pin in enumerate(event_pins):
            guard = ctx.guard("pin", code, str(index))
            for resource in pin.resources:
                for ordinal in ordinals:
                    literal = ctx.use.get((code, ordinal, resource))
                    if literal is not None:
                        forced = ctx.model.add(literal == 1)
                        if guard is not None:
                            forced.only_enforce_if(guard)
                        break
                else:
                    ctx.declare_infeasible(
                        f'event "{code}" is pinned to "{resource}", which no requirement can use',
                        guard,
                    )


def _no_overlap(ctx: CompileContext) -> None:
    """H1: one no-overlap set per exclusive resource."""
    # resource -> (event, pooled `use` literal or None for fixed occupancy, its interval)
    members: dict[str, list[tuple[str, cp_model.IntVar | None, cp_model.IntervalVar]]] = (
        defaultdict(list)
    )
    for code in ctx.events:
        for resource in sorted(ctx.hierarchy.occupied_exclusive(code)):
            members[resource].append((code, None, ctx.iv[code]))
    for (code, ordinal, resource), interval in ctx.oiv.items():
        # A pooled candidate the event already occupies through its fixed resources is one use.
        if resource not in ctx.hierarchy.occupied_exclusive(code):
            members[resource].append((code, ctx.use[(code, ordinal, resource)], interval))
    for resource in sorted(ctx.members):  # participants of blocks the solver fills (ADR-0007)
        for code, literal in ctx.members[resource]:
            interval = ctx.model.new_optional_fixed_size_interval_var(
                ctx.start[code], ctx.events[code].duration, literal, f"m_{resource}_{code}"
            )
            members[resource].append((code, literal, interval))

    for resource in sorted(members):
        entries = members[resource]
        for _, _, interval in entries:
            ctx.add_occupant(resource, interval)
        if len(entries) < 2:
            continue
        guard = ctx.guard("no_overlap", resource)
        if guard is None:
            ctx.model.add_no_overlap([interval for _, _, interval in entries])
            continue
        guarded = []
        for code, use, _ in entries:
            if use is None:
                present = guard
            else:
                present = ctx.model.new_bool_var(f"on_{resource}_{code}")
                ctx.model.add_bool_and([use, guard]).only_enforce_if(present)
                ctx.model.add_bool_or([use.Not(), guard.Not(), present])
            guarded.append(
                ctx.model.new_optional_fixed_size_interval_var(
                    ctx.start[code], ctx.events[code].duration, present, f"g_{resource}_{code}"
                )
            )
        ctx.model.add_no_overlap(guarded)


def _pool_capacity(ctx: CompileContext) -> None:
    """In the times-only model: at any time, the events that must take their resources from a
    set S cannot need more than |S| of them (spec 05 section 7, "aggregated capacity").

    For each distinct candidate set S, the events whose candidates all lie in S share a cumulative
    of capacity |S|, each needing `count`. This is the only rule on pooled resources in the first
    half of the decomposition. In the full model it is implied and measured no faster (P10.4), so
    it is not added there.
    """
    if not ctx.times_only:
        return
    counts = {(q.event, q.ordinal): q.count for q in ctx.dataset.pooled}
    needs: dict[str, list[tuple[frozenset[str], int]]] = defaultdict(list)
    for (event, ordinal), candidates in ctx.candidates.items():
        needs[event].append((frozenset(candidates), counts[(event, ordinal)]))
    pools = {pool for items in needs.values() for pool, _ in items if pool}
    for pool in sorted(pools, key=lambda p: (len(p), sorted(p))):
        members = [
            (event, count)
            for event, items in needs.items()
            for candidates, count in items
            if candidates and candidates <= pool
        ]
        if sum(count for _, count in members) <= len(pool):
            continue  # can never be full
        ctx.model.add_cumulative(
            [ctx.iv[event] for event, _ in members], [count for _, count in members], len(pool)
        )


def _objective(ctx: CompileContext) -> None:
    """Minimise the weighted penalties of soft constraints, if any were compiled."""
    if ctx.explain:
        return  # an explanation is only about feasibility
    weights = {c.code: c.weight for c in ctx.dataset.constraints if c.active and not c.hard}
    terms = [weights.get(name, 1) * var for name, var in ctx.penalties.items()]
    if terms:
        ctx.model.minimize(sum(terms))
