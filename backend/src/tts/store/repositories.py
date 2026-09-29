"""Repositories: the only code that reads and writes the tables (spec 06 section 4).

`DatasetRepo` saves and loads a core `Dataset`. `RunRepo` holds the run lifecycle: creating,
progress, cancel, finishing with a result, publishing and re-queueing stale runs. The `SKIP LOCKED`
claim query lives in `worker/runner.py`, as `backend/CLAUDE.md` allows.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from tts.core.model import (
    Assignment,
    Dataset,
    Diagnostic,
    PooledChoice,
    Result,
)
from tts.store import models as m

_DATASET_TABLES: tuple[type[m.Base], ...] = (
    m.ResourceTypeRow,
    m.ResourceRow,
    m.ReferenceTypeRow,
    m.ReferenceRow,
    m.DayRow,
    m.PeriodRow,
    m.StartPatternRow,
    m.AvailabilityRow,
    m.EventRow,
    m.EventResourceRow,
    m.RequirementRow,
    m.ConstraintRow,
    m.TemplateRow,
    m.PinRow,
)

TERMINAL = (
    "succeeded",
    "blocked",
    "infeasible",
    "invalid",
    "cancelled",
    "cancelled_partial",
    "failed",
)
PUBLISHABLE = ("succeeded", "cancelled_partial")
STALE_AFTER = timedelta(seconds=60)
_List = list  # the repositories define a `list` method, which shadows the builtin in annotations

MAX_ATTEMPTS = 3  # the first run plus two re-queues


class NotFoundError(LookupError):
    """No dataset or run has that id."""


class NotPublishableError(ValueError):
    """A run without a timetable cannot be published."""


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    id: int
    name: str
    preset: str
    version: int
    created_at: datetime
    updated_at: datetime


def _info(row: m.DatasetRow) -> DatasetInfo:
    return DatasetInfo(row.id, row.name, row.preset, row.version, row.created_at, row.updated_at)


class DatasetRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        name: str,
        preset: str,
        dataset: Dataset | None = None,
        extras: Mapping[str, Any] | None = None,
    ) -> int:
        row = m.DatasetRow(name=name, preset=preset, extras=dict(extras or {}))
        self.session.add(row)
        self.session.flush()
        self._write(row.id, dataset or Dataset(preset=preset))
        return row.id

    def list(self) -> _List[DatasetInfo]:
        rows = self.session.scalars(select(m.DatasetRow).order_by(m.DatasetRow.id)).all()
        return [_info(r) for r in rows]

    def info(self, dataset_id: int) -> DatasetInfo:
        return _info(self._row(dataset_id))

    def rename(self, dataset_id: int, name: str) -> DatasetInfo:
        row = self._row(dataset_id)
        row.name = name
        row.updated_at = m.utcnow()
        return _info(row)

    def delete(self, dataset_id: int) -> None:
        self._row(dataset_id)
        self.session.execute(delete(m.DatasetRow).where(m.DatasetRow.id == dataset_id))
        self.session.expire_all()

    def save(
        self, dataset_id: int, dataset: Dataset, extras: Mapping[str, Any] | None = None
    ) -> DatasetInfo:
        """Replace every row of the dataset. `extras=None` keeps the stored ones."""
        row = self._row(dataset_id)
        for table in _DATASET_TABLES:
            self.session.execute(delete(table).where(table.dataset_id == dataset_id))  # type: ignore[attr-defined]
        self._write(dataset_id, dataset)
        row.preset = dataset.preset or row.preset
        if extras is not None:
            row.extras = dict(extras)
        row.version += 1
        row.updated_at = m.utcnow()
        return _info(row)

    def extras(self, dataset_id: int) -> dict[str, Any]:
        return dict(self._row(dataset_id).extras)

    def load(self, dataset_id: int) -> Dataset:
        row = self._row(dataset_id)
        s = self.session

        def rows[T: m.Base](table: type[T]) -> list[T]:
            return list(
                s.scalars(select(table).where(table.dataset_id == dataset_id).order_by(table.id))  # type: ignore[attr-defined]
            )

        return Dataset.model_validate(
            {
                "preset": row.preset,
                "resource_types": [
                    {
                        "code": r.code,
                        "exclusive": r.exclusive,
                        "has_capacity": r.has_capacity,
                        "attribute_schema": r.attribute_schema,
                    }
                    for r in rows(m.ResourceTypeRow)
                ],
                "resources": [
                    {
                        "code": r.code,
                        "type": r.type,
                        "name": r.name,
                        "parent": r.parent,
                        "capacity": r.capacity,
                        "attributes": r.attributes,
                        "tags": r.tags,
                    }
                    for r in rows(m.ResourceRow)
                ],
                "reference_types": [
                    {"code": r.code, "name": r.name, "attribute_schema": r.attribute_schema}
                    for r in rows(m.ReferenceTypeRow)
                ],
                "references": [
                    {
                        "code": r.code,
                        "type": r.type,
                        "name": r.name,
                        "attributes": r.attributes,
                        "tags": r.tags,
                    }
                    for r in rows(m.ReferenceRow)
                ],
                "time": {
                    "days": [
                        {"code": r.code, "label": r.label, "order": r.order} for r in rows(m.DayRow)
                    ],
                    "periods": [
                        {
                            "code": r.code,
                            "start": r.start,
                            "end": r.end,
                            "order": r.order,
                            "is_break": r.is_break,
                        }
                        for r in rows(m.PeriodRow)
                    ],
                    "start_patterns": [
                        {
                            "code": r.code,
                            "duration": r.duration,
                            "start_periods": r.start_periods,
                            "days": r.days,
                        }
                        for r in rows(m.StartPatternRow)
                    ],
                },
                "events": [
                    {
                        "code": r.code,
                        "kind": r.kind,
                        "duration": r.duration,
                        "start_pattern": r.start_pattern,
                        "reference": r.reference,
                        "delivery": r.delivery,
                        "tags": r.tags,
                        "template": r.template,
                    }
                    for r in rows(m.EventRow)
                ],
                "fixed": [
                    {"event": r.event, "resource": r.resource} for r in rows(m.EventResourceRow)
                ],
                "pooled": [
                    {
                        "event": r.event,
                        "ordinal": r.ordinal,
                        "resource_type": r.resource_type,
                        "count": r.count,
                        "filter": r.filter,
                        "capacity_rule": _capacity_rule(r.capacity_rule),
                    }
                    for r in rows(m.RequirementRow)
                ],
                "availability": [
                    {"resource": r.resource, "day": r.day, "period": r.period, "status": r.status}
                    for r in rows(m.AvailabilityRow)
                ],
                "constraints": [
                    {
                        "code": r.code,
                        "type": r.type,
                        "scope": r.scope,
                        "params": r.params,
                        "hard": r.hard,
                        "weight": r.weight,
                        "active": r.active,
                    }
                    for r in rows(m.ConstraintRow)
                ],
                "templates": [
                    {
                        "code": r.code,
                        "kind": r.kind,
                        "mode": r.mode,
                        "reference": r.reference,
                        "targets": r.targets,
                        "batch_size": r.batch_size,
                        "fixed": r.fixed,
                        "pooled": r.pooled,
                        "duration": r.duration,
                        "start_pattern": r.start_pattern,
                        "sessions_per_week": r.sessions_per_week,
                        "active": r.active,
                    }
                    for r in rows(m.TemplateRow)
                ],
                "pins": [
                    {
                        "event": r.event,
                        "day": r.day,
                        "start_period": r.start_period,
                        "resources": r.resources,
                        "source": r.source,
                    }
                    for r in rows(m.PinRow)
                ],
            }
        )

    # -- internals -----------------------------------------------------------------------------

    def _row(self, dataset_id: int) -> m.DatasetRow:
        row = self.session.get(m.DatasetRow, dataset_id)
        if row is None:
            raise NotFoundError(f"dataset {dataset_id} not found")
        return row

    def _write(self, dataset_id: int, ds: Dataset) -> None:
        add = self.session.add_all
        d = dataset_id
        add(
            m.ResourceTypeRow(
                dataset_id=d,
                code=t.code,
                exclusive=t.exclusive,
                has_capacity=t.has_capacity,
                attribute_schema=[a.model_dump() for a in t.attribute_schema],
            )
            for t in ds.resource_types
        )
        add(
            m.ResourceRow(
                dataset_id=d,
                code=r.code,
                type=r.type,
                name=r.name,
                parent=r.parent,
                capacity=r.capacity,
                attributes=[list(p) for p in r.attributes],
                tags=[list(p) for p in r.tags],
            )
            for r in ds.resources
        )
        add(
            m.ReferenceTypeRow(
                dataset_id=d,
                code=t.code,
                name=t.name,
                attribute_schema=[a.model_dump() for a in t.attribute_schema],
            )
            for t in ds.reference_types
        )
        add(
            m.ReferenceRow(
                dataset_id=d,
                code=r.code,
                type=r.type,
                name=r.name,
                attributes=[list(p) for p in r.attributes],
                tags=[list(p) for p in r.tags],
            )
            for r in ds.references
        )
        add(m.DayRow(dataset_id=d, code=x.code, label=x.label, order=x.order) for x in ds.time.days)
        add(
            m.PeriodRow(
                dataset_id=d,
                code=p.code,
                start=p.start,
                end=p.end,
                order=p.order,
                is_break=p.is_break,
            )
            for p in ds.time.periods
        )
        add(
            m.StartPatternRow(
                dataset_id=d,
                code=s.code,
                duration=s.duration,
                start_periods=list(s.start_periods),
                days=None if s.days is None else list(s.days),
            )
            for s in ds.time.start_patterns
        )
        add(
            m.AvailabilityRow(
                dataset_id=d, resource=a.resource, day=a.day, period=a.period, status=a.status
            )
            for a in ds.availability
        )
        add(
            m.EventRow(
                dataset_id=d,
                code=e.code,
                kind=e.kind,
                duration=e.duration,
                start_pattern=e.start_pattern,
                reference=e.reference,
                delivery=e.delivery,
                tags=[list(p) for p in e.tags],
                template=e.template,
            )
            for e in ds.events
        )
        add(m.EventResourceRow(dataset_id=d, event=f.event, resource=f.resource) for f in ds.fixed)
        add(
            m.RequirementRow(
                dataset_id=d,
                event=q.event,
                ordinal=q.ordinal,
                resource_type=q.resource_type,
                count=q.count,
                filter=q.filter,
                capacity_rule=str(q.capacity_rule),
            )
            for q in ds.pooled
        )
        add(
            m.ConstraintRow(
                dataset_id=d,
                code=c.code,
                type=c.type,
                scope=c.scope,
                params=dict(c.params),
                hard=c.hard,
                weight=c.weight,
                active=c.active,
            )
            for c in ds.constraints
        )
        add(
            m.TemplateRow(
                dataset_id=d,
                code=t.code,
                kind=t.kind,
                mode=t.mode,
                reference=t.reference,
                targets=t.targets,
                batch_size=t.batch_size,
                fixed=list(t.fixed),
                pooled=[p.model_dump(mode="json") for p in t.pooled],
                duration=t.duration,
                start_pattern=t.start_pattern,
                sessions_per_week=t.sessions_per_week,
                active=t.active,
            )
            for t in ds.templates
        )
        add(
            m.PinRow(
                dataset_id=d,
                event=p.event,
                day=p.day,
                start_period=p.start_period,
                resources=list(p.resources),
                source=p.source,
            )
            for p in ds.pins
        )
        self.session.flush()


def _capacity_rule(text: str) -> dict[str, Any]:
    from tts.core.model import CapacityRule

    return CapacityRule.parse(text).model_dump()


# --- Runs --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RunInfo:
    id: int
    dataset_id: int
    status: str
    params: dict[str, Any]
    input_hash: str
    progress: dict[str, Any]
    score: float | None
    score_breakdown: dict[str, Any]
    cancel_requested: bool
    published: bool
    attempts: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


def _run_info(row: m.RunRow) -> RunInfo:
    return RunInfo(
        id=row.id,
        dataset_id=row.dataset_id,
        status=row.status,
        params=dict(row.params),
        input_hash=row.input_hash,
        progress=dict(row.progress),
        score=row.score,
        score_breakdown=dict(row.score_breakdown),
        cancel_requested=row.cancel_requested,
        published=row.published,
        attempts=row.attempts,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


class RunRepo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        dataset_id: int,
        params: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        input_hash: str,
    ) -> int:
        DatasetRepo(self.session)._row(dataset_id)
        row = m.RunRow(
            dataset_id=dataset_id,
            status="queued",
            params=dict(params),
            snapshot=dict(snapshot),
            input_hash=input_hash,
        )
        self.session.add(row)
        self.session.flush()
        return row.id

    def get(self, run_id: int) -> RunInfo:
        return _run_info(self._row(run_id))

    def list(self, dataset_id: int) -> _List[RunInfo]:
        rows = self.session.scalars(
            select(m.RunRow).where(m.RunRow.dataset_id == dataset_id).order_by(m.RunRow.id.desc())
        )
        return [_run_info(r) for r in rows]

    def snapshot(self, run_id: int) -> dict[str, Any]:
        return dict(self._row(run_id).snapshot)

    def request_cancel(self, run_id: int) -> RunInfo:
        """Ask a run to stop. A queued run is cancelled at once."""
        row = self._row(run_id)
        if row.status == "queued":
            row.status = "cancelled"
            row.finished_at = m.utcnow()
        elif row.status == "running":
            row.cancel_requested = True
        return _run_info(row)

    def cancel_requested(self, run_id: int) -> bool:
        return bool(
            self.session.scalar(select(m.RunRow.cancel_requested).where(m.RunRow.id == run_id))
        )

    def heartbeat(self, run_id: int, progress: Mapping[str, Any] | None = None) -> None:
        values: dict[str, Any] = {"heartbeat_at": m.utcnow()}
        if progress is not None:
            values["progress"] = dict(progress)
        self.session.execute(update(m.RunRow).where(m.RunRow.id == run_id).values(**values))

    def finish(
        self,
        run_id: int,
        status: str,
        result: Result | None = None,
        diagnostics: Iterable[Diagnostic] = (),
        score: float | None = None,
        score_breakdown: Mapping[str, Any] | None = None,
        progress: Mapping[str, Any] | None = None,
    ) -> RunInfo:
        row = self._row(run_id)
        row.status = status
        row.finished_at = m.utcnow()
        row.score = score
        row.score_breakdown = dict(score_breakdown or {})
        if progress is not None:
            row.progress = dict(progress)
        self.session.execute(delete(m.AssignmentRow).where(m.AssignmentRow.run_id == run_id))
        self.session.execute(
            delete(m.AssignedResourceRow).where(m.AssignedResourceRow.run_id == run_id)
        )
        self.session.execute(delete(m.DiagnosticRow).where(m.DiagnosticRow.run_id == run_id))
        for a in result.assignments if result else ():
            self.session.add(
                m.AssignmentRow(
                    run_id=run_id, event=a.event, day=a.day, start_period=a.start_period
                )
            )
            for choice in a.chosen:
                for resource in choice.resources:
                    self.session.add(
                        m.AssignedResourceRow(
                            run_id=run_id, event=a.event, ordinal=choice.ordinal, resource=resource
                        )
                    )
        for d in diagnostics:
            self.session.add(
                m.DiagnosticRow(
                    run_id=run_id,
                    kind=d.kind,
                    severity=d.severity,
                    message=d.message,
                    refs=[r.model_dump() for r in d.refs],
                    details=list(d.details),
                    minimal=d.minimal,
                )
            )
        self.session.flush()
        return _run_info(row)

    def result(self, run_id: int) -> Result:
        self._row(run_id)
        chosen: dict[str, dict[int, list[str]]] = {}
        for r in self.session.scalars(
            select(m.AssignedResourceRow).where(m.AssignedResourceRow.run_id == run_id)
        ):
            chosen.setdefault(r.event, {}).setdefault(r.ordinal, []).append(r.resource)
        assignments = []
        for a in self.session.scalars(
            select(m.AssignmentRow).where(m.AssignmentRow.run_id == run_id)
        ):
            picks = tuple(
                PooledChoice(ordinal=o, resources=tuple(rs))
                for o, rs in sorted(chosen.get(a.event, {}).items())
            )
            assignments.append(
                Assignment(event=a.event, day=a.day, start_period=a.start_period, chosen=picks)
            )
        return Result(assignments=tuple(assignments))

    def diagnostics(self, run_id: int) -> _List[Diagnostic]:
        rows = self.session.scalars(
            select(m.DiagnosticRow)
            .where(m.DiagnosticRow.run_id == run_id)
            .order_by(m.DiagnosticRow.id)
        )
        return [
            Diagnostic.model_validate(
                {
                    "kind": r.kind,
                    "severity": r.severity,
                    "message": r.message,
                    "refs": r.refs,
                    "details": r.details,
                    "minimal": r.minimal,
                }
            )
            for r in rows
        ]

    def publish(self, run_id: int) -> RunInfo:
        """Make the run the dataset's published one, unpublishing any other (spec 06 section 4)."""
        row = self._row(run_id)
        if row.status not in PUBLISHABLE:
            raise NotPublishableError(
                f'a run with status "{row.status}" has no timetable to publish'
            )
        self.session.execute(
            update(m.RunRow)
            .where(m.RunRow.dataset_id == row.dataset_id, m.RunRow.published.is_(True))
            .values(published=False)
        )
        self.session.flush()
        row.published = True
        self.session.flush()
        return _run_info(row)

    def unpublish(self, run_id: int) -> RunInfo:
        row = self._row(run_id)
        row.published = False
        return _run_info(row)

    def published(self, dataset_id: int) -> RunInfo | None:
        row = self.session.scalar(
            select(m.RunRow).where(m.RunRow.dataset_id == dataset_id, m.RunRow.published.is_(True))
        )
        return None if row is None else _run_info(row)

    def reap_stale(self, now: datetime | None = None) -> tuple[_List[int], _List[int]]:
        """Re-queue runs left `running` without a heartbeat for 60 s, at most twice.

        Returns the ids re-queued and the ids failed.
        """
        cutoff = (now or datetime.now(UTC)) - STALE_AFTER
        stale = self.session.scalars(
            select(m.RunRow).where(
                m.RunRow.status == "running",
                (m.RunRow.heartbeat_at < cutoff) | m.RunRow.heartbeat_at.is_(None),
            )
        ).all()
        requeued, failed = [], []
        for row in stale:
            if row.heartbeat_at is None and row.started_at is not None:
                started = row.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=UTC)
                if started >= cutoff:
                    continue
            if row.attempts >= MAX_ATTEMPTS:
                row.status = "failed"
                row.finished_at = m.utcnow()
                row.progress = {**row.progress, "error": "the worker stopped responding"}
                failed.append(row.id)
            else:
                row.status = "queued"
                row.worker_id = None
                row.started_at = None
                row.heartbeat_at = None
                requeued.append(row.id)
        self.session.flush()
        return requeued, failed

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(m.RunRow)) or 0)

    def _row(self, run_id: int) -> m.RunRow:
        row = self.session.get(m.RunRow, run_id)
        if row is None:
            raise NotFoundError(f"run {run_id} not found")
        return row
