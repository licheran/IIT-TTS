"""Dataset management, the preset schema and pre-flight."""

from fastapi import APIRouter

from tts.api.deps import DbSession
from tts.api.errors import ApiError
from tts.api.expansion import preflight_with_preset, prepare_with_preset
from tts.api.schemas import (
    DatasetCreate,
    DatasetOut,
    DatasetPatch,
    IssueOut,
    PlannedOut,
    PreflightOut,
    RefOut,
    SchemaOut,
)
from tts.api.workbooks import preset_of
from tts.core.model import Dataset
from tts.preflight.checks import has_errors
from tts.presets import (
    PRESETS,
    UnknownPresetError,
    get_preset,
    labels,
    with_defaults,
)
from tts.store.repositories import DatasetInfo, DatasetRepo

presets_router = APIRouter(tags=["datasets"])
router = APIRouter(prefix="/datasets", tags=["datasets"])


@presets_router.get("/presets")
def list_presets() -> list[str]:
    """The names of the presets a dataset can be created from."""
    return sorted(PRESETS)


def _out(info: DatasetInfo, kind: str = "configured") -> DatasetOut:
    return DatasetOut(
        id=info.id,
        name=info.name,
        preset=info.preset,
        kind=kind,
        version=info.version,
        created_at=info.created_at,
        updated_at=info.updated_at,
    )


@router.get("")
def list_datasets(session: DbSession) -> list[DatasetOut]:
    repo = DatasetRepo(session)
    return [_out(i, repo.kind(i.id)) for i in repo.list()]


@router.post("", status_code=201)
def create_dataset(body: DatasetCreate, session: DbSession) -> DatasetOut:
    try:
        preset = get_preset(body.preset)
    except UnknownPresetError as error:
        raise ApiError(422, "unknown_preset", str(error)) from None
    repo = DatasetRepo(session)
    seed = with_defaults(
        Dataset(
            preset=preset.name,
            resource_types=preset.resource_types,
            reference_types=preset.reference_types,
        )
    )
    dataset_id = repo.create(body.name, preset.name, seed)
    return _out(repo.info(dataset_id), repo.kind(dataset_id))


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int, session: DbSession) -> DatasetOut:
    repo = DatasetRepo(session)
    return _out(repo.info(dataset_id), repo.kind(dataset_id))


@router.patch("/{dataset_id}")
def rename_dataset(dataset_id: int, body: DatasetPatch, session: DbSession) -> DatasetOut:
    repo = DatasetRepo(session)
    return _out(repo.rename(dataset_id, body.name), repo.kind(dataset_id))


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, session: DbSession) -> None:
    DatasetRepo(session).delete(dataset_id)


@router.get("/{dataset_id}/schema")
def get_schema(dataset_id: int, session: DbSession) -> SchemaOut:
    """The preset's sheet definitions and labels. They drive the table editors."""
    preset = preset_of(session, dataset_id)
    return SchemaOut(
        preset=preset.name,
        kind=DatasetRepo(session).kind(dataset_id),
        format_version=preset.format_version,
        sheets=list(preset.sheets),
        labels=labels(preset.name),
        resource_types=list(preset.resource_types),
    )


@router.get("/{dataset_id}/sessions")
def planned_sessions(dataset_id: int, session: DbSession) -> list[PlannedOut]:
    """The sessions the solver will make: each module and kind, its groups and how many sessions."""
    dataset = DatasetRepo(session).load(dataset_id)
    if dataset.kind == "hand_made":
        raise ApiError(409, "not_configured", "this dataset's activities were typed or imported")
    return [
        PlannedOut(
            demand=d.code,
            module=d.reference,
            kind=d.kind,
            groups=list(d.participants),
            groups_per_session=d.max_participants,
            blocks=d.blocks,
            per_week=d.repeat,
            sessions=d.blocks * d.repeat,
        )
        for d in prepare_with_preset(dataset).demands
    ]


@router.post("/{dataset_id}/preflight")
def preflight(dataset_id: int, session: DbSession) -> PreflightOut:
    dataset = DatasetRepo(session).load(dataset_id)
    preset = preset_of(session, dataset_id)
    issues = preflight_with_preset(dataset)
    type_of = {r.code: r.type for r in dataset.resources}
    sheet_of_type = {s.resource_type: s.name for s in preset.sheets if s.resource_type}
    sheet_of_target: dict[str, str] = {
        s.target: s.name for s in preset.sheets if s.target in ("event", "constraint")
    }

    def sheet_for(kind: str, code: str) -> str | None:
        if kind == "resource":
            return sheet_of_type.get(type_of.get(code, ""))
        return sheet_of_target.get(kind)

    return PreflightOut(
        issues=[
            IssueOut(
                severity=i.severity,
                kind=i.kind,
                message=i.message,
                refs=[
                    RefOut(kind=r.kind, code=r.code, sheet=sheet_for(r.kind, r.code))
                    for r in i.refs
                ],
            )
            for i in issues
        ],
        has_errors=has_errors(issues),
    )
