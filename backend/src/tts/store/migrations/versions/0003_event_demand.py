"""the demand an edited event belongs to

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("event", schema=None) as batch_op:
        batch_op.add_column(sa.Column("demand", sa.String(length=200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("event", schema=None) as batch_op:
        batch_op.drop_column("demand")
