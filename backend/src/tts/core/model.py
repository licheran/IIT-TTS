"""Domain-neutral core model (spec 02).

Every model is frozen. Collections are tuples sorted into a canonical order so that two datasets
with the same content compare equal and hash the same, whatever order they were built in.
Local invariants are model validators. Global ones (cross-table references, exclusivity) are
reported by `Dataset.validate_invariants`, which collects every problem instead of stopping at
the first.
"""

import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from datetime import time
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

AttrValue = str | int | bool
Attributes = tuple[tuple[str, AttrValue], ...]
Tags = tuple[tuple[str, str], ...]
Code = Annotated[str, Field(min_length=1)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _pairs(value: object) -> object:
    """Accept a mapping and turn it into pairs sorted by key."""
    if isinstance(value, Mapping):
        return tuple(sorted(value.items()))
    if isinstance(value, list | tuple):
        return tuple(sorted(tuple(pair) for pair in value))
    return value


# --- Resources --------------------------------------------------------------------------------


class AttributeDef(_Frozen):
    name: Code
    kind: Literal["str", "int", "bool"] = "str"


class ResourceType(_Frozen):
    """A kind of resource. An exclusive type can be used by at most one event per period."""

    code: Code
    exclusive: bool = False
    has_capacity: bool = False
    attribute_schema: tuple[AttributeDef, ...] = ()

    @field_validator("attribute_schema")
    @classmethod
    def _sort_schema(cls, value: tuple[AttributeDef, ...]) -> tuple[AttributeDef, ...]:
        return tuple(sorted(value, key=lambda a: a.name))


class Resource(_Frozen):
    code: Code
    type: Code
    name: str = ""
    parent: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    attributes: Attributes = ()
    tags: Tags = ()

    _normalise = field_validator("attributes", "tags", mode="before")(_pairs)

    def tag(self, key: str) -> str | None:
        return dict(self.tags).get(key)

    def attribute(self, name: str) -> AttrValue | None:
        return dict(self.attributes).get(name)


class ReferenceType(_Frozen):
    """A non-schedulable lookup type."""

    code: Code
    name: str = ""
    attribute_schema: tuple[AttributeDef, ...] = ()


class Reference(_Frozen):
    code: Code
    type: Code
    name: str = ""
    attributes: Attributes = ()
    tags: Tags = ()

    _normalise = field_validator("attributes", "tags", mode="before")(_pairs)


# --- Time -------------------------------------------------------------------------------------


class Day(_Frozen):
    code: Code
    label: str = ""
    order: int


class Period(_Frozen):
    code: Code
    start: time
    end: time
    order: int
    is_break: bool = False

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.end <= self.start:
            raise ValueError(f"period {self.code}: end must be after start")
        return self


class StartPattern(_Frozen):
    """Where events of a given duration may start. `days=None` means every day."""

    code: Code
    duration: int = Field(ge=1)
    start_periods: tuple[Code, ...]
    days: tuple[Code, ...] | None = None


class TimeModel(_Frozen):
    days: tuple[Day, ...] = ()
    periods: tuple[Period, ...] = ()
    start_patterns: tuple[StartPattern, ...] = ()

    @field_validator("days")
    @classmethod
    def _sort_days(cls, value: tuple[Day, ...]) -> tuple[Day, ...]:
        return tuple(sorted(value, key=lambda d: (d.order, d.code)))

    @field_validator("periods")
    @classmethod
    def _sort_periods(cls, value: tuple[Period, ...]) -> tuple[Period, ...]:
        return tuple(sorted(value, key=lambda p: (p.order, p.code)))

    @field_validator("start_patterns")
    @classmethod
    def _sort_patterns(cls, value: tuple[StartPattern, ...]) -> tuple[StartPattern, ...]:
        return tuple(sorted(value, key=lambda s: s.code))

    @property
    def periods_per_day(self) -> int:
        return len(self.periods)


# --- Events and requirements ---------------------------------------------------------------------

_CAPACITY_RULE = re.compile(r"^sum_of_fixed:(?P<type>.+)$")


class CapacityRule(_Frozen):
    """How much capacity a pooled resource must offer. `none` means no requirement."""

    kind: Literal["none", "sum_of_fixed"] = "none"
    resource_type: str | None = None

    @model_validator(mode="after")
    def _type_matches_kind(self) -> Self:
        if (self.kind == "sum_of_fixed") != (self.resource_type is not None):
            raise ValueError("capacity rule: resource_type is required exactly for sum_of_fixed")
        return self

    @classmethod
    def parse(cls, text: str) -> Self:
        """Parse `none` (or empty) and `sum_of_fixed:<ResourceType>`."""
        text = text.strip()
        if text in ("", "none"):
            return cls()
        match = _CAPACITY_RULE.match(text)
        if match is None:
            raise ValueError(f'unknown capacity rule "{text}"')
        return cls(kind="sum_of_fixed", resource_type=match["type"].strip())

    def __str__(self) -> str:
        return "none" if self.kind == "none" else f"sum_of_fixed:{self.resource_type}"


class Event(_Frozen):
    code: Code
    kind: str
    duration: int = Field(ge=1)
    start_pattern: Code
    reference: str | None = None
    delivery: str = "in_person"
    tags: Tags = ()
    template: str | None = None
    demand: str | None = None

    _normalise = field_validator("tags", mode="before")(_pairs)


class FixedRequirement(_Frozen):
    """The event always occupies this resource."""

    event: Code
    resource: Code


class PooledSpec(_Frozen):
    """The solver picks `count` resources of `resource_type` that match `filter`.

    `ordinal` distinguishes several pooled requirements of one event.
    """

    resource_type: Code
    ordinal: int = Field(default=0, ge=0)
    count: int = Field(default=1, ge=1)
    filter: str = "all"
    capacity_rule: CapacityRule = CapacityRule()


class PooledRequirement(PooledSpec):
    event: Code


class Availability(_Frozen):
    resource: Code
    day: Code
    period: Code
    status: Literal["unavailable", "avoid"]


class Constraint(_Frozen):
    code: Code
    type: Code
    scope: str = "all"
    params: dict[str, JsonValue] = Field(default_factory=dict)
    hard: bool = True
    weight: int = Field(default=1, ge=0)
    active: bool = True


class Template(_Frozen):
    """A rule that expands into events (spec 05 section 2).

    `mode` is a free string here. The expander validates the values it supports.
    """

    code: Code
    kind: str
    mode: str
    reference: str | None = None
    targets: str = "all"
    batch_size: int | None = Field(default=None, ge=1)
    fixed: tuple[Code, ...] = ()
    pooled: tuple[PooledSpec, ...] = ()
    duration: int = Field(ge=1)
    start_pattern: Code
    sessions_per_week: int = Field(default=1, ge=1)
    active: bool = True


class Demand(_Frozen):
    """A rule the solver splits into events (ADR-0007, spec 02 section 1).

    The `participants` (exclusive resources of one type) are divided into `blocks` blocks of at
    most `max_participants`, with sizes differing by at most one. Each block attends `repeat`
    events of this kind, always with the same participants. Every event has this duration, start
    pattern, delivery and these pooled requirements. With no limit there is one block.
    """

    code: Code
    kind: str
    participants: tuple[Code, ...] = ()
    reference: str | None = None
    max_participants: int | None = Field(default=None, ge=1)
    repeat: int = Field(default=1, ge=1)
    duration: int = Field(ge=1)
    start_pattern: Code
    delivery: str = "in_person"
    pooled: tuple[PooledSpec, ...] = ()
    tags: Tags = ()

    _normalise = field_validator("tags", mode="before")(_pairs)

    @field_validator("participants")
    @classmethod
    def _sort_participants(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("a participant is listed twice")
        return tuple(sorted(value))

    @property
    def blocks(self) -> int:
        """How many blocks the participants are divided into (0 when there are none)."""
        count = len(self.participants)
        if count == 0:
            return 0
        if self.max_participants is None:
            return 1
        return -(-count // self.max_participants)


class Pin(_Frozen):
    """A fixed time and/or resources for one event."""

    event: Code
    day: str | None = None
    start_period: str | None = None
    resources: tuple[Code, ...] = ()
    source: Literal["user", "lock"] = "user"

    @field_validator("resources")
    @classmethod
    def _sort_resources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(value))


# --- Dataset ----------------------------------------------------------------------------------


def _sorted_by[T](items: Iterable[T], key: Callable[[T], tuple[str | int, ...]]) -> tuple[T, ...]:
    return tuple(sorted(items, key=key))


class ModelIssue(_Frozen):
    """One violated invariant found by `Dataset.validate_invariants`."""

    kind: str
    table: str
    key: str
    message: str


class Dataset(_Frozen):
    """The whole declared input of a solve."""

    preset: str = ""
    resource_types: tuple[ResourceType, ...] = ()
    resources: tuple[Resource, ...] = ()
    reference_types: tuple[ReferenceType, ...] = ()
    references: tuple[Reference, ...] = ()
    time: TimeModel = TimeModel()
    events: tuple[Event, ...] = ()
    fixed: tuple[FixedRequirement, ...] = ()
    pooled: tuple[PooledRequirement, ...] = ()
    availability: tuple[Availability, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    templates: tuple[Template, ...] = ()
    pins: tuple[Pin, ...] = ()
    demands: tuple[Demand, ...] = ()

    @field_validator("resource_types")
    @classmethod
    def _sort_resource_types(cls, v: tuple[ResourceType, ...]) -> tuple[ResourceType, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("resources")
    @classmethod
    def _sort_resources(cls, v: tuple[Resource, ...]) -> tuple[Resource, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("reference_types")
    @classmethod
    def _sort_reference_types(cls, v: tuple[ReferenceType, ...]) -> tuple[ReferenceType, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("references")
    @classmethod
    def _sort_references(cls, v: tuple[Reference, ...]) -> tuple[Reference, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("events")
    @classmethod
    def _sort_events(cls, v: tuple[Event, ...]) -> tuple[Event, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("fixed")
    @classmethod
    def _sort_fixed(cls, v: tuple[FixedRequirement, ...]) -> tuple[FixedRequirement, ...]:
        return _sorted_by(v, lambda x: (x.event, x.resource))

    @field_validator("pooled")
    @classmethod
    def _sort_pooled(cls, v: tuple[PooledRequirement, ...]) -> tuple[PooledRequirement, ...]:
        return _sorted_by(v, lambda x: (x.event, x.ordinal))

    @field_validator("availability")
    @classmethod
    def _sort_availability(cls, v: tuple[Availability, ...]) -> tuple[Availability, ...]:
        return _sorted_by(v, lambda x: (x.resource, x.day, x.period, x.status))

    @field_validator("constraints")
    @classmethod
    def _sort_constraints(cls, v: tuple[Constraint, ...]) -> tuple[Constraint, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("templates")
    @classmethod
    def _sort_templates(cls, v: tuple[Template, ...]) -> tuple[Template, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @field_validator("pins")
    @classmethod
    def _sort_pins(cls, v: tuple[Pin, ...]) -> tuple[Pin, ...]:
        return _sorted_by(v, lambda x: (x.event, x.source))

    @field_validator("demands")
    @classmethod
    def _sort_demands(cls, v: tuple[Demand, ...]) -> tuple[Demand, ...]:
        return _sorted_by(v, lambda x: (x.code,))

    @property
    def kind(self) -> Literal["configured", "hand_made"]:
        """`configured` when the events come from demands, else `hand_made` (spec 02 section 2)."""
        return "configured" if self.demands else "hand_made"

    def validate_invariants(self) -> list[ModelIssue]:
        """Every global invariant violation (spec 02 section 2). Empty means the dataset is sound.

        Named `validate_invariants` because `validate` is a deprecated Pydantic classmethod.
        """
        issues: list[ModelIssue] = []

        def add(kind: str, table: str, key: str, message: str) -> None:
            issues.append(ModelIssue(kind=kind, table=table, key=key, message=message))

        def duplicates(table: str, codes: Iterable[str]) -> None:
            seen: set[str] = set()
            for code in codes:
                if code in seen:
                    add("duplicate_code", table, code, f'duplicate code "{code}"')
                seen.add(code)

        def unknown(table: str, key: str, what: str, code: str, known: set[str]) -> None:
            if code not in known:
                add("unknown_reference", table, key, f'unknown {what} "{code}"')

        # Imported here because hierarchy imports this module.
        from tts.core.hierarchy import detect_cycles

        for cycle in detect_cycles(self):
            path = " → ".join((*cycle, cycle[0]))
            add("hierarchy_cycle", "resource", cycle[0], f"parent cycle: {path}")

        def check_attributes(
            table: str, key: str, attributes: Attributes, schema: tuple[AttributeDef, ...]
        ) -> None:
            kinds = {a.name: a.kind for a in schema}
            for name, value in attributes:
                if name not in kinds:
                    add("unknown_attribute", table, key, f'unknown attribute "{name}"')
                elif not _matches_kind(value, kinds[name]):
                    add("bad_attribute", table, key, f'attribute "{name}" is not {kinds[name]}')

        duplicates("resource_type", (t.code for t in self.resource_types))
        duplicates("resource", (r.code for r in self.resources))
        duplicates("reference_type", (t.code for t in self.reference_types))
        duplicates("reference", (r.code for r in self.references))
        duplicates("event", (e.code for e in self.events))
        duplicates("constraint", (c.code for c in self.constraints))
        duplicates("template", (t.code for t in self.templates))
        duplicates("demand", (d.code for d in self.demands))
        duplicates("day", (d.code for d in self.time.days))
        duplicates("period", (p.code for p in self.time.periods))
        duplicates("start_pattern", (s.code for s in self.time.start_patterns))

        types = {t.code: t for t in self.resource_types}
        resources = {r.code: r for r in self.resources}
        reference_types = {t.code: t for t in self.reference_types}
        events = {e.code for e in self.events}
        days = {d.code for d in self.time.days}
        periods = {p.code for p in self.time.periods}
        patterns = {s.code for s in self.time.start_patterns}
        references = {r.code for r in self.references}

        for r in self.resources:
            unknown("resource", r.code, "resource type", r.type, set(types))
            if r.parent is not None:
                unknown("resource", r.code, "parent", r.parent, set(resources))
            rtype = types.get(r.type)
            if rtype is not None:
                if r.capacity is not None and not rtype.has_capacity:
                    add("unexpected_capacity", "resource", r.code, f"type {r.type} has no capacity")
                check_attributes("resource", r.code, r.attributes, rtype.attribute_schema)

        for ref in self.references:
            unknown("reference", ref.code, "reference type", ref.type, set(reference_types))
            ref_type = reference_types.get(ref.type)
            if ref_type is not None:
                check_attributes("reference", ref.code, ref.attributes, ref_type.attribute_schema)

        for s in self.time.start_patterns:
            for p in s.start_periods:
                unknown("start_pattern", s.code, "period", p, periods)
            for d in s.days or ():
                unknown("start_pattern", s.code, "day", d, days)

        for e in self.events:
            unknown("event", e.code, "start pattern", e.start_pattern, patterns)
            if e.reference is not None:
                unknown("event", e.code, "reference", e.reference, references)

        for f in self.fixed:
            key = f"{f.event}/{f.resource}"
            unknown("fixed", key, "event", f.event, events)
            unknown("fixed", key, "resource", f.resource, set(resources))

        seen_pooled: set[tuple[str, int]] = set()
        for q in self.pooled:
            key = f"{q.event}#{q.ordinal}"
            unknown("pooled", key, "event", q.event, events)
            if (q.event, q.ordinal) in seen_pooled:
                add("duplicate_code", "pooled", key, f'duplicate requirement "{key}"')
            seen_pooled.add((q.event, q.ordinal))
            rtype = types.get(q.resource_type)
            if rtype is None:
                add(
                    "unknown_reference", "pooled", key, f'unknown resource type "{q.resource_type}"'
                )
            elif not rtype.exclusive:
                add(
                    "pooled_not_exclusive",
                    "pooled",
                    key,
                    f"type {q.resource_type} is not exclusive",
                )
            if q.capacity_rule.resource_type is not None:
                unknown("pooled", key, "resource type", q.capacity_rule.resource_type, set(types))

        for a in self.availability:
            key = f"{a.resource}/{a.day}/{a.period}"
            unknown("availability", key, "resource", a.resource, set(resources))
            unknown("availability", key, "day", a.day, days)
            unknown("availability", key, "period", a.period, periods)

        for pin in self.pins:
            unknown("pin", pin.event, "event", pin.event, events)
            if pin.day is not None:
                unknown("pin", pin.event, "day", pin.day, days)
            if pin.start_period is not None:
                unknown("pin", pin.event, "period", pin.start_period, periods)
            for code in pin.resources:
                unknown("pin", pin.event, "resource", code, set(resources))

        for t in self.templates:
            unknown("template", t.code, "start pattern", t.start_pattern, patterns)
            for code in t.fixed:
                unknown("template", t.code, "resource", code, set(resources))

        self._demand_issues(add, unknown, types, resources, patterns, references)
        return issues

    def _demand_issues(
        self,
        add: Callable[[str, str, str, str], None],
        unknown: Callable[[str, str, str, str, set[str]], None],
        types: dict[str, ResourceType],
        resources: dict[str, Resource],
        patterns: set[str],
        references: set[str],
    ) -> None:
        """Invariants 6 and 7 of spec 02 (demands and their edits)."""
        demand_codes = {d.code for d in self.demands}
        participant_type: dict[str, str | None] = {}
        for d in self.demands:
            unknown("demand", d.code, "start pattern", d.start_pattern, patterns)
            if d.reference is not None:
                unknown("demand", d.code, "reference", d.reference, references)
            for code in d.participants:
                unknown("demand", d.code, "participant", code, set(resources))
            known = [code for code in d.participants if code in resources]
            for code in known:
                found = types.get(resources[code].type)
                if found is not None and not found.exclusive:
                    add(
                        "demand_participant_not_exclusive",
                        "demand",
                        d.code,
                        f'participant "{code}" is not of an exclusive type',
                    )
            found_types = {resources[code].type for code in known}
            if len(found_types) > 1:
                add(
                    "demand_mixed_participants",
                    "demand",
                    d.code,
                    "participants are of different types: " + ", ".join(sorted(found_types)),
                )
            participant_type[d.code] = next(iter(found_types)) if len(found_types) == 1 else None
            for spec in d.pooled:
                rtype = types.get(spec.resource_type)
                if rtype is None:
                    add(
                        "unknown_reference",
                        "demand",
                        d.code,
                        f'unknown resource type "{spec.resource_type}"',
                    )
                elif not rtype.exclusive:
                    add(
                        "pooled_not_exclusive",
                        "demand",
                        d.code,
                        f"type {spec.resource_type} is not exclusive",
                    )

        declared: dict[str, list[str]] = defaultdict(list)
        for f in self.fixed:
            declared[f.event].append(f.resource)
        owners = {d.code: d for d in self.demands}
        for e in self.events:
            if e.demand is None:
                if self.demands:
                    add(
                        "mixed_dataset",
                        "event",
                        e.code,
                        "a dataset with demands cannot also have events without a demand",
                    )
                continue
            unknown("event", e.code, "demand", e.demand, demand_codes)
            owner = owners.get(e.demand)
            if owner is None:
                continue
            kind = participant_type.get(owner.code)
            taken = [
                code
                for code in declared.get(e.code, ())
                if code in resources and resources[code].type == kind
            ]
            for code in taken:
                if code not in owner.participants:
                    add(
                        "edit_outside_demand",
                        "event",
                        e.code,
                        f'"{code}" is not a participant of demand "{owner.code}"',
                    )
            limit = owner.max_participants
            if limit is not None and len(taken) > limit:
                add(
                    "edit_too_large",
                    "event",
                    e.code,
                    f"{len(taken)} participants, more than the limit of {limit} of demand "
                    f'"{owner.code}"',
                )


def _matches_kind(value: AttrValue, kind: str) -> bool:
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, str)


# --- Results and violations -----------------------------------------------------------------------


class PooledChoice(_Frozen):
    """The resources chosen for one pooled requirement (identified by its ordinal)."""

    ordinal: int = Field(default=0, ge=0)
    resources: tuple[Code, ...]

    @field_validator("resources")
    @classmethod
    def _sort_resources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(value))


class Assignment(_Frozen):
    """A run's placement of one event."""

    event: Code
    day: Code
    start_period: Code
    chosen: tuple[PooledChoice, ...] = ()

    @field_validator("chosen")
    @classmethod
    def _sort_chosen(cls, value: tuple[PooledChoice, ...]) -> tuple[PooledChoice, ...]:
        return tuple(sorted(value, key=lambda c: c.ordinal))


class Result(_Frozen):
    """The assignments of one solve. Events without an assignment are unplaced."""

    assignments: tuple[Assignment, ...] = ()

    @field_validator("assignments")
    @classmethod
    def _sort_assignments(cls, value: tuple[Assignment, ...]) -> tuple[Assignment, ...]:
        return tuple(sorted(value, key=lambda a: a.event))


class Ref(_Frozen):
    """A pointer to something a violation is about, for messages and UI links."""

    kind: Literal["event", "resource", "slot", "constraint"]
    code: str


class Violation(_Frozen):
    """One broken rule.

    `code` is the rule's type (for example `no_overlap`). `constraint_code` is its catalogue code
    (`H1`) for implicit rules, or the declared constraint's own code. `severity` is `hard` (the
    result is invalid), `soft` (a preference with a penalty) or `warning`.
    """

    code: str
    constraint_code: str
    severity: Literal["hard", "soft", "warning"]
    penalty: int = Field(default=0, ge=0)
    refs: tuple[Ref, ...] = ()
    message: str = ""


class Diagnostic(_Frozen):
    """A finding about a whole run rather than one placement (spec 05 section 5).

    `kind` is for example `infeasible_core`. `details` holds one line per part of the finding (for
    an infeasible core, one per conflicting rule group). `minimal` is false when an explanation
    ran out of time before it could prove that no part can be dropped.
    """

    kind: str
    severity: Literal["error", "warning"] = "error"
    message: str
    refs: tuple[Ref, ...] = ()
    details: tuple[str, ...] = ()
    minimal: bool = True
