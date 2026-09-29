"""HTML and CSV exports of a result (spec 06 section 3, FR-13).

The HTML page has one weekly grid per resource. The grid layout comes from `core.grid`, so the
page shows exactly what the API's grid endpoint returns.
"""

import csv
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
    grids = [
        ResourceGrid(
            resource=code,
            name=by_code[code].name if code in by_code else "",
            type_label=label(by_code[code].type) if code in by_code else "",
            grid=build_grid(dataset, result, code),
        )
        for code in resources
    ]
    return _env.get_template("grid.html.j2").render(
        title=title, grids=grids, days=dataset.time.days, kind_label=label
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
