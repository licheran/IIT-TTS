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
"""

from collections import defaultdict

from ortools.sat.python import cp_model

from tts.core.candidates import Candidates
from tts.core.model import Dataset, Pin
from tts.core.selectors import SelectorError
from tts.core.timegrid import TimeGridError, covered_slots
from tts.solver.context import CompileContext
from tts.solver.registry import compile_declared


def compile_model(dataset: Dataset) -> CompileContext:
    """The model of `dataset`. A dataset with no possible solution still compiles: the context
    records why in `problems`, and the model is infeasible."""
    ctx = CompileContext(dataset)
    pins: dict[str, list[Pin]] = defaultdict(list)
    for pin in dataset.pins:
        pins[pin.event].append(pin)
    unavailable = _unavailable_slots(ctx)

    _start_variables(ctx, pins, unavailable)
    _pooled_variables(ctx, pins, unavailable)
    _no_overlap(ctx)
    compile_declared(ctx)
    _objective(ctx)
    return ctx


def _unavailable_slots(ctx: CompileContext) -> dict[str, frozenset[int]]:
    found: dict[str, set[int]] = defaultdict(set)
    for a in ctx.dataset.availability:
        if a.status != "unavailable":
            continue
        try:
            found[a.resource].add(ctx.grid.slot(a.day, a.period))
        except TimeGridError:
            continue
    return {resource: frozenset(slots) for resource, slots in found.items()}


def _pin_allows(ctx: CompileContext, pin: Pin, t: int) -> bool:
    if pin.day is not None and ctx.grid.day_index(t) != ctx.grid.day_number(pin.day):
        return False
    return pin.start_period is None or ctx.grid.period_index(t) == ctx.grid.period_number(
        pin.start_period
    )


def _start_variables(
    ctx: CompileContext, pins: dict[str, list[Pin]], unavailable: dict[str, frozenset[int]]
) -> None:
    model = ctx.model
    for code, event in ctx.events.items():
        blocked: set[int] = set()
        for resource in ctx.hierarchy.occupied_resources(code):
            blocked |= unavailable.get(resource, frozenset())
        domain = [
            t
            for t in ctx.grid.allowed_starts(event)
            if blocked.isdisjoint(covered_slots(t, event.duration))
            and all(_pin_allows(ctx, pin, t) for pin in pins.get(code, ()))
        ]
        ctx.domains[code] = tuple(domain)
        if not domain:
            ctx.declare_infeasible(f'event "{code}" has no start left after availability and pins')
            start = model.new_constant(0)
        else:
            start = model.new_int_var_from_domain(
                cp_model.Domain.from_values(domain), f"start_{code}"
            )
        ctx.start[code] = start
        ctx.iv[code] = model.new_fixed_size_interval_var(start, event.duration, f"iv_{code}")


def _pooled_variables(
    ctx: CompileContext, pins: dict[str, list[Pin]], unavailable: dict[str, frozenset[int]]
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
        try:
            eligible = static.of(q).codes
        except SelectorError as error:
            eligible = ()
            if q.filter not in bad_filters:
                bad_filters.add(q.filter)
                ctx.declare_infeasible(
                    f'filter "{q.filter}" of requirement {label}: {error.message}'
                )
        domain = ctx.domains[q.event]
        candidates: list[str] = []
        for code in eligible:
            bad = unavailable.get(code, frozenset())
            usable = [t for t in domain if bad.isdisjoint(covered_slots(t, event.duration))]
            if not usable:
                continue
            literal = model.new_bool_var(f"use_{label}_{code}")
            ctx.use[(q.event, q.ordinal, code)] = literal
            ctx.oiv[(q.event, q.ordinal, code)] = model.new_optional_fixed_size_interval_var(
                ctx.start[q.event], event.duration, literal, f"oiv_{label}_{code}"
            )
            if len(usable) < len(domain):
                # Choosing this resource forbids the starts that overlap its unavailable slots.
                model.add_linear_expression_in_domain(
                    ctx.start[q.event], cp_model.Domain.from_values(usable)
                ).only_enforce_if(literal)
            candidates.append(code)
        ctx.candidates[(q.event, q.ordinal)] = tuple(candidates)
        if len(candidates) < q.count:
            ctx.declare_infeasible(
                f"requirement {label} needs {q.count} {q.resource_type} resource(s) but only "
                f"{len(candidates)} can serve it (type, filter, capacity {needed}, availability)"
            )
        model.add(sum(ctx.use[(q.event, q.ordinal, code)] for code in candidates) == q.count)

    _pinned_resources(ctx, pins)


def _pinned_resources(ctx: CompileContext, pins: dict[str, list[Pin]]) -> None:
    """A pinned resource is forced into the first requirement of the event that can use it."""
    for code, event_pins in pins.items():
        ordinals = sorted(o for (e, o) in ctx.candidates if e == code)
        for pin in event_pins:
            for resource in pin.resources:
                for ordinal in ordinals:
                    literal = ctx.use.get((code, ordinal, resource))
                    if literal is not None:
                        ctx.model.add(literal == 1)
                        break
                else:
                    ctx.declare_infeasible(
                        f'event "{code}" is pinned to "{resource}", which no requirement can use'
                    )


def _no_overlap(ctx: CompileContext) -> None:
    """H1: one no-overlap set per exclusive resource."""
    for code in ctx.events:
        fixed = ctx.hierarchy.occupied_exclusive(code)
        for resource in sorted(fixed):
            ctx.add_occupant(resource, ctx.iv[code])
    for (code, _ordinal, resource), interval in ctx.oiv.items():
        # A pooled candidate the event already occupies through its fixed resources is one use.
        if resource not in ctx.hierarchy.occupied_exclusive(code):
            ctx.add_occupant(resource, interval)
    for resource in ctx.occupied_resources():
        intervals = ctx.occupants(resource)
        if len(intervals) > 1:
            ctx.model.add_no_overlap(intervals)


def _objective(ctx: CompileContext) -> None:
    """Minimise the weighted penalties of soft constraints, if any were compiled."""
    weights = {c.code: c.weight for c in ctx.dataset.constraints if c.active and not c.hard}
    terms = [weights.get(name, 1) * var for name, var in ctx.penalties.items()]
    if terms:
        ctx.model.minimize(sum(terms))
