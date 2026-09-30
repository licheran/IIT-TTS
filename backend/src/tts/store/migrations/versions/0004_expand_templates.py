"""expand stored templates into activities, then drop them (ADR-0007, Phase 23)

The application keeps no templates any more: they were only a way to type activities. A dataset
that still has template rows gets its activities made once, the way the importer does for a
version 1 file, and its templates are removed. A template that cannot be expanded is dropped too
(the importer would have refused the file, but a stored dataset must not become unreadable).

Revision ID: 0004
Revises: 0003
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ids = [r[0] for r in bind.execute(sa.text("SELECT DISTINCT dataset_id FROM template"))]
    if not ids:
        return
    # Only reached by a database that has templates, so a fresh one never needs the models.
    from tts.expand.templates import expand
    from tts.presets import expansion_options
    from tts.store.repositories import DatasetRepo

    session = Session(bind=bind)
    repo = DatasetRepo(session)
    for dataset_id in ids:
        dataset = repo.load(dataset_id)
        options: dict[str, Any] = expansion_options(dataset.preset)
        done = expand(dataset, **options).dataset
        events = tuple(e.model_copy(update={"template": None}) for e in done.events)
        repo.save(dataset_id, done.model_copy(update={"templates": (), "events": events}))
    session.flush()


def downgrade() -> None:
    """Templates cannot be brought back: the activities they made stay."""
