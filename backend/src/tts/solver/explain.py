"""Explaining why a dataset has no timetable (spec 05 section 5).

1. Compile the guarded model (`compile_model(dataset, explain=True)`): every hard rule set has an
   assumption literal. The rule sets are each availability row, pin, per-resource no-overlap set,
   pooled requirement, declared hard constraint, and an event's allowed starts.
2. Solve with every guard assumed, and read the sufficient assumptions for infeasibility.
3. Shrink that core greedily: drop one rule set, and if the rest is still infeasible, keep it
   dropped. Each solve has a short time limit, and the whole search a budget. A rule set whose test
   times out is kept, and the result is marked as not proven minimal.
4. Describe the remaining rule sets by entity code, with type words from the `label` function passed
   in, so this package stays free of domain vocabulary.
"""

import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from ortools.sat.python import cp_model

from tts.core.model import Dataset, Diagnostic, Ref
from tts.core.timegrid import TimeGrid
from tts.solver.compile import compile_model
from tts.solver.context import CompileContext, RuleSet

Labeller = Callable[[str], str]

PER_SOLVE_S = 5.0
BUDGET_S = 60.0

# Order in which the rule sets are listed: the ones a user most likely changes come first.
_KIND_ORDER = {
    "constraint": 0,
    "availability": 1,
    "pin": 2,
    "starts": 3,
    "requirement": 4,
    "no_overlap": 5,
}


@dataclass(frozen=True, slots=True)
class Core:
    """Rule sets that cannot all hold at once. `minimal`: no rule set can be dropped."""

    rule_sets: tuple[RuleSet, ...]
    minimal: bool


def find_core(
    dataset: Dataset, per_solve_s: float = PER_SOLVE_S, budget_s: float = BUDGET_S, seed: int = 0
) -> Core | None:
    """The conflicting rule sets of `dataset`, or `None` if it is not proven infeasible."""
    started = time.perf_counter()
    ctx = compile_model(dataset, explain=True)
    status, core = solve_with(ctx, sorted(ctx.guards), per_solve_s, seed)
    if status != cp_model.INFEASIBLE:
        return None

    current = sorted(core)
    minimal = True
    for rule_set in list(current):
        if rule_set not in current:
            continue  # already dropped by a smaller core found on the way
        left = budget_s - (time.perf_counter() - started)
        if left <= 0:
            minimal = False
            break
        trial = [g for g in current if g != rule_set]
        status, smaller = solve_with(ctx, trial, min(per_solve_s, left), seed)
        if status == cp_model.INFEASIBLE:
            current = sorted(set(trial) & set(smaller))
        elif status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            minimal = False  # could not tell in time: keep the rule set
    return Core(rule_sets=tuple(current), minimal=minimal)


def solve_with(
    ctx: CompileContext, rule_sets: Iterable[RuleSet], time_limit_s: float, seed: int = 0
) -> tuple[cp_model.CpSolverStatus, list[RuleSet]]:
    """Solve the guarded model with only `rule_sets` switched on.

    Returns the status and, when infeasible, the rule sets CP-SAT found sufficient for that.
    """
    active = list(rule_sets)
    model = ctx.model
    model.clear_assumptions()
    model.add_assumptions([ctx.guards[g] for g in active])
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(time_limit_s, 0.01)
    solver.parameters.num_workers = 1  # cores from assumptions are only reliable on one worker
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    if status != cp_model.INFEASIBLE:
        return status, []
    by_index = {ctx.guards[g].index: g for g in active}
    found = [
        by_index[i] for i in solver.sufficient_assumptions_for_infeasibility() if i in by_index
    ]
    return status, found


def explain(
    dataset: Dataset,
    label: Labeller = str,
    per_solve_s: float = PER_SOLVE_S,
    budget_s: float = BUDGET_S,
) -> Diagnostic | None:
    """A diagnostic of kind `infeasible_core` naming the conflicting rules, or `None` when the
    dataset is not proven infeasible."""
    core = find_core(dataset, per_solve_s, budget_s)
    if core is None:
        return None
    return describe(dataset, core, label)


# --- Messages ---------------------------------------------------------------------------------


def describe(dataset: Dataset, core: Core, label: Labeller = str) -> Diagnostic:
    """Turn a core into a readable diagnostic."""
    describer = _Describer(dataset, label)
    details: list[str] = []
    refs: list[Ref] = []
    by_kind: dict[str, list[RuleSet]] = defaultdict(list)
    for rule_set in core.rule_sets:
        by_kind[rule_set.kind].append(rule_set)
    for kind in sorted(by_kind, key=lambda k: _KIND_ORDER.get(k, 99)):
        for text, rule_refs in describer.describe(kind, by_kind[kind]):
            details.append(text)
            refs.extend(r for r in rule_refs if r not in refs)
    if not details:
        details.append("the time grid and durations alone leave no solution")
    message = "Conflicting rules: " + "; ".join(details)
    if not core.minimal:
        message += " (may include rules that are not needed: the search ran out of time)"
    return Diagnostic(
        kind="infeasible_core",
        message=message,
        refs=tuple(refs),
        details=tuple(details),
        minimal=core.minimal,
    )


def _event(code: str) -> Ref:
    return Ref(kind="event", code=code)


def _resource(code: str) -> Ref:
    return Ref(kind="resource", code=code)


class _Describer:
    def __init__(self, dataset: Dataset, label: Labeller) -> None:
        self.ds = dataset
        self.label = label
        self.grid = TimeGrid(dataset.time)
        self.ctx = CompileContext(dataset)  # indexes only: hierarchy, selectors, maps
        self.days = [d.code for d in dataset.time.days]
        self.periods = [p.code for p in dataset.time.periods]
        self.usable = [p.code for p in dataset.time.periods if not p.is_break]

    def kind_of(self, resource: str) -> str:
        found = self.ctx.resources.get(resource)
        return self.label(found.type) if found is not None else ""

    def named(self, resource: str) -> str:
        return f"{self.kind_of(resource)} {resource}".strip()

    def describe(self, kind: str, rule_sets: list[RuleSet]) -> list[tuple[str, list[Ref]]]:
        if kind == "availability":
            return self._availability(rule_sets)
        return [self._one(rule_set) for rule_set in rule_sets]

    def _one(self, rule_set: RuleSet) -> tuple[str, list[Ref]]:
        match rule_set.kind:
            case "constraint":
                (code,) = rule_set.key
                found = next((c for c in self.ds.constraints if c.code == code), None)
                kind = f" ({found.type})" if found is not None else ""
                return f"constraint {code}{kind}", [Ref(kind="constraint", code=code)]
            case "pin":
                event, index = rule_set.key
                pin = [p for p in self.ds.pins if p.event == event][int(index)]
                parts = [p for p in (pin.day, pin.start_period) if p is not None]
                parts += list(pin.resources)
                where = " ".join(parts) if parts else "nothing"
                return f"pin of {event} to {where}", [
                    _event(event),
                    *(_resource(r) for r in pin.resources),
                ]
            case "starts":
                (event,) = rule_set.key
                duration = self.ctx.events[event].duration
                return f"{event} has no allowed start for duration {duration}", [_event(event)]
            case "requirement":
                event, ordinal = rule_set.key
                q = next(
                    r for r in self.ds.pooled if r.event == event and r.ordinal == int(ordinal)
                )
                return (
                    f'{event} needs {q.count} {self.label(q.resource_type)} matching "{q.filter}"',
                    [_event(event)],
                )
            case "no_overlap":
                (resource,) = rule_set.key
                return self._no_overlap(resource)
        return f"{rule_set.kind} {' '.join(rule_set.key)}", []

    def _no_overlap(self, resource: str) -> tuple[str, list[Ref]]:
        fixed = [
            code
            for code in self.ctx.events
            if resource in self.ctx.hierarchy.occupied_exclusive(code)
        ]
        parts = []
        if fixed:
            durations = {self.ctx.events[c].duration for c in fixed}
            if len(durations) == 1:
                parts.append(f"{len(fixed)} events of {durations.pop()} periods for {resource}")
            else:
                total = sum(self.ctx.events[c].duration for c in fixed)
                parts.append(f"{len(fixed)} events, {total} periods in all, for {resource}")
        parts.append(f"no_overlap({resource})")
        return "; ".join(parts), [_resource(resource)]

    def _availability(self, rule_sets: list[RuleSet]) -> list[tuple[str, list[Ref]]]:
        by_resource: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for rule_set in rule_sets:
            resource, day, period = rule_set.key
            by_resource[resource][day].add(period)
        found = []
        for resource in sorted(by_resource):
            when = self._when(by_resource[resource])
            found.append((f"{self.named(resource)} unavailable {when}", [_resource(resource)]))
        return found

    def _when(self, periods_by_day: dict[str, set[str]]) -> str:
        """For example `Tue–Sat`, `Mon P01–P03, P05` or `Mon P01; Wed P02`."""
        text_by_day = {day: self._periods(periods) for day, periods in periods_by_day.items()}
        runs: list[tuple[list[str], str]] = []
        for day in self.days:
            if day not in text_by_day:
                continue
            index = self.days.index(day)
            if (
                runs
                and runs[-1][1] == text_by_day[day]
                and self.days.index(runs[-1][0][-1]) == index - 1
            ):
                runs[-1][0].append(day)
            else:
                runs.append(([day], text_by_day[day]))
        parts = []
        for days, periods in runs:
            span = days[0] if len(days) == 1 else f"{days[0]}–{days[-1]}"
            parts.append(f"{span} {periods}".strip())
        return "; ".join(parts)

    def _periods(self, periods: set[str]) -> str:
        if set(self.usable) <= periods:
            return ""  # the whole day
        indexes = sorted(self.periods.index(p) for p in periods)
        ranges: list[list[int]] = []
        for i in indexes:
            if ranges and i == ranges[-1][-1] + 1:
                ranges[-1].append(i)
            else:
                ranges.append([i])
        return ", ".join(
            self.periods[r[0]] if len(r) == 1 else f"{self.periods[r[0]]}–{self.periods[r[-1]]}"
            for r in ranges
        )
