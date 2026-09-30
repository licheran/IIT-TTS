"""HTML and CSV exports of a result (spec 06 section 3, FR-13).

The HTML page has one weekly grid per resource. The grid layout comes from `core.grid`, so the
page shows exactly what the API's grid endpoint returns. A page with several grids groups them by
resource type and starts with a contents list that links to each one.
"""

import csv
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import StringIO

from jinja2 import Environment, PackageLoader, select_autoescape

from tts.core.grid import Grid, build_grid, chosen_resources, involved
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Result
from tts.core.timegrid import TimeGrid

Labeller = Callable[[str], str]

_env = Environment(
    loader=PackageLoader("tts.io", "templates"),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True, slots=True)
class ResourceGrid:
    resource: str
    name: str
    type_label: str
    grid: Grid
    anchor: str


@dataclass(frozen=True, slots=True)
class Section:
    """The grids of one resource type, under one heading of a multi-grid page."""

    label: str
    anchor: str
    grids: list[ResourceGrid]


def anchor_ids(codes: Sequence[str], prefix: str = "r") -> list[str]:
    """One HTML id per code: letters and digits only, and never the same id twice."""
    taken: set[str] = set()
    ids = []
    for code in codes:
        base = f"{prefix}-{re.sub(r'[^A-Za-z0-9]+', '-', code).strip('-').lower() or 'item'}"
        candidate, n = base, 1
        while candidate in taken:
            n += 1
            candidate = f"{base}-{n}"
        taken.add(candidate)
        ids.append(candidate)
    return ids


def export_resources(
    dataset: Dataset,
    result: Result,
    resource_type: str | None = None,
    code: str | None = None,
) -> list[str]:
    """The resources to export: one code, else every one of a type, else every exclusive one.

    Only resources that have at least one event are listed.
    """
    seen = involved(dataset, result)
    types = {t.code: t for t in dataset.resource_types}
    chosen = []
    for r in dataset.resources:
        if code is not None:
            if r.code != code:
                continue
        elif resource_type is not None:
            if r.type != resource_type:
                continue
        elif not types[r.type].exclusive:
            continue
        if r.code in seen:
            chosen.append(r.code)
    return chosen


def render_html(
    dataset: Dataset,
    result: Result,
    resources: Sequence[str],
    title: str,
    label: Labeller = str,
) -> str:
    by_code = {r.code: r for r in dataset.resources}
    type_order = {t.code: i for i, t in enumerate(dataset.resource_types)}
    # Grouped by type in the dataset's order; within a type the order given is kept.
    ordered = sorted(
        resources,
        key=lambda c: type_order.get(by_code[c].type, len(type_order)) if c in by_code else 0,
    )
    anchors = anchor_ids(ordered)
    grids = [
        ResourceGrid(
            resource=code,
            name=by_code[code].name if code in by_code else "",
            type_label=label(by_code[code].type) if code in by_code else "",
            grid=build_grid(dataset, result, code),
            anchor=anchor,
        )
        for code, anchor in zip(ordered, anchors, strict=True)
    ]
    sections: list[Section] = []
    for g in grids:
        if not sections or sections[-1].label != g.type_label:
            sections.append(Section(label=g.type_label, anchor="", grids=[]))
        sections[-1].grids.append(g)
    type_anchors = anchor_ids([s.label for s in sections], prefix="type")
    sections = [
        Section(label=s.label, anchor=a, grids=s.grids)
        for s, a in zip(sections, type_anchors, strict=True)
    ]
    return _env.get_template("grid.html.j2").render(
        title=title,
        sections=sections,
        contents=len(grids) > 1,
        days=dataset.time.days,
        kind_label=label,
    )


def render_csv(dataset: Dataset, result: Result, resources: Sequence[str] | None = None) -> str:
    """One row per placed event, in event order. `resources` keeps only events involving them."""
    grid = TimeGrid(dataset.time)
    hierarchy = Hierarchy(dataset)
    events = {e.code: e for e in dataset.events}
    periods = [p.code for p in dataset.time.periods]
    keep: set[str] | None = None
    if resources is not None:
        seen = involved(dataset, result)
        keep = {event for code in resources for event in seen.get(code, ())}
    out = StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(
        ["event", "kind", "reference", "day", "start_period", "end_period", "fixed", "chosen"]
    )
    for a in result.assignments:
        event = events[a.event]
        if keep is not None and a.event not in keep:
            continue
        end = grid.slot(a.day, a.start_period) + event.duration - 1
        end_period = periods[min(grid.period_index(end), len(periods) - 1)]
        writer.writerow(
            [
                a.event,
                event.kind,
                event.reference or "",
                a.day,
                a.start_period,
                end_period,
                ";".join(hierarchy.fixed_resources(a.event)),
                ";".join(chosen_resources(a)),
            ]
        )
    return out.getvalue()
