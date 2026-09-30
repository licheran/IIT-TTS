"""The state shared by the compile step and every constraint compiler (spec 05 section 4).

`CompileContext` owns the CP-SAT model and the variable maps. Constraint compilers
(`solver/constraints/<type>.py`) read the maps and add to the model. They never look at the
solver, and they never special-case a dataset.

In explain mode (spec 05 section 5) every hard rule set is guarded by an assumption literal from
`guard`, so the solver can say which rule sets conflict. Outside explain mode `guard` returns `None`
and the rules hold unconditionally. A compiler enforces a hard rule with
`only_enforce_if(guard)` when the guard is not `None`.
"""

from collections import defaultdict
from dataclasses import dataclass

from ortools.sat.python import cp_model

from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Event, Resource
from tts.core.selectors import Selectors
from tts.core.timegrid import TimeGrid

PooledKey = tuple[str, int, str]  # (event code, requirement ordinal, resource code)

RuleKind = str  # starts | availability | pin | no_overlap | requirement | constraint


@dataclass(frozen=True, slots=True, order=True)
class RuleSet:
    """One hard rule set that an explanation can switch off (spec 05 section 5).

    `key` identifies the instance: (event,) for `starts`, (resource, day, period) for
    `availability`, (event, index) for `pin`, (resource,) for `no_overlap`, (event, ordinal) for
    `requirement` and (code,) for `constraint`.
    """

    kind: RuleKind
    key: tuple[str, ...]


class CompileContext:
    """The model under construction, with the variables of every event."""

    def __init__(self, dataset: Dataset, explain: bool = False) -> None:
        self.dataset = dataset
        self.explain = explain
        self.guards: dict[RuleSet, cp_model.IntVar] = {}  # only filled in explain mode
        self.model = cp_model.CpModel()
        self.grid = TimeGrid(dataset.time)
        self.hierarchy = Hierarchy(dataset)
        self.selectors = Selectors(dataset, self.hierarchy)
        self.events: dict[str, Event] = {e.code: e for e in dataset.events}
        self.resources: dict[str, Resource] = {r.code: r for r in dataset.resources}

        self.domains: dict[str, tuple[int, ...]] = {}  # start slots left for each event
        self.start: dict[str, cp_model.IntVar] = {}
        self.iv: dict[str, cp_model.IntervalVar] = {}
        self.candidates: dict[
            tuple[str, int], tuple[str, ...]
        ] = {}  # (event, ordinal) -> resources
        self.use: dict[PooledKey, cp_model.IntVar] = {}
        self.oiv: dict[PooledKey, cp_model.IntervalVar] = {}
        self.problems: list[
            str
        ] = []  # reasons the model cannot have a solution, found while compiling
        self.warnings: list[str] = []

        self._occupants: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
        self._penalties: dict[str, cp_model.IntVar] = {}
        self._day_is: dict[tuple[str, int], cp_model.IntVar] = {}
        self._start_is: dict[str, dict[int, cp_model.IntVar]] = {}
        self._day_var: dict[str, cp_model.IntVar] = {}
        self._occupied: dict[tuple[str, int], cp_model.IntVar | None] = {}
        self._uses: dict[tuple[str, str], cp_model.IntVar] = {}
        self._fixed_occupants: dict[str, list[str]] | None = None

    def add_occupant(self, resource: str, interval: cp_model.IntervalVar) -> None:
        """Record that `interval` occupies `resource` (its no-overlap set is built later)."""
        self._occupants[resource].append(interval)

    def occupants(self, resource: str) -> list[cp_model.IntervalVar]:
        """The intervals of the events that occupy `resource`, fixed or pooled."""
        return self._occupants.get(resource, [])

    def occupied_resources(self) -> list[str]:
        return sorted(self._occupants)

    def penalty(self, name: str) -> cp_model.IntVar:
        """A non-negative penalty variable for one soft constraint instance (`p` in spec 04)."""
        found = self._penalties.get(name)
        if found is None:
            found = self.model.new_int_var(0, 10**9, f"penalty_{name}")
            self._penalties[name] = found
        return found

    @property
    def penalties(self) -> dict[str, cp_model.IntVar]:
        return dict(self._penalties)

    def day_is(self, event: str, day: int) -> cp_model.IntVar:
        """A literal that is true when `event` starts on day number `day` (built on first use)."""
        key = (event, day)
        found = self._day_is.get(key)
        if found is None:
            found = self.model.new_bool_var(f"day_{event}_{day}")
            first = day * self.grid.periods_per_day
            last = first + self.grid.periods_per_day - 1
            in_day = cp_model.Domain(first, last)
            self.model.add_linear_expression_in_domain(self.start[event], in_day).only_enforce_if(
                found
            )
            self.model.add_linear_expression_in_domain(
                self.start[event], in_day.complement()
            ).only_enforce_if(found.negated())
            self._day_is[key] = found
        return found

    # --- Building blocks for declared constraints (solver/constraints/*) ------------------------

    def start_is(self, event: str) -> dict[int, cp_model.IntVar]:
        """One literal per possible start of `event`, exactly one true (built on first use)."""
        found = self._start_is.get(event)
        if found is None:
            domain = self.domains[event]
            found = {t: self.model.new_bool_var(f"at_{event}_{t}") for t in domain}
            if found:
                self.model.add_exactly_one(found.values())
                self.model.add(self.start[event] == sum(t * lit for t, lit in found.items()))
            self._start_is[event] = found
        return found

    def covering(self, event: str, t: int) -> list[cp_model.IntVar]:
        """The start literals of `event` under which it covers slot `t` (at most one is true)."""
        duration = self.events[event].duration
        return [lit for s, lit in self.start_is(event).items() if s <= t < s + duration]

    def day_var(self, event: str) -> cp_model.IntVar:
        """The day number `event` starts on."""
        found = self._day_var.get(event)
        if found is None:
            found = self.model.new_int_var(0, max(self.grid.day_count - 1, 0), f"dayof_{event}")
            self.model.add_division_equality(found, self.start[event], self.grid.periods_per_day)
            self._day_var[event] = found
        return found

    def fixed_occupants(self, resource: str) -> list[str]:
        """Events that occupy `resource` whatever the solver picks (occupancy rule)."""
        if self._fixed_occupants is None:
            table: dict[str, list[str]] = defaultdict(list)
            for code in self.events:
                for r in self.hierarchy.occupied_resources(code):
                    table[r].append(code)
            self._fixed_occupants = dict(table)
        return self._fixed_occupants.get(resource, [])

    def uses(self, event: str, resource: str) -> cp_model.IntVar | None:
        """A literal true when `resource` is chosen for `event` by any pooled requirement."""
        key = (event, resource)
        if key in self._uses:
            return self._uses[key]
        literals = [lit for (e, _, r), lit in self.use.items() if e == event and r == resource]
        if not literals:
            return None
        if len(literals) == 1:
            found = literals[0]
        else:
            found = self.model.new_bool_var(f"uses_{event}_{resource}")
            self.model.add_max_equality(found, literals)
        self._uses[key] = found
        return found

    def occupying_events(self, resource: str) -> list[tuple[str, cp_model.IntVar | None]]:
        """Every event that can occupy `resource`, with the literal it needs (None: always)."""
        fixed = set(self.fixed_occupants(resource))
        found: list[tuple[str, cp_model.IntVar | None]] = [(e, None) for e in sorted(fixed)]
        pooled = sorted({e for (e, _, r) in self.use if r == resource and e not in fixed})
        for e in pooled:
            found.append((e, self.uses(e, resource)))
        return found

    def both(self, a: cp_model.IntVar, b: cp_model.IntVar, name: str) -> cp_model.IntVar:
        """A literal equal to `a and b`."""
        x = self.model.new_bool_var(name)
        self.model.add_implication(x, a)
        self.model.add_implication(x, b)
        self.model.add_bool_or([a.Not(), b.Not(), x])
        return x

    def occupied(self, resource: str, t: int) -> cp_model.IntVar | None:
        """A literal equal to "`resource` is occupied in slot `t`", or None if it never can be."""
        key = (resource, t)
        if key in self._occupied:
            return self._occupied[key]
        terms: list[cp_model.IntVar] = []
        for event, needs in self.occupying_events(resource):
            covering = self.covering(event, t)
            if not covering:
                continue
            if len(covering) == 1:
                covers = covering[0]
            else:
                covers = self.model.new_bool_var(f"cov_{event}_{t}")
                self.model.add(covers == sum(covering))
            terms.append(
                covers if needs is None else self.both(needs, covers, f"on_{event}_{resource}_{t}")
            )
        found: cp_model.IntVar | None
        if not terms:
            found = None
        elif len(terms) == 1:
            found = terms[0]
        else:
            found = self.model.new_bool_var(f"occ_{resource}_{t}")
            self.model.add_max_equality(found, terms)
        self._occupied[key] = found
        return found

    def guard(self, kind: RuleKind, *key: str) -> cp_model.IntVar | None:
        """The assumption literal of a rule set in explain mode, else `None` (always on)."""
        if not self.explain:
            return None
        rule_set = RuleSet(kind, tuple(key))
        found = self.guards.get(rule_set)
        if found is None:
            found = self.model.new_bool_var(f"guard_{kind}_{'_'.join(key)}")
            self.guards[rule_set] = found
        return found

    def constraint_guard(self, code: str) -> cp_model.IntVar | None:
        """The guard of a declared hard constraint instance (for `solver/constraints/*`)."""
        return self.guard("constraint", code)

    def declare_infeasible(self, reason: str, guard: cp_model.IntVar | None = None) -> None:
        """Note why no solution exists and make the model infeasible, without failing.

        With a guard, only the guard's rule set is made impossible (explain mode).
        """
        self.problems.append(reason)
        self.model.add_bool_or([] if guard is None else [guard.Not()])
