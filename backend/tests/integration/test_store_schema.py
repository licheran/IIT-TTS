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
