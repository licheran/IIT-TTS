"""Starting, watching and cancelling runs."""

import hashlib
import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from tts.api.deps import DbSession
from tts.api.errors import ApiError
from tts.api.expansion import expand_with_preset
from tts.core.model import Dataset
from tts.core.run import RunParams
from tts.core.selectors import SelectorError
from tts.core.staging import published_locks, stage, with_locks
from tts.store.repositories import DatasetRepo, RunInfo, RunRepo

router = APIRouter(tags=["runs"])


class RunCreated(BaseModel):
    run_id: int


class DiagnosticOut(BaseModel):
    kind: str
    severity: str
    message: str
    refs: list[dict[str, Any]] = []
    details: list[str] = []
    minimal: bool = True


class RunOut(BaseModel):
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
    created_at: str
    started_at: str | None
    finished_at: str | None
    diagnostics: list[DiagnosticOut] = []


def snapshot_of(dataset_json: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """The frozen input of a run and its SHA-256 (of the canonical JSON, spec 05 section 1)."""
    canonical = json.dumps(dataset_json, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"dataset": dataset_json}, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_out(info: RunInfo, session: DbSession | None = None) -> RunOut:
    diagnostics: list[DiagnosticOut] = []
    if session is not None:
        diagnostics = [
            DiagnosticOut(
                kind=d.kind,
                severity=d.severity,
                message=d.message,
                refs=[r.model_dump() for r in d.refs],
                details=list(d.details),
                minimal=d.minimal,
            )
            for d in RunRepo(session).diagnostics(info.id)
        ]
    return RunOut(
        id=info.id,
        dataset_id=info.dataset_id,
        status=info.status,
        params=info.params,
        input_hash=info.input_hash,
        progress=info.progress,
        score=info.score,
        score_breakdown=info.score_breakdown,
        cancel_requested=info.cancel_requested,
        published=info.published,
        attempts=info.attempts,
        created_at=info.created_at.isoformat(),
        started_at=info.started_at.isoformat() if info.started_at else None,
        finished_at=info.finished_at.isoformat() if info.finished_at else None,
        diagnostics=diagnostics,
    )


@router.post("/datasets/{dataset_id}/runs", status_code=201)
def start_run(dataset_id: int, session: DbSession, params: RunParams | None = None) -> RunCreated:
    """Snapshot and hash the dataset, then queue a run. The worker picks it up."""
    # The snapshot holds the expanded dataset, so a run's events, grids and exports all name the
    # activities its templates made, even if the templates change later.
    dataset = expand_with_preset(DatasetRepo(session).load(dataset_id)).dataset
    params = params or RunParams()
    runs = RunRepo(session)
    if params.lock_published:
        others = []
        for info in DatasetRepo(session).list():
            published = runs.published(info.id) if info.id != dataset_id else None
            if published is not None:
                theirs = Dataset.model_validate(runs.snapshot(published.id)["dataset"])
                others.append((theirs, runs.result(published.id)))
        dataset = with_locks(dataset, published_locks(dataset, others))
    if params.stage_scope:
        mine = runs.published(dataset_id)
        previous = runs.result(mine.id) if mine is not None else None
        try:
            dataset = stage(dataset, params.stage_scope, previous)
        except SelectorError as error:
            raise ApiError(422, "invalid_stage_scope", f"stage_scope: {error}") from None
    snapshot, digest = snapshot_of(dataset.model_dump(mode="json"))
    run_id = RunRepo(session).create(dataset_id, params.model_dump(mode="json"), snapshot, digest)
    return RunCreated(run_id=run_id)


@router.get("/datasets/{dataset_id}/runs")
def list_runs(dataset_id: int, session: DbSession) -> list[RunOut]:
    DatasetRepo(session).info(dataset_id)
    return [run_out(r) for r in RunRepo(session).list(dataset_id)]


@router.get("/runs/{run_id}")
def get_run(run_id: int, session: DbSession) -> RunOut:
    return run_out(RunRepo(session).get(run_id), session)


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: int, session: DbSession) -> RunOut:
    info = RunRepo(session).request_cancel(run_id)
    if info.status not in ("queued", "running", "cancelled") and not info.cancel_requested:
        raise ApiError(409, "not_running", f'a run with status "{info.status}" cannot be cancelled')
    return run_out(info, session)
