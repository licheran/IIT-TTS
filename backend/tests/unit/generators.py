"""Hypothesis strategies for random academic datasets that the workbook can express."""

from datetime import time
from typing import Any

from hypothesis import strategies as st

from tts.core.constraints.catalogue import CATALOGUE
from tts.core.model import (
    Availability,
    CapacityRule,
    Constraint,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    Pin,
    PooledRequirement,
    PooledSpec,
    Reference,
    Resource,
    StartPattern,
    Template,
    TimeModel,
)
from tts.core.selectors import Selector, TagClause, UnderClause, format_selector
from tts.presets.academic_weekly.preset import PRESET

# Characters that stress quoting and trimming but are legal in codes and text.
_ALPHABET = "abcXYZ019 /-[]().,:_é"
_words = st.text(_ALPHABET, min_size=1, max_size=6).map(str.strip).filter(bool)
_plain = st.text("abcxyz019_", min_size=1, max_size=4)


def _unique(draw: Any, prefix: str, count: int) -> list[str]:
    """`count` distinct codes that start with `prefix` and end in awkward text."""
    suffixes = draw(st.lists(_words, min_size=count, max_size=count))
    return [f"{prefix}{i}{s}" for i, s in enumerate(suffixes)]


def _tags(draw: Any, blocked: tuple[str, ...] = ()) -> dict[str, str]:
    keys = draw(st.lists(_plain.filter(lambda k: k not in blocked), max_size=2, unique=True))
    return {k: draw(_words) for k in keys}


def _some(draw: Any, items: list[str], minimum: int = 0, maximum: int | None = None) -> list[str]:
    """A subset of `items` in a random order (no repeats)."""
    if not items:
        return []
    return draw(
        st.lists(
            st.sampled_from(items), min_size=min(minimum, len(items)), max_size=maximum, unique=True
        )
    )


@st.composite
def academic_datasets(draw: Any) -> Dataset:
    days = _unique(draw, "D", draw(st.integers(1, 3)))
    periods = _unique(draw, "P", draw(st.integers(2, 5)))
    breaks = draw(st.lists(st.booleans(), min_size=len(periods), max_size=len(periods)))
    patterns = []
    for code in _unique(draw, "S", draw(st.integers(1, 2))):
        patterns.append(
            StartPattern(
                code=code,
                duration=draw(st.integers(1, 2)),
                start_periods=tuple(_some(draw, periods, minimum=1)),
                days=draw(
                    st.one_of(st.none(), st.builds(tuple, st.just(_some(draw, days, minimum=1))))
                ),
            )
        )
    time_model = TimeModel(
        days=tuple(
            Day(code=c, label=draw(st.one_of(st.just(""), _words)), order=i + 1)
            for i, c in enumerate(days)
        ),
        periods=tuple(
            Period(code=c, start=time(6 + i), end=time(7 + i), order=i + 1, is_break=breaks[i])
            for i, c in enumerate(periods)
        ),
        start_patterns=tuple(patterns),
    )

    resources: list[Resource] = []

    def add(code: str, kind: str, **kwargs: Any) -> None:
        resources.append(
            Resource(code=code, type=kind, name=draw(st.one_of(st.just(""), _words)), **kwargs)
        )

    universities = _unique(draw, "U", draw(st.integers(0, 1)))
    for c in universities:
        add(c, "University", tags=_tags(draw))
    levels = _unique(draw, "L", draw(st.integers(0, 2)))
    for c in levels:
        add(
            c,
            "Level",
            parent=draw(st.one_of(st.none(), *map(st.just, universities))),
            tags=_tags(draw),
        )
    programmes = _unique(draw, "PR", draw(st.integers(1, 2)))
    for c in programmes:
        add(
            c,
            "Programme",
            parent=draw(st.one_of(st.none(), *map(st.just, levels))),
            tags=_tags(draw),
        )
    groups = _unique(draw, "G", draw(st.integers(1, 4)))
    for i, c in enumerate(groups):
        parent = draw(st.sampled_from([*programmes, *groups[:i]]))
        add(
            c,
            "StudentGroup",
            parent=parent,
            capacity=draw(st.one_of(st.none(), st.integers(0, 60))),
            tags=_tags(draw),
        )
    teachers = _unique(draw, "T", draw(st.integers(1, 3)))
    for c in teachers:
        add(c, "Teacher", tags=_tags(draw))
    campuses = _unique(draw, "C", draw(st.integers(0, 1)))
    for c in campuses:
        add(c, "Campus", tags=_tags(draw))
    buildings = _unique(draw, "B", draw(st.integers(0, 2)))
    for c in buildings:
        abbreviation = draw(st.one_of(st.none(), _words))
        add(
            c,
            "Building",
            parent=draw(st.one_of(st.none(), *map(st.just, campuses))),
            attributes={} if abbreviation is None else {"abbreviation": abbreviation},
            tags=_tags(draw),
        )
    room_types = draw(st.lists(_words, min_size=1, max_size=2, unique=True))
    rooms = _unique(draw, "R", draw(st.integers(0, 3)))
    for c in rooms:
        add(
            c,
            "Room",
            parent=draw(st.one_of(st.none(), *map(st.just, buildings))),
            capacity=draw(st.one_of(st.none(), st.integers(0, 300))),
            tags={
                **_tags(draw, blocked=("room_type",)),
                "room_type": draw(st.sampled_from(room_types)),
            },
        )

    references = []
    for c in _unique(draw, "M", draw(st.integers(0, 2))):
        attributes = {}
        if levels and draw(st.booleans()):
            attributes["level"] = draw(st.sampled_from(levels))
        if draw(st.booleans()):
            attributes["programme"] = draw(st.sampled_from(programmes))
        references.append(
            Reference(
                code=c,
                type="Module",
                name=draw(st.one_of(st.just(""), _words)),
                attributes=attributes,
                tags=_tags(draw),
            )
        )
    module_codes = [r.code for r in references]

    def room_spec(kind: str) -> PooledSpec | None:
        if not rooms:
            return None
        selector = Selector((TagClause("room_type", kind),))
        return PooledSpec(
            resource_type="Room",
            filter=format_selector(selector),
            capacity_rule=CapacityRule.parse("sum_of_fixed:StudentGroup"),
        )

    templates = []
    if module_codes:
        for c in _unique(draw, "TP", draw(st.integers(0, 2))):
            mode = draw(st.sampled_from(["joint", "each", "batched"]))  # core names
            spec = room_spec(draw(st.sampled_from(room_types))) if draw(st.booleans()) else None
            templates.append(
                Template(
                    code=c,
                    kind=draw(st.sampled_from(["LEC", "TUT", "LAB"])),
                    mode=mode,
                    reference=draw(st.sampled_from(module_codes)),
                    targets=format_selector(
                        Selector((UnderClause(draw(st.sampled_from(programmes))),))
                    ),
                    batch_size=draw(st.integers(1, 5)) if mode == "batched" else None,
                    fixed=tuple(_some(draw, teachers)),
                    pooled=(spec,) if spec else (),
                    duration=draw(st.integers(1, 2)),
                    start_pattern=draw(st.sampled_from([p.code for p in patterns])),
                    sessions_per_week=draw(st.integers(1, 3)),
                    active=draw(st.booleans()),
                )
            )
    template_codes = [t.code for t in templates]

    events, fixed, pooled = [], [], []
    for c in _unique(draw, "A", draw(st.integers(0, 4))):
        online = draw(st.booleans())
        events.append(
            Event(
                code=c,
                kind=draw(st.sampled_from(["LEC", "TUT", "LAB"])),
                duration=draw(st.integers(1, 2)),
                start_pattern=draw(st.sampled_from([p.code for p in patterns])),
                reference=draw(st.one_of(st.none(), *map(st.just, module_codes))),
                delivery="online" if online else "in_person",
                tags=_tags(draw),
                template=draw(st.one_of(st.none(), *map(st.just, template_codes))),
            )
        )
        for target in _some(draw, [*groups, *programmes, *levels]) + _some(draw, teachers):
            fixed.append(FixedRequirement(event=c, resource=target))
        if not online and rooms and draw(st.booleans()):
            spec = room_spec(draw(st.sampled_from(room_types)))
            assert spec is not None
            pooled.append(
                PooledRequirement(
                    event=c, **{**spec.model_dump(), "count": draw(st.integers(1, 2))}
                )
            )

    everything = [r.code for r in resources]
    seen: set[tuple[str, str, str, str]] = set()
    availability = []
    for _ in range(draw(st.integers(0, 3))):
        resource, day = draw(st.sampled_from(everything)), draw(st.sampled_from(days))
        status = draw(st.sampled_from(["unavailable", "avoid"]))
        chosen = periods if draw(st.booleans()) else [draw(st.sampled_from(periods))]
        for p in chosen:
            if (resource, day, p, status) not in seen:
                seen.add((resource, day, p, status))
                availability.append(
                    Availability(resource=resource, day=day, period=p, status=status)
                )

    constraints = []
    for c in _unique(draw, "K", draw(st.integers(0, 3))):
        kind = draw(st.sampled_from(sorted(CATALOGUE)))
        if CATALOGUE[kind] == "resource":
            scope = draw(
                st.sampled_from(
                    [
                        "all",
                        "type:StudentGroup",
                        format_selector(Selector((UnderClause(programmes[0]),))),
                    ]
                )
            )
        else:
            scope = draw(st.sampled_from(["all", "kind:LEC,TUT"]))
        constraints.append(
            Constraint(
                code=c,
                type=kind,
                scope=scope,
                params=draw(
                    st.dictionaries(
                        _plain,
                        st.one_of(
                            st.integers(0, 9), _words, st.lists(st.integers(0, 3), max_size=2)
                        ),
                        max_size=2,
                    )
                ),
                hard=draw(st.booleans()),
                weight=draw(st.integers(0, 9)),
                active=draw(st.booleans()),
            )
        )

    pins = []
    for code in _some(draw, [e.code for e in events], maximum=2):
        pins.append(
            Pin(
                event=code,
                day=draw(st.one_of(st.none(), st.sampled_from(days))),
                start_period=draw(st.one_of(st.none(), st.sampled_from(periods))),
                resources=tuple(_some(draw, rooms, maximum=2)),
                source=draw(st.sampled_from(["user", "lock"])),
            )
        )

    dataset = Dataset(
        preset=PRESET.name,
        resource_types=PRESET.resource_types,
        resources=tuple(resources),
        reference_types=PRESET.reference_types,
        references=tuple(references),
        time=time_model,
        events=tuple(events),
        fixed=tuple(fixed),
        pooled=tuple(pooled),
        availability=tuple(availability),
        constraints=tuple(constraints),
        templates=tuple(templates),
        pins=tuple(pins),
    )
    assert dataset.validate_invariants() == []
    return dataset
