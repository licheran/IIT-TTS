"""The Alembic migration matches the models, and the published-run index holds."""

from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from tts.store.db import make_engine, make_session_factory, session_scope, upgrade
from tts.store.models import Base, DatasetRow, RunRow


@pytest.fixture
def engine(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 't.db'}"
    upgrade(url)
    return make_engine(url)


def test_the_migration_creates_every_table_of_the_spec(engine) -> None:
    expected = {
        "dataset", "resource_type", "resource", "reference_type", "reference", "day", "period",
        "start_pattern", "availability", "event", "event_resource", "requirement", "constraint",
        "template", "pin", "run", "assignment", "assigned_resource", "created_event",
        "created_participant", "diagnostic",
    }  # fmt: skip
    assert expected <= set(inspect(engine).get_table_names())


def test_the_migration_and_the_models_agree(engine) -> None:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []


def test_a_dataset_can_have_only_one_published_run(engine) -> None:
    factory = make_session_factory(engine)
    with session_scope(factory) as session:
        session.add(DatasetRow(name="d", preset="p"))
        session.flush()
        dataset_id = session.scalars(select(DatasetRow.id)).one()
        session.add(RunRow(dataset_id=dataset_id, published=True))
        session.add(RunRow(dataset_id=dataset_id, published=False))
        session.add(RunRow(dataset_id=dataset_id, published=False))
    with pytest.raises(IntegrityError), session_scope(factory) as session:
        session.add(RunRow(dataset_id=dataset_id, published=True))


def test_the_templates_migration_expands_stored_templates_and_drops_them(tmp_path: Path) -> None:
    from datetime import time

    from sqlalchemy import text

    from tts.core.model import (
        Dataset,
        Day,
        Period,
        Reference,
        Resource,
        StartPattern,
        Template,
        TimeModel,
    )
    from tts.presets.academic_weekly import types
    from tts.store.repositories import DatasetRepo

    old = Dataset(
        preset="academic_weekly",
        resource_types=types.RESOURCE_TYPES,
        reference_types=types.REFERENCE_TYPES,
        resources=(
            Resource(code="PR1", type="Programme"),
            Resource(code="G1", type="StudentGroup", parent="PR1", capacity=30),
        ),
        references=(Reference(code="M1", type="Module"),),
        time=TimeModel(
            days=(Day(code="Mon", order=1),),
            periods=(Period(code="P1", start=time(8), end=time(9), order=1),),
            start_patterns=(StartPattern(code="1H", duration=1, start_periods=("P1",)),),
        ),
        templates=(
            Template(
                code="TP1", kind="LEC", mode="joint", reference="M1", targets="type:StudentGroup",
                duration=1, start_pattern="1H", sessions_per_week=2,
            ),
        ),
    )  # fmt: skip
    url = f"sqlite:///{tmp_path / 'old.db'}"
    upgrade(url, "0003")
    factory = make_session_factory(make_engine(url))
    with session_scope(factory) as session:
        dataset_id = DatasetRepo(session).create("old", "academic_weekly", old)
    upgrade(url)
    with session_scope(factory) as session:
        stored = DatasetRepo(session).load(dataset_id)
        assert stored.templates == ()
        assert [e.code for e in stored.events] == ["M1-LEC-01", "M1-LEC-02"]
        assert all(e.template is None for e in stored.events)
        assert session.execute(text("SELECT count(*) FROM template")).scalar_one() == 0
