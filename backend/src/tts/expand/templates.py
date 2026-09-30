"""Templates to events (spec 05 section 2).

A template names the fixed resources an event serves through a selector (`targets`), plus fixed
resources every event gets (`fixed`), pooled requirements, a duration and a start pattern. Modes:

- `joint`: one event per session with every target;
- `each`: one event per session for each target (a preset may call it `per_group`);
- `batched`: targets sorted by code, cut into consecutive batches of `batch_size`; one event per
  batch and session.

Events are coded `<reference>-<kind>-<nn>` (the template code when there is no reference),
numbered 01, 02, ... per (reference, kind) in template-code order, skipping codes that hand-made
events use, so the same inputs always give the same codes.

Re-expanding replaces every event that has a `template` (with its fixed and pooled rows) and every
ordering constraint the expander made; hand-made events are never touched. Pins stay on events
that still exist. For each (before, after) kind pair given by the preset, each event of the
before kind gets a soft `order` constraint (weight 1) to every event of the after kind with the
same reference that shares a target.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from tts.core.hierarchy import Hierarchy
from tts.core.model import (
    Constraint,
    Dataset,
    Event,
    FixedRequirement,
    PooledRequirement,
    Template,
)
from tts.core.selectors import SelectorError, Selectors

MODES = ("joint", "each", "batched")
ORDER_PREFIX = "AUTO-ORDER:"


class ExpansionError(ValueError):
    """A template that cannot be expanded (unknown mode, bad selector, missing batch size)."""

    def __init__(self, template: str, problem: str) -> None:
        super().__init__(f'template "{template}": {problem}')
        self.template = template
        self.problem = problem


@dataclass(frozen=True, slots=True)
class ExpansionDiff:
    """Codes of template events added, changed and removed by an expansion."""

    added: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    orders_added: int = 0
    orders_removed: int = 0

    @property
    def empty(self) -> bool:
        return not (
            self.added or self.changed or self.removed or self.orders_added or self.orders_removed
        )


@dataclass(frozen=True, slots=True)
class Expansion:
    dataset: Dataset  # the dataset after expansion
    diff: ExpansionDiff
    problems: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class _Made:
    event: Event
    fixed: tuple[str, ...]
    pooled: tuple[PooledRequirement, ...]
    targets: frozenset[str]


def _batches(template: Template, targets: list[str]) -> list[list[str]]:
    if template.mode == "joint":
        return [targets] if targets else []
    if template.mode == "each":
        return [[t] for t in targets]
    if template.mode == "batched":
        if template.batch_size is None:
            raise ExpansionError(template.code, "mode batched needs a batch size")
        size = template.batch_size
        return [targets[i : i + size] for i in range(0, len(targets), size)]
    raise ExpansionError(
        template.code, f'unknown mode "{template.mode}" (known: {", ".join(MODES)})'
    )


def expand(
    dataset: Dataset,
    ordering: Sequence[tuple[str, str]] = (),
    unpooled_delivery: str | None = None,
) -> Expansion:
    """The dataset with its templates expanded, and what changed.

    `ordering` lists (before kind, after kind) pairs; `unpooled_delivery` is the delivery given to
    events of templates with no pooled requirement (for example `online`). A template that cannot
    be expanded is skipped and named in `problems`.
    """
    selectors = Selectors(dataset, Hierarchy(dataset))
    hand_made = [e for e in dataset.events if e.template is None]
    taken = {e.code for e in hand_made}
    numbers: dict[tuple[str, str], int] = defaultdict(int)
    made: list[_Made] = []
    problems: list[str] = []

    for template in dataset.templates:  # sorted by code
        if not template.active:
            continue
        try:
            targets = sorted(selectors.resources(template.targets))
            batches = _batches(template, targets)
        except SelectorError as error:
            problems.append(str(ExpansionError(template.code, f"targets: {error}")))
            continue
        except ExpansionError as error:
            problems.append(str(error))
            continue
        prefix = template.reference or template.code
        for _session in range(template.sessions_per_week):
            for batch in batches:
                code = _next_code(prefix, template.kind, numbers, taken)
                taken.add(code)
                event = Event(
                    code=code,
                    kind=template.kind,
                    duration=template.duration,
                    start_pattern=template.start_pattern,
                    reference=template.reference,
                    delivery=unpooled_delivery
                    if unpooled_delivery is not None and not template.pooled
                    else "in_person",
                    template=template.code,
                )
                pooled = tuple(
                    PooledRequirement(event=code, **spec.model_dump()) for spec in template.pooled
                )
                fixed = tuple(dict.fromkeys((*batch, *template.fixed)))
                made.append(_Made(event, fixed, pooled, frozenset(batch)))

    orders = _orders(made, ordering)
    new_events = {m.event.code for m in made}
    hand_codes = {e.code for e in hand_made}
    kept_events = hand_codes | new_events
    result = dataset.model_validate(
        {
            **dataset.model_dump(),
            "events": [*hand_made, *(m.event for m in made)],
            "fixed": [
                *(f for f in dataset.fixed if f.event in hand_codes),
                *(FixedRequirement(event=m.event.code, resource=r) for m in made for r in m.fixed),
            ],
            "pooled": [
                *(q for q in dataset.pooled if q.event in hand_codes),
                *(q for m in made for q in m.pooled),
            ],
            "constraints": [
                *(c for c in dataset.constraints if not c.code.startswith(ORDER_PREFIX)),
                *orders,
            ],
            "pins": [p for p in dataset.pins if p.event in kept_events],
        }
    )
    return Expansion(result, _diff(dataset, result, orders), tuple(problems))


def _next_code(prefix: str, kind: str, numbers: dict[tuple[str, str], int], taken: set[str]) -> str:
    while True:
        numbers[(prefix, kind)] += 1
        code = f"{prefix}-{kind}-{numbers[(prefix, kind)]:02d}"
        if code not in taken:
            return code


def _orders(made: Iterable[_Made], ordering: Sequence[tuple[str, str]]) -> list[Constraint]:
    by_reference: dict[str | None, list[_Made]] = defaultdict(list)
    for m in made:
        if m.event.reference is not None:
            by_reference[m.event.reference].append(m)
    found: list[Constraint] = []
    for before_kind, after_kind in ordering:
        for items in by_reference.values():
            firsts = [m for m in items if m.event.kind == before_kind]
            laters = [m for m in items if m.event.kind == after_kind]
            for a in firsts:
                for b in laters:
                    if a.targets & b.targets:
                        found.append(
                            Constraint(
                                code=f"{ORDER_PREFIX}{a.event.code}>{b.event.code}",
                                type="order",
                                scope="all",
                                params={"sequence": [a.event.code, b.event.code]},
                                hard=False,
                                weight=1,
                            )
                        )
    return found


def _signatures(ds: Dataset) -> dict[str, tuple[object, ...]]:
    """Each template event with its fixed resources and pooled requirements, by code."""
    fixed: dict[str, list[str]] = defaultdict(list)
    for f in ds.fixed:
        fixed[f.event].append(f.resource)
    pooled: dict[str, list[PooledRequirement]] = defaultdict(list)
    for q in ds.pooled:
        pooled[q.event].append(q)
    return {
        e.code: (e, tuple(sorted(fixed[e.code])), tuple(pooled[e.code]))
        for e in ds.events
        if e.template is not None
    }


def _diff(before: Dataset, after: Dataset, orders: list[Constraint]) -> ExpansionDiff:
    old_events, new_events = _signatures(before), _signatures(after)
    old, new = set(old_events), set(new_events)
    changed = sorted(c for c in old & new if old_events[c] != new_events[c])
    old_orders = {
        c.model_dump_json() for c in before.constraints if c.code.startswith(ORDER_PREFIX)
    }
    new_orders = {c.model_dump_json() for c in orders}
    return ExpansionDiff(
        added=tuple(sorted(new - old)),
        changed=tuple(changed),
        removed=tuple(sorted(old - new)),
        orders_added=len(new_orders - old_orders),
        orders_removed=len(old_orders - new_orders),
    )
