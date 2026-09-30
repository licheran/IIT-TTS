"""What a run produced: assignments, grids, differences, publishing and exports."""

from io import BytesIO
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel

from tts.api.deps import DbSession
from tts.api.errors import ApiError, not_found
from tts.api.routers.runs import RunOut, run_out
from tts.core.clashes import cross_clashes
from tts.core.demands import realise
from tts.core.grid import EventChange, Grid, build_grid, diff_results
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, Result
from tts.core.timegrid import TimeGrid
from tts.io.export_html import export_resources, render_csv, render_html
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.presets import labeller
from tts.store.repositories import DatasetRepo, RunRepo

router = APIRouter(prefix="/runs", tags=["results"])
clashes_router = APIRouter(tags=["results"])


class ClashOut(BaseModel):
    resource: str
    day: str
    period: str
    uses: list[dict[str, str]]  # {dataset, run, event}


@clashes_router.get("/clashes")
def clashes(session: DbSession) -> list[ClashOut]:
    """Clashes between the published timetables of different datasets (shared resource codes)."""
    runs = RunRepo(session)
    timetables = []
    names: dict[str, tuple[str, int]] = {}
    for info in DatasetRepo(session).list():
        published = runs.published(info.id)
        if published is None:
            continue
        label = str(info.id)
        names[label] = (info.name, published.id)
        stored = runs.result(published.id)
        dataset = realise(Dataset.model_validate(runs.snapshot(published.id)["dataset"]), stored)
        timetables.append((label, dataset, stored))
    return [
        ClashOut(
            resource=c.resource,
            day=c.day,
            period=c.period,
            uses=[
                {"dataset": names[label][0], "run": str(names[label][1]), "event": event}
                for label, event in c.uses
            ],
        )
        for c in cross_clashes(timetables)
    ]


class AssignmentOut(BaseModel):
    event: str
    kind: str
    reference: str | None
    day: str
    start_period: str
    end_period: str
    fixed: list[str]
    chosen: list[dict[str, Any]]


class DiffOut(BaseModel):
    a: int
    b: int
    changes: list[EventChange]


def _load(session: DbSession, run_id: int) -> tuple[Dataset, Result]:
    runs = RunRepo(session)
    info = runs.get(run_id)
    result = runs.result(run_id)
    if not result.assignments:
        raise ApiError(409, "no_result", f'run {run_id} has no timetable (status "{info.status}")')
    # Sessions the solver created become ordinary events, so grids and exports need no other change.
    return realise(Dataset.model_validate(runs.snapshot(run_id)["dataset"]), result), result


def _check_resource(dataset: Dataset, resource_type: str | None, code: str) -> None:
    found = next((r for r in dataset.resources if r.code == code), None)
    if found is None or (resource_type is not None and found.type != resource_type):
        raise not_found(
            f'no resource "{code}"' + (f" of type {resource_type}" if resource_type else "")
        )


@router.get("/{run_id}/assignments")
def assignments(run_id: int, session: DbSession) -> list[AssignmentOut]:
    dataset, result = _load(session, run_id)
    grid = TimeGrid(dataset.time)
    hierarchy = Hierarchy(dataset)
    events = {e.code: e for e in dataset.events}
    periods = [p.code for p in dataset.time.periods]
    out = []
    for a in result.assignments:
        event = events[a.event]
        last = grid.slot(a.day, a.start_period) + event.duration - 1
        out.append(
            AssignmentOut(
                event=a.event,
                kind=event.kind,
                reference=event.reference,
                day=a.day,
                start_period=a.start_period,
                end_period=periods[min(grid.period_index(last), len(periods) - 1)],
                fixed=list(hierarchy.fixed_resources(a.event)),
                chosen=[{"ordinal": c.ordinal, "resources": list(c.resources)} for c in a.chosen],
            )
        )
    return out


@router.get("/{run_id}/grid")
def grid(run_id: int, code: str, session: DbSession, type: str | None = None) -> Grid:  # noqa: A002
    dataset, result = _load(session, run_id)
    _check_resource(dataset, type, code)
    return build_grid(dataset, result, code)


@router.get("/{a}/diff/{b}")
def diff(a: int, b: int, session: DbSession) -> DiffOut:
    runs = RunRepo(session)
    if runs.get(a).dataset_id != runs.get(b).dataset_id:
        raise ApiError(409, "different_datasets", "the two runs belong to different datasets")
    return DiffOut(a=a, b=b, changes=list(diff_results(runs.result(a), runs.result(b))))


@router.post("/{run_id}/publish")
def publish(run_id: int, session: DbSession) -> RunOut:
    """Make this run the dataset's published one. Any other published run is unpublished."""
    return run_out(RunRepo(session).publish(run_id), session)


@router.get("/{run_id}/export")
def export(
    run_id: int,
    session: DbSession,
    format: Annotated[Literal["html", "xlsx", "csv"], Query()] = "html",  # noqa: A002
    type: str | None = None,  # noqa: A002
    code: str | None = None,
) -> Response:
    """Export a run: HTML grids, a workbook with the assignments, or a CSV list.

    `code` limits it to one resource, `type` to the resources of one type. With neither, the HTML
    holds every timetable (groups, teachers and rooms) in one file, with a contents list.
    """
    dataset, result = _load(session, run_id)
    if code is not None:
        _check_resource(dataset, type, code)
    label = labeller(dataset.preset)
    if format == "xlsx":
        buffer = BytesIO()
        export_xlsx(WorkbookData(dataset, result, run=f"run-{run_id}"), buffer)
        return _download(
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"run-{run_id}.xlsx",
        )
    resources = export_resources(dataset, result, type, code)
    if format == "csv":
        limited = resources if (code is not None or type is not None) else None
        text = render_csv(dataset, result, limited)
        return _download(text.encode("utf-8"), "text/csv; charset=utf-8", f"run-{run_id}.csv")
    title = f"Timetable — run {run_id}" + (f" — {code}" if code else "")
    html = render_html(dataset, result, resources, title, label)
    everything = type is None and code is None
    name = f"run-{run_id}-all.html" if everything else f"run-{run_id}.html"
    return _download(html.encode("utf-8"), "text/html; charset=utf-8", name)


def _download(payload: bytes, media_type: str, filename: str) -> Response:
    return Response(
        payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
