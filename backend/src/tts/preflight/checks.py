"""Pre-flight checks (spec 05 section 3): cheap tests that find a hopeless dataset before solving.

`run_preflight` returns every issue. An `error` means no timetable can exist (or the dataset is not
sound enough to solve), so the pipeline stops. A `warning` is a likely mistake that does not block.

The checks only use the dataset. Each is a necessary condition, so an error is never a false alarm:
for example, a resource that needs more periods than it has can never be scheduled. The converse
does not hold, and a dataset with no issues can still be infeasible (the explanation in
`solver/explain.py` covers that case).

Messages name entities by code. Words for resource types come from the `label` function passed in,
so this package stays free of any domain vocabulary.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from tts.core.candidates import Candidates
from tts.core.constraints.catalogue import CATALOGUE
from tts.core.constraints.declared import InvalidConstraintError, parse_instance
from tts.core.constraints.registry import declared_type
from tts.core.demands import created_event
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Demand, ModelIssue, PooledSpec, Ref
from tts.core.selectors import CodeClause, SelectorError, Selectors, UsesClause, parse
from tts.core.timegrid import TimeGrid, TimeGridError

Severity = Literal["error", "warning"]
Labeller = Callable[[str], str]


class Issue(BaseModel):
    """One finding. `kind` names the check, `refs` point at the entities it is about."""

    model_config = ConfigDict(frozen=True)

    severity: Severity
    kind: str
    message: str
    refs: tuple[Ref, ...] = ()


def has_errors(issues: Iterable[Issue]) -> bool:
    """True if any issue blocks the solve."""
    return any(i.severity == "error" for i in issues)


def run_preflight(dataset: Dataset, label: Labeller = str) -> list[Issue]:
    """Every pre-flight issue of `dataset`, errors first, then by kind and message.

    A dataset that breaks an invariant (an unknown reference, a hierarchy cycle) gets only those
    issues, because the other checks assume a sound dataset.
    """
    invariants = _invariant_issues(dataset)
    if invariants:
        return _ordered(invariants)
    return _ordered(_Checker(dataset, label).run())


def _ordered(issues: Iterable[Issue]) -> list[Issue]:
    return sorted(issues, key=lambda i: (i.severity != "error", i.kind, i.message))


def _event_ref(code: str) -> Ref:
    return Ref(kind="event", code=code)


def _resource_ref(code: str) -> Ref:
    return Ref(kind="resource", code=code)


def _constraint_ref(code: str) -> Ref:
    return Ref(kind="constraint", code=code)


# --- Unresolved references, cycles and the other invariants -----------------------------------


def _invariant_issues(dataset: Dataset) -> list[Issue]:
    found = dataset.validate_invariants()
    return [
        Issue(
            severity="error",
            kind=issue.kind,
            message=f'{issue.table} "{issue.key}": {issue.message}',
            refs=_invariant_refs(dataset, issue),
        )
        for issue in found
    ]


def _invariant_refs(dataset: Dataset, issue: ModelIssue) -> tuple[Ref, ...]:
    """The entities an invariant issue is about. Keys are looked up, never parsed, because codes
    may contain the separators the keys use."""
    match issue.table:
        case "resource":
            return (_resource_ref(issue.key),)
        case "event" | "pin":
            return (_event_ref(issue.key),)
        case "constraint":
            return (_constraint_ref(issue.key),)
        case "availability":
            for a in dataset.availability:
                if f"{a.resource}/{a.day}/{a.period}" == issue.key:
                    return (_resource_ref(a.resource),)
        case "pooled":
            for q in dataset.pooled:
                if f"{q.event}#{q.ordinal}" == issue.key:
                    return (_event_ref(q.event),)
        case "fixed":
            for f in dataset.fixed:
                if f"{f.event}/{f.resource}" == issue.key:
                    return (_event_ref(f.event), _resource_ref(f.resource))
    return ()


# --- The checks ------------------------------------------------------------------------------


class _Checker:
    """Runs every check of one dataset, building the indexes once."""

    def __init__(self, dataset: Dataset, label: Labeller) -> None:
        self.ds = dataset
        self.label = label
        self.grid = TimeGrid(dataset.time)
        self.hierarchy = Hierarchy(dataset)
        self.selectors = Selectors(dataset, self.hierarchy)
        self.candidates = Candidates(dataset, self.hierarchy, self.selectors)
        self.events = {e.code: e for e in dataset.events}
        self.resources = {r.code: r for r in dataset.resources}
        self.issues: list[Issue] = []

        breaks = {p.code for p in dataset.time.periods if p.is_break}
        self._usable_per_day = sum(not p.is_break for p in dataset.time.periods)
        self._blocked: dict[str, set[tuple[str, str]]] = defaultdict(set)
        for a in dataset.availability:
            if a.status == "unavailable" and a.period not in breaks:
                self._blocked[a.resource].add((a.day, a.period))

        self._candidate_sets: dict[tuple[str, int], tuple[str, ...]] = {}
        self._demand_sets: dict[tuple[str, int], tuple[str, ...]] = {}
        self._failed_types: set[str] = set()

    def run(self) -> list[Issue]:
        self._nothing_to_schedule()
        self._start_domains()
        self._pooled_candidates()
        self._demand_candidates()
        self._over_demand()
        self._pooled_pressure()
        self._conflicting_pins()
        self._unused_resources()
        self._constraint_scopes()
        self._demand_scopes()
        self._constraint_params()
        return self.issues

    def add(self, severity: Severity, kind: str, message: str, *refs: Ref) -> None:
        self.issues.append(Issue(severity=severity, kind=kind, message=message, refs=refs))

    def available(self, resource: str) -> int:
        """Periods a resource can be occupied in: not a break, not marked unavailable."""
        total = len(self.ds.time.days) * self._usable_per_day
        return total - len(self._blocked.get(resource, ()))

    # Nothing to schedule
    def _nothing_to_schedule(self) -> None:
        if not self.ds.events and not self.ds.demands:
            self.add(
                "warning",
                "nothing_to_schedule",
                "No demands and no events: the timetable would be empty",
            )

    # Empty start domain
    def _start_domains(self) -> None:
        for d in self.ds.demands:
            if not d.participants:
                continue
            try:
                starts = self.grid.allowed_starts(created_event(d, d.code))
            except TimeGridError:
                continue  # an unknown pattern is reported as an invariant issue
            if not starts:
                self.add(
                    "error",
                    "empty_start_domain",
                    f"{d.code}: no allowed start fits duration {d.duration}",
                )
        for event in self.ds.events:
            try:
                starts = self.grid.allowed_starts(event)
            except TimeGridError:
                continue  # an unknown pattern is reported as an invariant issue
            if not starts:
                self.add(
                    "error",
                    "empty_start_domain",
                    f"{event.code}: no allowed start fits duration {event.duration}",
                    _event_ref(event.code),
                )

    # No candidate pooled resource
    def _pooled_candidates(self) -> None:
        for q in self.ds.pooled:
            key = f"{q.event}#{q.ordinal}"
            try:
                found = self.candidates.of(q)
            except SelectorError as error:
                self._failed_types.add(q.resource_type)
                self.add(
                    "error",
                    "invalid_selector",
                    f'{key}: filter "{q.filter}": {error.message}',
                    _event_ref(q.event),
                )
                continue
            self._candidate_sets[(q.event, q.ordinal)] = found.codes
            if len(found.codes) >= q.count:
                continue
            kind = self.label(q.resource_type)
            capacity = f" with capacity ≥ {found.needed}" if found.needed else ""
            if not found.codes:
                message = f'{q.event}: no {kind} matching "{q.filter}"{capacity}'
            else:
                message = (
                    f"{q.event}: needs {q.count} {kind} but only {len(found.codes)} "
                    f'match "{q.filter}"{capacity}'
                )
            self.add("error", "no_candidate", message, _event_ref(q.event))

    # Pooled requirements of demands: candidates for the block that cannot be avoided
    def _demand_candidates(self) -> None:
        for d in self.ds.demands:
            if not d.participants:
                self.add(
                    "warning", "empty_demand", f"{d.code}: no participants, nothing to schedule"
                )
                continue
            for spec in d.pooled:
                self._demand_spec(d, spec)

    def _unavoidable_block(self, d: Demand, spec: PooledSpec) -> int:
        """The capacity some block of the demand needs whatever the split: the biggest
        participant alone, or an even share of the total when that is more."""
        rule = spec.capacity_rule
        if rule.resource_type is None:
            return 0
        sizes = [
            self.resources[p].capacity or 0
            for p in d.participants
            if p in self.resources and self.resources[p].type == rule.resource_type
        ]
        blocks = d.blocks
        if not sizes or blocks == 0:
            return 0
        return max(max(sizes), -(-sum(sizes) // blocks))

    def _demand_spec(self, d: Demand, spec: PooledSpec) -> None:
        key = f"{d.code}#{spec.ordinal}"
        try:
            matching = self.selectors.resources(spec.filter)
        except SelectorError as error:
            self._failed_types.add(spec.resource_type)
            self.add("error", "invalid_selector", f'{key}: filter "{spec.filter}": {error.message}')
            return
        needed = self._unavoidable_block(d, spec)
        codes = tuple(
            r.code
            for r in self.ds.resources
            if r.type == spec.resource_type and r.code in matching and (r.capacity or 0) >= needed
        )
        self._demand_sets[(d.code, spec.ordinal)] = codes
        if len(codes) >= spec.count:
            return
        kind = self.label(spec.resource_type)
        capacity = f" with capacity ≥ {needed}" if needed else ""
        if not codes:
            message = f'{d.code}: no {kind} matching "{spec.filter}"{capacity}'
        else:
            message = (
                f"{d.code}: needs {spec.count} {kind} but only {len(codes)} "
                f'match "{spec.filter}"{capacity}'
            )
        self.add("error", "no_candidate", message)

    def _occupied_by_participants(self, d: Demand) -> set[str]:
        found: set[str] = set()
        for p in d.participants:
            if p in self.resources:
                found.add(p)
                found |= self.hierarchy.exclusive_descendants(p)
        return found

    # Resource over-demand
    def _over_demand(self) -> None:
        demand: dict[str, int] = defaultdict(int)
        owners = {d.code: d for d in self.ds.demands}
        taken = {code: self._occupied_by_participants(d) for code, d in owners.items()}
        for event in self.ds.events:
            skip = taken.get(event.demand or "", set())  # an edit is counted with its demand
            for code in self.hierarchy.occupied_exclusive(event.code):
                if code not in skip:
                    demand[code] += event.duration
        for d in self.ds.demands:
            for code in taken[d.code]:
                demand[code] += d.repeat * d.duration
        for code in sorted(demand):
            available = self.available(code)
            if demand[code] > available:
                kind = self.label(self.resources[code].type)
                self.add(
                    "error",
                    "over_demand",
                    f"{kind} {code}: needs {demand[code]} periods, {available} available",
                    _resource_ref(code),
                )

    # Pooled pressure
    def _pooled_pressure(self) -> None:
        supplying_by: dict[tuple[str, str], set[str]] = defaultdict(set)
        needed_by: dict[tuple[str, str], int] = defaultdict(int)
        for q in self.ds.pooled:
            key = (q.resource_type, q.filter)
            supplying_by[key].update(self._candidate_sets.get((q.event, q.ordinal), ()))
            needed_by[key] += self.events[q.event].duration * q.count
        for d in self.ds.demands:
            for spec in d.pooled:
                key = (spec.resource_type, spec.filter)
                supplying_by[key].update(self._demand_sets.get((d.code, spec.ordinal), ()))
                needed_by[key] += d.blocks * d.repeat * d.duration * spec.count
        for (resource_type, selector), supplying in sorted(supplying_by.items()):
            demand = needed_by[(resource_type, selector)]
            supply = sum(self.available(code) for code in supplying)
            if supplying and demand > supply:
                self.add(
                    "warning",
                    "pooled_pressure",
                    f"{self.label(resource_type)} {selector}: "
                    f"{demand} periods needed, {supply} available",
                )

    # Conflicting pins
    def _conflicting_pins(self) -> None:
        pinned: dict[str, list[tuple[str | None, str | None, tuple[str, ...]]]] = defaultdict(list)
        for pin in self.ds.pins:
            pinned[pin.event].append((pin.day, pin.start_period, pin.resources))

        by_resource: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
        for event_code, pins in pinned.items():
            days = {d for d, _, _ in pins if d is not None}
            periods = {p for _, p, _ in pins if p is not None}
            if len(days) != 1 or len(periods) != 1:
                continue  # no exact time, or pins that disagree with each other
            start = self.grid.slot(next(iter(days)), next(iter(periods)))
            chosen = {r for _, _, resources in pins for r in resources}
            duration = self.events[event_code].duration
            for code in self.hierarchy.occupied_exclusive(event_code, chosen):
                by_resource[code].append((start, start + duration, event_code))

        for code in sorted(by_resource):
            cluster: list[tuple[int, int, str]] = []  # pins whose times overlap one another
            reach = 0
            for entry in sorted(by_resource[code]):
                if cluster and entry[0] >= reach:
                    self._report_pins(code, cluster)
                    cluster, reach = [], 0
                cluster.append(entry)
                reach = max(reach, entry[1])
            self._report_pins(code, cluster)

    def _report_pins(self, resource: str, cluster: list[tuple[int, int, str]]) -> None:
        if len(cluster) < 2:
            return
        first = cluster[0][0]
        day, period = self.grid.codes(first)
        same = all(start == first for start, _, _ in cluster)
        when = f"on {day} {period}" if same else f"with overlapping times from {day} {period}"
        events = sorted(event for _, _, event in cluster)
        self.add(
            "error",
            "conflicting_pins",
            f"Pins: {len(cluster)} activities pinned to {resource} {when}",
            _resource_ref(resource),
            *(_event_ref(e) for e in events),
            Ref(kind="slot", code=f"{day}/{period}"),
        )

    # Unused resource
    def _unused_resources(self) -> None:
        pooled_types = {q.resource_type for q in self.ds.pooled} | {
            spec.resource_type for d in self.ds.demands for spec in d.pooled
        }
        pooled_types -= self._failed_types
        used = {code for codes in self._candidate_sets.values() for code in codes}
        used |= {code for codes in self._demand_sets.values() for code in codes}
        for resource in self.ds.resources:
            if resource.type in pooled_types and resource.code not in used:
                self.add(
                    "warning",
                    "unused_resource",
                    f"{self.label(resource.type)} {resource.code} is never a candidate",
                    _resource_ref(resource.code),
                )

    # Soft constraint on an empty scope
    def _constraint_scopes(self) -> None:
        for c in self.ds.constraints:
            target = CATALOGUE.get(c.type)
            if not c.active or c.hard or target is None:
                continue
            try:
                matched = (
                    self.selectors.resources(c.scope)
                    if target == "resource"
                    else self.selectors.events(c.scope)
                )
            except SelectorError as error:
                self.add(
                    "error",
                    "invalid_selector",
                    f'{c.code}: scope "{c.scope}": {error.message}',
                    _constraint_ref(c.code),
                )
                continue
            if not matched:
                self.add(
                    "warning",
                    "empty_scope",
                    f"{c.code}: scope matches nothing",
                    _constraint_ref(c.code),
                )

    # Scopes that depend on the solver's grouping (spec 04 section 5)
    def _demand_scopes(self) -> None:
        if not self.ds.demands:
            return
        for c in self.ds.constraints:
            if not c.active or CATALOGUE.get(c.type) != "event":
                continue
            try:
                clauses = parse(c.scope).clauses
                matched = self.selectors.events(c.scope)
            except SelectorError:
                continue  # reported by the scope checks
            if any(isinstance(clause, CodeClause) for clause in clauses) and not matched:
                self.add(
                    "warning",
                    "code_scope_with_demands",
                    f"{c.code}: scope names no declared event, while demands make events with "
                    "codes only after solving",
                    _constraint_ref(c.code),
                )
            if any(isinstance(clause, UsesClause) for clause in clauses):
                if c.hard:
                    self.add(
                        "error",
                        "uses_scope_unsupported",
                        f"{c.code}: a hard rule with a uses: scope cannot be enforced on "
                        "events the solver creates",
                        _constraint_ref(c.code),
                    )
                else:
                    self.add(
                        "warning",
                        "uses_scope_declared_only",
                        f"{c.code}: only declared events are optimised for this scope; the "
                        "score is still exact",
                        _constraint_ref(c.code),
                    )

    # Declared constraint with invalid parameters or references
    def _constraint_params(self) -> None:
        for c in self.ds.constraints:
            implementation = declared_type(c.type)
            if not c.active or implementation is None:
                continue
            try:
                instance = parse_instance(self.ds, c, implementation.Params, self.selectors)
            except InvalidConstraintError as error:
                if not error.problem.startswith("scope:"):  # scopes are reported above
                    self.add("error", "invalid_constraint", str(error), _constraint_ref(c.code))
                continue
            check = getattr(implementation, "problems", None)
            for problem in check(self.ds, instance) if check is not None else ():
                self.add(
                    "error",
                    "invalid_constraint",
                    f'constraint "{c.code}" ({c.type}): {problem}',
                    _constraint_ref(c.code),
                )
