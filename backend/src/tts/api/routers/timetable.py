"""The Activities table of a configured dataset: the solver's sessions, and the user's edits.

The table shows the dataset's current run (the published one, else the latest that has a
timetable) with the edits applied. An edit keeps what the user changed in one session (its day,
start, rooms, teachers, or which groups meet) as a declared event of the session's demand, with
the session's code. The next run is a complete rebuild that keeps the edited values and solves
everything else again (ADR-0007, spec 05 section 2.2). Nothing here changes a stored run.
"""

from collections import defaultdict
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from tts.api.deps import DbSession
from tts.api.errors import ApiError, not_found
from tts.api.expansion import prepare_with_preset
from tts.core.demands import realise, with_edits
from tts.core.model import Dataset, Event, FixedRequirement, Pin, Result
from tts.core.timegrid import TimeGrid
from tts.core.verifier import verify
from tts.presets.academic_weekly import types
from tts.store.repositories import PUBLISHABLE, DatasetRepo, RunRepo

router = APIRouter(prefix="/datasets/{dataset_id}/timetable", tags=["timetable"])

# What each kind of resource is called in a session's row.
ROLES = {types.STUDENT_GROUP: "groups", types.TEACHER: "teachers", types.ROOM: "rooms"}


class SessionOut(BaseModel):
    code: str
    module: str | None
    kind: str
    demand: str
    groups: list[str]
    teachers: list[str]
    rooms: list[str]
    day: str
    start: str
    end: str
    edited: list[str]  # the fields the user set: groups, day, start, rooms, teachers


class TimetableOut(BaseModel):
    run_id: int | None
    edits: int
    rows: list[SessionOut]


class EditBody(BaseModel):
    """The values to keep for one session. A field left out is not changed."""

    day: str | None = None
    start: str | None = None
    rooms: list[str] | None = None
    teachers: list[str] | None = None
    groups: list[str] | None = None


class ViolationOut(BaseModel):
    code: str
    constraint_code: str
    severity: str
    message: str
    refs: list[dict[str, str]]


class CheckOut(BaseModel):
    run_id: int | None
    violations: list[ViolationOut]


def _configured(session: DbSession, dataset_id: int) -> Dataset:
    dataset = DatasetRepo(session).load(dataset_id)
    if dataset.kind == "hand_made":
        raise ApiError(409, "not_configured", "this dataset's activities were typed or imported")
    return dataset


def _current_run(session: DbSession, dataset_id: int) -> tuple[int | None, Result | None]:
    runs = RunRepo(session)
    chosen = runs.published(dataset_id) or next(
        (r for r in runs.list(dataset_id) if r.status in PUBLISHABLE), None
    )
    if chosen is None:
        return None, None
    return chosen.id, runs.result(chosen.id)


def _rows(prepared: Dataset, draft: Result) -> list[SessionOut]:
    real = realise(prepared, draft)
    declared = {e.code for e in prepared.events if e.demand is not None}
    grid = TimeGrid(real.time)
    periods = [p.code for p in real.time.periods]
    events = {e.code: e for e in real.events}
    kinds = {r.code: r.type for r in real.resources}
    fixed: dict[str, list[str]] = defaultdict(list)
    for f in real.fixed:
        fixed[f.event].append(f.resource)
    pins: dict[str, list[Pin]] = defaultdict(list)
    for pin in real.pins:
        pins[pin.event].append(pin)
    rows = []
    for a in draft.assignments:
        event = events.get(a.event)
        if event is None or event.demand is None:
            continue
        by_role: dict[str, list[str]] = {"groups": [], "teachers": [], "rooms": []}
        for code in [*fixed[a.event], *(r for c in a.chosen for r in c.resources)]:
            role = ROLES.get(kinds.get(code, ""))
            if role is not None and code not in by_role[role]:
                by_role[role].append(code)
        last = grid.slot(a.day, a.start_period) + event.duration - 1
        rows.append(
            SessionOut(
                code=a.event,
                module=event.reference,
                kind=event.kind,
                demand=event.demand,
                groups=sorted(by_role["groups"]),
                teachers=sorted(by_role["teachers"]),
                rooms=sorted(by_role["rooms"]),
                day=a.day,
                start=a.start_period,
                end=periods[min(grid.period_index(last), len(periods) - 1)],
                edited=_edited(a.event, declared, pins[a.event], kinds),
            )
        )
    return sorted(rows, key=lambda r: r.code)


def _edited(code: str, declared: set[str], pins: list[Pin], kinds: dict[str, str]) -> list[str]:
    """The fields an edit has set (an edit always keeps its groups together). Sessions the run
    made itself have none."""
    if code not in declared:
        return []
    fields = ["groups"]
    for pin in pins:
        if pin.day is not None and "day" not in fields:
            fields.append("day")
        if pin.start_period is not None and "start" not in fields:
            fields.append("start")
        for resource in pin.resources:
            field = ROLES.get(kinds.get(resource, ""))
            if field in ("rooms", "teachers") and field not in fields:
                fields.append(field)
    return fields


def _timetable(session: DbSession, dataset_id: int) -> TimetableOut:
    current = _configured(session, dataset_id)
    prepared = prepare_with_preset(current)
    run_id, result = _current_run(session, dataset_id)
    draft = with_edits(prepared, result or Result())
    edits = sum(1 for e in prepared.events if e.demand is not None)
    return TimetableOut(run_id=run_id, edits=edits, rows=_rows(prepared, draft))


@router.get("")
def timetable(dataset_id: int, session: DbSession) -> TimetableOut:
    """The sessions of the current run, with the edits applied."""
    return _timetable(session, dataset_id)


def _pin_of(dataset: Dataset, code: str) -> Pin | None:
    return next((p for p in dataset.pins if p.event == code and p.source == "user"), None)


@router.put("/{code}")
def edit(dataset_id: int, code: str, body: EditBody, session: DbSession) -> TimetableOut:
    """Keep the given values for one session in the next run (and in the table at once)."""
    current = _configured(session, dataset_id)
    prepared = prepare_with_preset(current)
    _, result = _current_run(session, dataset_id)
    draft = with_edits(prepared, result or Result())
    real = realise(prepared, draft)
    event = next((e for e in real.events if e.code == code and e.demand is not None), None)
    if event is None:
        raise not_found(f'no session "{code}" in the current run')

    kinds = {r.code: r.type for r in real.resources}
    members = [
        f.resource
        for f in real.fixed
        if f.event == code and kinds.get(f.resource) == types.STUDENT_GROUP
    ]
    groups = sorted(body.groups if body.groups is not None else members)
    existing = _pin_of(prepared, code)
    resources = list(existing.resources) if existing is not None else []
    if body.rooms is not None or body.teachers is not None:
        resources = [
            r
            for r in resources
            if not (body.rooms is not None and kinds.get(r) == types.ROOM)
            and not (body.teachers is not None and kinds.get(r) == types.TEACHER)
        ]
        resources += [*(body.rooms or []), *(body.teachers or [])]
    pin = Pin(
        event=code,
        day=body.day if body.day is not None else (existing.day if existing else None),
        start_period=body.start
        if body.start is not None
        else (existing.start_period if existing else None),
        resources=tuple(resources),
        source="user",
    )
    edited = Event(
        code=code,
        kind=event.kind,
        duration=event.duration,
        start_pattern=event.start_pattern,
        reference=event.reference,
        delivery=event.delivery,
        tags=event.tags,
        demand=event.demand,
    )
    others = _without(current, {code})
    updated = others.model_copy(
        update={
            "events": (*others.events, edited),
            "fixed": (*others.fixed, *(FixedRequirement(event=code, resource=g) for g in groups)),
            "pins": (*others.pins, pin),
        }
    )
    issues = [
        i
        for i in prepare_with_preset(updated).validate_invariants()
        if i.table in ("event", "pin", "fixed")
    ]
    if issues:
        raise ApiError(
            422,
            "invalid_edit",
            "; ".join(f'{i.table} "{i.key}": {i.message}' for i in issues),
        )
    DatasetRepo(session).save(dataset_id, updated)
    return _timetable(session, dataset_id)


def _without(dataset: Dataset, codes: set[str]) -> Dataset:
    """The dataset without the edits named by `codes` (their events, groups and pins)."""
    return dataset.model_copy(
        update={
            "events": tuple(e for e in dataset.events if e.code not in codes),
            "fixed": tuple(f for f in dataset.fixed if f.event not in codes),
            "pins": tuple(p for p in dataset.pins if p.event not in codes),
        }
    )


@router.delete("/{code}")
def undo(dataset_id: int, code: str, session: DbSession) -> TimetableOut:
    """Forget the edit of one session: the next run is free to place it again."""
    current = _configured(session, dataset_id)
    if not any(e.code == code and e.demand is not None for e in current.events):
        raise not_found(f'session "{code}" has no edit')
    DatasetRepo(session).save(dataset_id, _without(current, {code}))
    return _timetable(session, dataset_id)


@router.delete("")
def clear(dataset_id: int, session: DbSession) -> TimetableOut:
    """Forget every edit."""
    current = _configured(session, dataset_id)
    codes = {e.code for e in current.events if e.demand is not None}
    DatasetRepo(session).save(dataset_id, _without(current, codes))
    return _timetable(session, dataset_id)


@router.get("/check")
def check(dataset_id: int, session: DbSession) -> CheckOut:
    """The current run's timetable with the edits applied, judged by the verifier.

    Nothing is stored: the stored run is never changed. A clash an edit causes shows here at once.
    """
    current = _configured(session, dataset_id)
    prepared = prepare_with_preset(current)
    run_id, result = _current_run(session, dataset_id)
    if result is None:
        return CheckOut(run_id=None, violations=[])
    draft = with_edits(prepared, result)
    found: list[Any] = verify(prepared, draft)
    return CheckOut(
        run_id=run_id,
        violations=[
            ViolationOut(
                code=v.code,
                constraint_code=v.constraint_code,
                severity=v.severity,
                message=v.message,
                refs=[{"kind": r.kind, "code": r.code} for r in v.refs],
            )
            for v in found
            if v.severity != "soft"
        ],
    )
