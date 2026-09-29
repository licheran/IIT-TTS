"""The state shared by the compile step and every constraint compiler (spec 05 section 4).

`CompileContext` owns the CP-SAT model and the variable maps. Constraint compilers
(`solver/constraints/<type>.py`) read the maps and add to the model. They never look at the
solver, and they never special-case a dataset.
"""

from collections import defaultdict

from ortools.sat.python import cp_model

from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Event, Resource
from tts.core.selectors import Selectors
from tts.core.timegrid import TimeGrid

PooledKey = tuple[str, int, str]  # (event code, requirement ordinal, resource code)


class CompileContext:
    """The model under construction, with the variables of every event."""

    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset
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

    def declare_infeasible(self, reason: str) -> None:
        """Note why no solution exists and make the model infeasible, without failing."""
        self.problems.append(reason)
        self.model.add_bool_or([])
