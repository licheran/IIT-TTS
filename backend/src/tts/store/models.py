"""SQLAlchemy tables (spec 06 section 4).

Every table except `dataset` has a `dataset_id` and, where it has a code, a unique
`(dataset_id, code)`. Relationships between rows are held as codes, the same keys the workbook
uses, so a dataset is saved and loaded without translating ids. JSON columns are JSONB on
PostgreSQL.
"""

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

Json = JSON().with_variant(JSONB(), "postgresql")

RUN_STATUSES = (
    "queued",
    "running",
    "succeeded",
    "blocked",
    "infeasible",
    "invalid",
    "cancelled",
    "cancelled_partial",
    "failed",
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: Json, list[Any]: Json}


def _dataset_fk() -> Mapped[int]:
    return mapped_column(ForeignKey("dataset.id", ondelete="CASCADE"), index=True)


class DatasetRow(Base):
    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    preset: Mapped[str] = mapped_column(String(100), default="")
    # The `_meta` rows and `x_` notes of the workbook, kept so that exports round-trip.
    extras: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class _Coded(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = _dataset_fk()


class ResourceTypeRow(_Coded):
    __tablename__ = "resource_type"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    has_capacity: Mapped[bool] = mapped_column(Boolean, default=False)
    attribute_schema: Mapped[list[Any]] = mapped_column(Json, default=list)


class ResourceRow(_Coded):
    __tablename__ = "resource"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(Text, default="")
    parent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attributes: Mapped[list[Any]] = mapped_column(Json, default=list)
    tags: Mapped[list[Any]] = mapped_column(Json, default=list)


class ReferenceTypeRow(_Coded):
    __tablename__ = "reference_type"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(Text, default="")
    attribute_schema: Mapped[list[Any]] = mapped_column(Json, default=list)


class ReferenceRow(_Coded):
    __tablename__ = "reference"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(Text, default="")
    attributes: Mapped[list[Any]] = mapped_column(Json, default=list)
    tags: Mapped[list[Any]] = mapped_column(Json, default=list)


class DayRow(_Coded):
    __tablename__ = "day"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(Text, default="")
    order: Mapped[int] = mapped_column(Integer)


class PeriodRow(_Coded):
    __tablename__ = "period"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    start: Mapped[time] = mapped_column(Time)
    end: Mapped[time] = mapped_column(Time)
    order: Mapped[int] = mapped_column(Integer)
    is_break: Mapped[bool] = mapped_column(Boolean, default=False)


class StartPatternRow(_Coded):
    __tablename__ = "start_pattern"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    duration: Mapped[int] = mapped_column(Integer)
    start_periods: Mapped[list[Any]] = mapped_column(Json, default=list)
    days: Mapped[list[Any] | None] = mapped_column(Json, nullable=True)


class AvailabilityRow(_Coded):
    __tablename__ = "availability"
    __table_args__ = (UniqueConstraint("dataset_id", "resource", "day", "period", "status"),)

    resource: Mapped[str] = mapped_column(String(200))
    day: Mapped[str] = mapped_column(String(200))
    period: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))


class EventRow(_Coded):
    __tablename__ = "event"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(200))
    duration: Mapped[int] = mapped_column(Integer)
    start_pattern: Mapped[str] = mapped_column(String(200))
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivery: Mapped[str] = mapped_column(String(50), default="in_person")
    tags: Mapped[list[Any]] = mapped_column(Json, default=list)
    template: Mapped[str | None] = mapped_column(String(200), nullable=True)


class EventResourceRow(_Coded):
    """A fixed requirement: the event always occupies the resource."""

    __tablename__ = "event_resource"
    __table_args__ = (UniqueConstraint("dataset_id", "event", "resource"),)

    event: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str] = mapped_column(String(200))


class RequirementRow(_Coded):
    """A pooled requirement."""

    __tablename__ = "requirement"
    __table_args__ = (UniqueConstraint("dataset_id", "event", "ordinal"),)

    event: Mapped[str] = mapped_column(String(200))
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    resource_type: Mapped[str] = mapped_column(String(200))
    count: Mapped[int] = mapped_column(Integer, default=1)
    filter: Mapped[str] = mapped_column(Text, default="all")
    capacity_rule: Mapped[str] = mapped_column(String(200), default="none")


class ConstraintRow(_Coded):
    __tablename__ = "constraint"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(Text, default="all")
    params: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    hard: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TemplateRow(_Coded):
    __tablename__ = "template"
    __table_args__ = (UniqueConstraint("dataset_id", "code"),)

    code: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(200))
    mode: Mapped[str] = mapped_column(String(50))
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    targets: Mapped[str] = mapped_column(Text, default="all")
    batch_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fixed: Mapped[list[Any]] = mapped_column(Json, default=list)
    pooled: Mapped[list[Any]] = mapped_column(Json, default=list)
    duration: Mapped[int] = mapped_column(Integer)
    start_pattern: Mapped[str] = mapped_column(String(200))
    sessions_per_week: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PinRow(_Coded):
    __tablename__ = "pin"
    __table_args__ = (UniqueConstraint("dataset_id", "event", "source"),)

    event: Mapped[str] = mapped_column(String(200))
    day: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_period: Mapped[str | None] = mapped_column(String(200), nullable=True)
    resources: Mapped[list[Any]] = mapped_column(Json, default=list)
    source: Mapped[str] = mapped_column(String(20), default="user")


class RunRow(Base):
    __tablename__ = "run"
    __table_args__ = (
        # At most one published run per dataset (spec 06 section 4).
        Index(
            "uq_run_published",
            "dataset_id",
            unique=True,
            postgresql_where=text("published"),
            sqlite_where=text("published"),
        ),
        Index("ix_run_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = _dataset_fk()
    status: Mapped[str] = mapped_column(String(30), default="queued")
    params: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    input_hash: Mapped[str] = mapped_column(String(64), default="")
    snapshot: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    progress: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)


def _run_fk() -> Mapped[int]:
    return mapped_column(ForeignKey("run.id", ondelete="CASCADE"), index=True)


class AssignmentRow(Base):
    __tablename__ = "assignment"
    __table_args__ = (UniqueConstraint("run_id", "event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = _run_fk()
    event: Mapped[str] = mapped_column(String(200))
    day: Mapped[str] = mapped_column(String(200))
    start_period: Mapped[str] = mapped_column(String(200))


class AssignedResourceRow(Base):
    __tablename__ = "assigned_resource"
    __table_args__ = (UniqueConstraint("run_id", "event", "ordinal", "resource"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = _run_fk()
    event: Mapped[str] = mapped_column(String(200))
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    resource: Mapped[str] = mapped_column(String(200))


class CreatedEventRow(Base):
    """A session the solver created for a demand (ADR-0007). It belongs to a run, not a dataset."""

    __tablename__ = "created_event"
    __table_args__ = (UniqueConstraint("run_id", "event"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = _run_fk()
    event: Mapped[str] = mapped_column(String(200))
    demand: Mapped[str] = mapped_column(String(200))


class CreatedParticipantRow(Base):
    __tablename__ = "created_participant"
    __table_args__ = (UniqueConstraint("run_id", "event", "resource"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = _run_fk()
    event: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str] = mapped_column(String(200))


class DiagnosticRow(Base):
    __tablename__ = "diagnostic"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = _run_fk()
    kind: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20), default="error")
    message: Mapped[str] = mapped_column(Text, default="")
    refs: Mapped[list[Any]] = mapped_column(Json, default=list)
    details: Mapped[list[Any]] = mapped_column(Json, default=list)
    minimal: Mapped[bool] = mapped_column(Boolean, default=True)
