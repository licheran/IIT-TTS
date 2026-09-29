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

from ortools.sat.python import cp_model

from tts.core.candidates import Candidates
from tts.core.model import Availability, Dataset, Pin
from tts.core.selectors import SelectorError
from tts.core.timegrid import TimeGridError, covered_slots
from tts.solver.context import CompileContext
from tts.solver.registry import compile_declared


def compile_model(dataset: Dataset, explain: bool = False) -> CompileContext:
    """The model of `dataset`. A dataset with no possible solution still compiles: the context
    records why in `problems`, and the model is infeasible.

    `explain=True` builds the guarded model used to explain infeasibility.
    """
    ctx = CompileContext(dataset, explain=explain)
    pins: dict[str, list[Pin]] = defaultdict(list)
    for pin in dataset.pins:
        pins[pin.event].append(pin)
    unavailable = _unavailable_rows(ctx)

    _start_variables(ctx, pins, unavailable)
    _pooled_variables(ctx, pins, unavailable)
    _no_overlap(ctx)
    compile_declared(ctx)
    _objective(ctx)
    return ctx


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
        chosen = sum(ctx.use[(q.event, q.ordinal, code)] for code in candidates)
        constraint = model.add(chosen == q.count)
        if requirement_guard is not None:
            constraint.only_enforce_if(requirement_guard)

    _pinned_resources(ctx, pins)


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


def _objective(ctx: CompileContext) -> None:
    """Minimise the weighted penalties of soft constraints, if any were compiled."""
    if ctx.explain:
        return  # an explanation is only about feasibility
    weights = {c.code: c.weight for c in ctx.dataset.constraints if c.active and not c.hard}
    terms = [weights.get(name, 1) * var for name, var in ctx.penalties.items()]
    if terms:
        ctx.model.minimize(sum(terms))
