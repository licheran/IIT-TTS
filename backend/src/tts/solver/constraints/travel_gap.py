"""C10 `travel_gap` (semantics in `core/constraints/travel_gap.py`).

For each ordered pair (a, b) of events that can occupy the resource and can be in different
locations, and for each start of a with a start of b close enough after it, a violation literal
is at least 1 when: both start there, both occupy the resource, both have a location, the
locations differ, and every non-break slot between them is free. Pairs whose candidates all sit
under the same location are skipped: they can never differ.
"""

from ortools.sat.python import cp_model

from tts.core.constraints.travel_gap import Params, locations
from tts.core.model import Constraint
from tts.solver.constraints.base import Term, finish, load, violated
from tts.solver.context import CompileContext


class _Places:
    """Location literals of each event: `at[(event, place)]` and `located[event]`."""

    def __init__(self, ctx: CompileContext, level: str) -> None:
        self.ctx = ctx
        self.level = level
        self.types = {r.code: r.type for r in ctx.dataset.resources}
        self.at: dict[tuple[str, str], cp_model.IntVar] = {}
        self.located: dict[str, cp_model.IntVar | int] = {}
        self.options: dict[str, frozenset[str]] = {}

    def of(self, event: str) -> frozenset[str]:
        """The locations the event may have, building its literals on first use."""
        if event in self.options:
            return self.options[event]
        ctx = self.ctx
        by_place: dict[str, list[cp_model.IntVar]] = {}
        unplaced_choice = False
        for (e, _, resource), literal in ctx.use.items():
            if e != event:
                continue
            places = locations(ctx.hierarchy, self.types, resource, self.level)
            if not places:
                unplaced_choice = True
            for place in places:
                by_place.setdefault(place, []).append(literal)
        for place, literals in by_place.items():
            x = ctx.model.new_bool_var(f"loc_{event}_{place}")
            ctx.model.add_max_equality(x, literals)
            self.at[(event, place)] = x
        if by_place and unplaced_choice:
            located = ctx.model.new_bool_var(f"located_{event}")
            ctx.model.add_max_equality(located, [self.at[(event, p)] for p in by_place])
            self.located[event] = located
        else:
            self.located[event] = 1 if by_place else 0
        self.options[event] = frozenset(by_place)
        return self.options[event]


def compile(ctx: CompileContext, constraint: Constraint) -> None:  # noqa: A001
    instance = load(ctx, constraint, Params)
    if instance is None:
        return
    need, level = instance.params.min_periods, instance.params.level
    places = _Places(ctx, level)
    model = ctx.model
    terms: list[Term] = []
    for resource in instance.targets:
        occupants = ctx.occupying_events(resource)
        for a, needs_a in occupants:
            for b, needs_b in occupants:
                if a == b:
                    continue
                pa, pb = places.of(a), places.of(b)
                if not pa or not pb or len(pa | pb) < 2:
                    continue
                name = f"c10_{constraint.code}_{resource}_{a}_{b}"
                differ = model.new_bool_var(f"{name}_diff")
                for place in pa | pb:
                    xa = places.at.get((a, place), 0)
                    xb = places.at.get((b, place), 0)
                    model.add(differ >= xa - xb)
                    model.add(differ >= xb - xa)
                v = violated(ctx, name)
                used = False
                duration = ctx.events[a].duration
                starts_b = ctx.start_is(b)
                for sa, at_a in ctx.start_is(a).items():
                    end = sa + duration
                    day = ctx.grid.day_index(sa)
                    for sb, at_b in starts_b.items():
                        if sb < end or ctx.grid.day_index(sb) != day:
                            continue
                        gap = [t for t in range(end, sb) if not ctx.grid.is_break(t)]
                        if len(gap) >= need:
                            continue
                        busy = [o for t in gap if (o := ctx.occupied(resource, t)) is not None]
                        conditions: list[cp_model.IntVar | int] = [
                            at_a, at_b, differ, places.located[a], places.located[b]
                        ]  # fmt: skip
                        conditions += [n for n in (needs_a, needs_b) if n is not None]
                        model.add(v >= sum(conditions) - (len(conditions) - 1) - sum(busy))
                        used = True
                if used:
                    terms.append(v)
    finish(ctx, constraint, terms)
