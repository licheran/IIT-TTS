"""Sheet definitions of the exams preset (its own workbook format, version 1).

Days are dated (`code` is the date, for example `2026-06-01`), and the periods are exam
sessions (`AM`, `PM`). Each exam needs one hall big enough for its cohorts and a number of
invigilators (ADR-0006: two pooled requirements on one sheet).
"""

from tts.core.sheets import ColumnDef, PooledMapping, SheetDef
from tts.presets.exams import types

FORMAT_VERSION = 1

COHORTS = "Cohorts"
HALLS = "Halls"
INVIGILATORS = "Invigilators"
PAPERS = "Papers"
EXAMS = "Exams"
EXAM_COHORTS = "ExamCohorts"
RESOURCE_SHEETS = (COHORTS, HALLS, INVIGILATORS)
STATUSES = ("unavailable", "avoid")
SOURCES = ("user", "lock")


def _c(name: str, field: str | None = None, **kwargs: object) -> ColumnDef:
    return ColumnDef(name=name, field=field or name, **kwargs)


def _entity(name: str, resource_type: str, *columns: ColumnDef, label: str) -> SheetDef:
    return SheetDef(
        name=name,
        target="resource",
        resource_type=resource_type,
        label=label,
        columns=(_c("code", required=True), _c("name"), *columns, _c("tags", kind="pairs")),
    )


HALL_NEED = PooledMapping(
    resource_type=types.HALL, capacity_rule=f"sum_of_fixed:{types.COHORT}"
)  # one hall with room for every cohort of the exam
INVIGILATOR_NEED = PooledMapping(
    resource_type=types.INVIGILATOR, capacity_rule="none", count_column="invigilators"
)

SHEETS: tuple[SheetDef, ...] = (
    SheetDef(
        name="_meta",
        target="meta",
        label="Workbook information",
        columns=(_c("key", required=True), _c("value")),
    ),
    SheetDef(
        name="Days",
        target="day",
        label="Exam days",
        columns=(_c("code", required=True), _c("label"), _c("order", kind="int", required=True)),
    ),
    SheetDef(
        name="Sessions",
        target="period",
        label="Sessions",
        columns=(
            _c("code", required=True),
            _c("start", kind="time", required=True),
            _c("end", kind="time", required=True),
            _c("order", kind="int", required=True),
            _c("is_break", kind="bool", default=False),
        ),
    ),
    SheetDef(
        name="StartPatterns",
        target="start_pattern",
        label="Start patterns",
        columns=(
            _c("code", required=True),
            _c("duration", kind="int", required=True, minimum=1),
            _c("start_periods", kind="list", required=True, refs=("Sessions",)),
            _c("days", kind="list", refs=("Days",)),
        ),
    ),
    _entity(COHORTS, types.COHORT, _c("size", "capacity", kind="int", minimum=0), label="Cohorts"),
    _entity(HALLS, types.HALL, _c("capacity", kind="int", minimum=0), label="Halls"),
    _entity(INVIGILATORS, types.INVIGILATOR, label="Invigilators"),
    SheetDef(
        name=PAPERS,
        target="reference",
        reference_type=types.PAPER,
        label="Papers",
        columns=(
            _c("code", required=True),
            _c("name"),
            _c("minutes", "attr:minutes", kind="int", minimum=0),
            _c("tags", kind="pairs"),
        ),
    ),
    SheetDef(
        name=EXAMS,
        target="event",
        label="Exams",
        pooled=HALL_NEED,
        more_pooled=(INVIGILATOR_NEED,),
        columns=(
            _c("code", required=True),
            _c("paper", "reference", refs=(PAPERS,)),
            _c("kind", required=True, choices=types.KINDS),
            _c("duration", kind="int", required=True, minimum=1),
            _c("start_pattern", required=True, refs=("StartPatterns",)),
            _c("invigilators", "pooled_count:1", kind="int", minimum=0, default=1),
            _c("cohorts", kind="list", refs=(COHORTS,), expands_to=EXAM_COHORTS),
            _c("tags", kind="pairs"),
        ),
    ),
    SheetDef(
        name=EXAM_COHORTS,
        target="fixed",
        label="Exam cohorts",
        columns=(
            _c("exam", "event", required=True, refs=(EXAMS,)),
            _c("cohort", "resource", required=True, refs=(COHORTS,)),
        ),
    ),
    SheetDef(
        name="Availability",
        target="availability",
        label="Availability",
        columns=(
            _c("resource", required=True, refs=RESOURCE_SHEETS),
            _c("day", required=True, refs=("Days",)),
            _c("period", required=True, refs=("Sessions",), allow_star=True),
            _c("status", required=True, choices=STATUSES),
        ),
    ),
    SheetDef(
        name="Constraints",
        target="constraint",
        label="Constraints",
        columns=(
            _c("code", required=True),
            _c("type", required=True),
            _c("scope", kind="selector", required=True),
            _c("params", kind="json"),
            _c("hard", kind="bool", default=True),
            _c("weight", kind="int", minimum=0, default=1),
            _c("active", kind="bool", default=True),
        ),
    ),
    SheetDef(
        name="Pins",
        target="pin",
        label="Pins",
        columns=(
            _c("exam", "event", required=True, refs=(EXAMS,)),
            _c("day", refs=("Days",)),
            _c("start_period", refs=("Sessions",)),
            _c("resources", kind="list", refs=(HALLS, INVIGILATORS)),
            _c("source", choices=SOURCES, default="user"),
        ),
    ),
    SheetDef(
        name="Assignments",
        target="assignment",
        label="Assignments",
        export_only=True,
        columns=(
            _c("run"),
            _c("exam", "event", refs=(EXAMS,)),
            _c("paper", "reference", derive="event.reference"),
            _c("day", refs=("Days",)),
            _c("start", kind="time"),
            _c("end", kind="time", derive="end"),
            _c("hall", "resources", kind="list", refs=(HALLS,)),
            _c("invigilators", "resources:1", kind="list", refs=(INVIGILATORS,)),
            _c("cohorts", kind="list", derive=f"fixed:{EXAM_COHORTS}"),
        ),
    ),
)
