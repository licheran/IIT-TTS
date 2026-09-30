"""sessions the solver created for demands

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "created_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=200), nullable=False),
        sa.Column("demand", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "event"),
    )
    with op.batch_alter_table("created_event", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_created_event_run_id"), ["run_id"], unique=False)

    op.create_table(
        "created_participant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=200), nullable=False),
        sa.Column("resource", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "event", "resource"),
    )
    with op.batch_alter_table("created_participant", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_created_participant_run_id"), ["run_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("created_participant", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_created_participant_run_id"))
    op.drop_table("created_participant")
    with op.batch_alter_table("created_event", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_created_event_run_id"))
    op.drop_table("created_event")
