"""Weekly grid of one resource, and the difference between two results.

`build_grid` says where each event of a resource sits in a days-by-periods grid. It is the one
place that decides this: the API's JSON grid, the HTML export and the web UI's picture all
follow it. A multi-period event is one cell with a `span`. An event that serves several fixed
resources (a joint event) lists all of them.
"""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from tts.core.hierarchy import Hierarchy
from tts.core.model import Assignment, Dataset, Result
from tts.core.timegrid import TimeGrid


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GridDay(_Frozen):
    code: str
    label: str


class GridPeriod(_Frozen):
    code: str
    start: str
    end: str
    is_break: bool


class GridCell(_Frozen):
    """One event in the grid.

    `row` is the index of its first period and `span` the number of periods it covers, so it is
    drawn as one block. Events of a resource that is not exclusive can overlap in time: `lane`
    and `lanes` say how to place them side by side (lane 0 of 1 when nothing overlaps).
    """

    event: str
    kind: str
    reference: str | None
    day: str
    start_period: str
    day_index: int
    row: int
    span: int
    duration: int
    fixed: tuple[str, ...]
    chosen: tuple[str, ...]
    lane: int = 0
    lanes: int = 1


class Grid(_Frozen):
    resource: str
    days: tuple[GridDay, ...]
    periods: tuple[GridPeriod, ...]
    cells: tuple[GridCell, ...]


def chosen_resources(assignment: Assignment) -> tuple[str, ...]:
    """Every pooled resource chosen for an assignment, sorted by code."""
    return tuple(sorted({r for choice in assignment.chosen for r in choice.resources}))


def involved(dataset: Dataset, result: Result) -> dict[str, list[str]]:
    """The events (with a placement) that involve each resource, by resource code.

    An event involves what it occupies and every ancestor of that (so a parent's grid shows the
    events of everything below it).
    """
    hierarchy = Hierarchy(dataset)
    found: dict[str, list[str]] = {}
    for assignment in result.assignments:
        occupied = hierarchy.occupied_resources(assignment.event, chosen_resources(assignment))
        touched = set(occupied)
        for code in occupied:
            touched.update(hierarchy.ancestors(code))
        for code in touched:
            found.setdefault(code, []).append(assignment.event)
    return found


def build_grid(dataset: Dataset, result: Result, resource: str) -> Grid:
    grid = TimeGrid(dataset.time)
    events = {e.code: e for e in dataset.events}
    hierarchy = Hierarchy(dataset)
    cells: list[GridCell] = []
    for assignment in result.assignments:
        event = events.get(assignment.event)
        if event is None:
            continue
        chosen = chosen_resources(assignment)
        occupied = hierarchy.occupied_resources(event.code, chosen)
        touched = set(occupied)
        for code in occupied:
            touched.update(hierarchy.ancestors(code))
        if resource not in touched:
            continue
        start = grid.slot(assignment.day, assignment.start_period)
        cells.append(
            GridCell(
                event=event.code,
                kind=event.kind,
                reference=event.reference,
                day=assignment.day,
                start_period=assignment.start_period,
                day_index=grid.day_index(start),
                row=grid.period_index(start),
                span=min(event.duration, grid.periods_per_day - grid.period_index(start)),
                duration=event.duration,
                fixed=tuple(hierarchy.fixed_resources(event.code)),
                chosen=chosen,
            )
        )
    cells = _assign_lanes(cells)
    return Grid(
        resource=resource,
        days=tuple(GridDay(code=d.code, label=d.label or d.code) for d in dataset.time.days),
        periods=tuple(
            GridPeriod(
                code=p.code,
                start=p.start.strftime("%H:%M"),
                end=p.end.strftime("%H:%M"),
                is_break=p.is_break,
            )
            for p in dataset.time.periods
        ),
        cells=tuple(sorted(cells, key=lambda c: (c.day_index, c.row, c.event))),
    )


def _assign_lanes(cells: list[GridCell]) -> list[GridCell]:
    """Give overlapping cells of one day separate lanes (greedy, by start time)."""
    by_day: dict[int, list[GridCell]] = {}
    for cell in cells:
        by_day.setdefault(cell.day_index, []).append(cell)
    placed: list[GridCell] = []
    for day_cells in by_day.values():
        day_cells.sort(key=lambda c: (c.row, c.event))
        cluster: list[tuple[GridCell, int]] = []
        lane_ends: list[int] = []
        cluster_end = -1

        def flush(items: list[tuple[GridCell, int]], lanes: int) -> None:
            placed.extend(c.model_copy(update={"lane": lane, "lanes": lanes}) for c, lane in items)

        for cell in day_cells:
            if cluster and cell.row >= cluster_end:
                flush(cluster, len(lane_ends))
                cluster, lane_ends, cluster_end = [], [], -1
            lane = next((i for i, end in enumerate(lane_ends) if end <= cell.row), None)
            if lane is None:
                lane_ends.append(cell.row + cell.span)
                lane = len(lane_ends) - 1
            else:
                lane_ends[lane] = cell.row + cell.span
            cluster.append((cell, lane))
            cluster_end = max(cluster_end, cell.row + cell.span)
        if cluster:
            flush(cluster, len(lane_ends))
    return placed


# --- Differences between two results -----------------------------------------------------------


class Placement(_Frozen):
    day: str
    start_period: str
    resources: tuple[str, ...]


class EventChange(_Frozen):
    """How one event differs between two results.

    `kind` is `moved`, `resources`, `added` or `removed`.
    """

    event: str
    kind: str
    before: Placement | None
    after: Placement | None


def _placement(assignment: Assignment) -> Placement:
    return Placement(
        day=assignment.day,
        start_period=assignment.start_period,
        resources=chosen_resources(assignment),
    )


def diff_results(a: Result, b: Result) -> tuple[EventChange, ...]:
    """The events that differ between `a` and `b`, sorted by event code."""
    before = {x.event: _placement(x) for x in a.assignments}
    after = {x.event: _placement(x) for x in b.assignments}
    changes: list[EventChange] = []
    for event in sorted(before.keys() | after.keys()):
        old, new = before.get(event), after.get(event)
        if old is None:
            changes.append(EventChange(event=event, kind="added", before=None, after=new))
        elif new is None:
            changes.append(EventChange(event=event, kind="removed", before=old, after=None))
        elif (old.day, old.start_period) != (new.day, new.start_period):
            changes.append(EventChange(event=event, kind="moved", before=old, after=new))
        elif old.resources != new.resources:
            changes.append(EventChange(event=event, kind="resources", before=old, after=new))
    return tuple(changes)


def resources_with_events(dataset: Dataset, result: Result, codes: Iterable[str]) -> list[str]:
    """The given resource codes that have at least one event in `result`, in the order given."""
    seen = involved(dataset, result)
    return [c for c in codes if c in seen]
