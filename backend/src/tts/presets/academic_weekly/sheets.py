"""Sheet definitions of the academic preset, one per sheet of workbook format 1.

The sheet and column names, the required marks and the order follow
`docs/spec/03-workbook-format.md` section 2, and a test keeps the two in step.
"""

from tts.core.sheets import ColumnDef, PooledMapping, SheetDef
from tts.presets.academic_weekly import types

# Format version 2 holds configuration only (ADR-0007); version 1 is what hand-made datasets
# (typed or imported activities, such as the L6 fixture) use.
FORMAT_VERSION = 2
HAND_MADE_FORMAT_VERSION = 1

UNIVERSITIES = "Universities"
LEVELS = "Levels"
PROGRAMMES = "Programmes"
GROUPS = "Groups"
TEACHERS = "Teachers"
CAMPUSES = "Campuses"
BUILDINGS = "Buildings"
ROOMS = "Rooms"
MODULES = "Modules"
TEMPLATES = "Templates"
ACTIVITIES = "Activities"
ACTIVITY_GROUPS = "ActivityGroups"
ACTIVITY_TEACHERS = "ActivityTeachers"
SESSION_TYPES = "SessionTypes"

RESOURCE_SHEETS = (
    UNIVERSITIES,
    LEVELS,
    PROGRAMMES,
    GROUPS,
    TEACHERS,
    CAMPUSES,
    BUILDINGS,
    ROOMS,
)

MODES = ("joint", "per_group", "batched")
STATUSES = ("unavailable", "avoid")
SOURCES = ("user", "lock")
ROOM_COUNT_DEFAULT = 1


def _c(name: str, field: str | None = None, **kwargs: object) -> ColumnDef:
    return ColumnDef(name=name, field=field or name, **kwargs)


def _entity(
    name: str,
    resource_type: str,
    *columns: ColumnDef,
    label: str,
) -> SheetDef:
    """A sheet of resources: `code`, `name`, the given columns, then `tags`."""
    return SheetDef(
        name=name,
        target="resource",
        resource_type=resource_type,
        label=label,
        columns=(
            _c("code", required=True),
            _c("name"),
            *columns,
            _c("tags", kind="pairs"),
        ),
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
        label="Days",
        columns=(_c("code", required=True), _c("label"), _c("order", kind="int", required=True)),
    ),
    SheetDef(
        name="Periods",
        target="period",
        label="Periods",
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
            _c("start_periods", kind="list", required=True, refs=("Periods",)),
            _c("days", kind="list", refs=("Days",)),
        ),
    ),
    _entity(UNIVERSITIES, types.UNIVERSITY, label="Universities"),
    _entity(
        LEVELS,
        types.LEVEL,
        _c("university", "parent", refs=(UNIVERSITIES,)),
        label="Levels",
    ),
    _entity(
        PROGRAMMES,
        types.PROGRAMME,
        _c("level", "parent", refs=(LEVELS,)),
        label="Programmes",
    ),
    _entity(
        GROUPS,
        types.STUDENT_GROUP,
        _c("parent", required=True, refs=(PROGRAMMES, GROUPS)),
        _c("size", "capacity", kind="int", minimum=0),
        label="Groups",
    ),
    _entity(TEACHERS, types.TEACHER, label="Teachers"),
    _entity(CAMPUSES, types.CAMPUS, label="Campuses"),
    _entity(
        BUILDINGS,
        types.BUILDING,
        _c("abbreviation", "attr:abbreviation"),
        _c("campus", "parent", refs=(CAMPUSES,)),
        label="Buildings",
    ),
    _entity(
        ROOMS,
        types.ROOM,
        _c("building", "parent", refs=(BUILDINGS,)),
        _c("capacity", kind="int", minimum=0),
        _c("room_type", f"tag:{types.ROOM_TYPE_TAG}", required=True),
        label="Rooms",
    ),
    SheetDef(
        name=MODULES,
        target="reference",
        reference_type=types.MODULE,
        label="Modules",
        columns=(
            _c("code", required=True),
            _c("name"),
            _c("level", "attr:level", refs=(LEVELS,)),
            _c("programme", "attr:programme", refs=(PROGRAMMES,)),
            _c("tags", kind="pairs"),
        ),
    ),
    SheetDef(
        name=TEMPLATES,
        target="template",
        label="Templates",
        import_only=True,
        pooled=PooledMapping(
            resource_type=types.ROOM,
            tag=types.ROOM_TYPE_TAG,
            capacity_rule=f"sum_of_fixed:{types.STUDENT_GROUP}",
            type_column="room_type",
        ),
        columns=(
            _c("code", required=True),
            _c("module", "reference", required=True, refs=(MODULES,)),
            _c("kind", required=True),
            _c("mode", required=True, choices=MODES, stored_as=(("per_group", "each"),)),
            _c("groups", "targets", kind="selector", required=True),
            _c("batch_size", kind="int", minimum=1, required_when=("mode", "batched")),
            _c("teachers", "fixed", kind="list", refs=(TEACHERS,)),
            _c("duration", kind="int", required=True, minimum=1),
            _c("start_pattern", required=True, refs=("StartPatterns",)),
            _c("room_type", "pooled_type"),
            _c("sessions_per_week", kind="int", minimum=1, default=1),
            _c("active", kind="bool", default=True),
        ),
    ),
    SheetDef(
        name=ACTIVITIES,
        target="event",
        label="Activities",
        pooled=PooledMapping(
            resource_type=types.ROOM,
            tag=types.ROOM_TYPE_TAG,
            capacity_rule=f"sum_of_fixed:{types.STUDENT_GROUP}",
            type_column="room_type",
            count_column="room_count",
        ),
        columns=(
            _c("code", required=True),
            _c("module", "reference", refs=(MODULES,)),
            _c("kind", required=True),
            _c("duration", kind="int", required=True, minimum=1),
            _c("start_pattern", required=True, refs=("StartPatterns",)),
            _c("delivery", default=types.IN_PERSON),
            _c("room_type", "pooled_type"),
            _c("room_count", "pooled_count", kind="int", minimum=0),
            _c("template", refs=(TEMPLATES,)),
            _c(
                "groups",
                kind="list",
                refs=(GROUPS, PROGRAMMES, LEVELS),
                expands_to=ACTIVITY_GROUPS,
            ),
            _c("teachers", kind="list", refs=(TEACHERS,), expands_to=ACTIVITY_TEACHERS),
            _c("tags", kind="pairs"),
        ),
    ),
    SheetDef(
        name=ACTIVITY_GROUPS,
        target="fixed",
        label="Activity groups",
        hidden=True,
        columns=(
            _c("activity", "event", required=True, refs=(ACTIVITIES,)),
            _c("group", "resource", required=True, refs=(GROUPS, PROGRAMMES, LEVELS)),
        ),
    ),
    SheetDef(
        name=ACTIVITY_TEACHERS,
        target="fixed",
        label="Activity teachers",
        hidden=True,
        columns=(
            _c("activity", "event", required=True, refs=(ACTIVITIES,)),
            _c("teacher", "resource", required=True, refs=(TEACHERS,)),
        ),
    ),
    SheetDef(
        name="Availability",
        target="availability",
        label="Availability",
        columns=(
            _c("resource", required=True, refs=RESOURCE_SHEETS),
            _c("day", required=True, refs=("Days",)),
            _c("period", required=True, refs=("Periods",), allow_star=True),
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
            _c("activity", "event", required=True, refs=(ACTIVITIES,)),
            _c("day", refs=("Days",)),
            _c("start_period", refs=("Periods",)),
            _c("rooms", "resources", kind="list", refs=(ROOMS,)),
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
            _c("activity", "event", refs=(ACTIVITIES,)),
            _c("module", "reference", derive="event.reference"),
            _c("kind", derive="event.kind"),
            _c("day", refs=("Days",)),
            _c("start", kind="time"),
            _c("end", kind="time", derive="end"),
            _c("rooms", "resources", kind="list", refs=(ROOMS,)),
            _c("groups", kind="list", derive=f"fixed:{ACTIVITY_GROUPS}"),
            _c("teachers", kind="list", derive=f"fixed:{ACTIVITY_TEACHERS}"),
            _c("buildings", kind="list", derive=f"ancestors:{BUILDINGS}"),
        ),
    ),
)


def _v2_groups() -> SheetDef:
    return _entity(
        GROUPS,
        types.STUDENT_GROUP,
        _c("parent", required=True, refs=(PROGRAMMES,)),
        _c("size", "capacity", kind="int", minimum=0),
        _c("options", "attr:options", kind="list", refs=(MODULES,)),
        label="Groups",
    )


def _v2_teachers() -> SheetDef:
    # Items are a module code or `module:KIND`, so the preset checks them, not `refs`.
    return _entity(
        TEACHERS,
        types.TEACHER,
        _c("modules", "attr:modules", kind="list"),
        label="Teachers",
    )


SESSION_DELIVERIES = (types.IN_PERSON, types.ONLINE)

_V2_SESSION_TYPES = SheetDef(
    name=SESSION_TYPES,
    target="reference",
    reference_type=types.SESSION_TYPE,
    label="Session types",
    columns=(
        _c("code", required=True),
        _c("name"),
        _c("start_pattern", "attr:start_pattern", required=True, refs=("StartPatterns",)),
        _c("delivery", "attr:delivery", choices=SESSION_DELIVERIES, default=types.IN_PERSON),
        _c("room_type", "attr:room_type", required_when=("delivery", types.IN_PERSON)),
        _c("max_groups", "attr:max_groups", kind="int", minimum=1),
        _c("teachers", "attr:teachers", kind="int", minimum=0, default=1),
        _c("weekly", "attr:weekly", kind="int", minimum=1, default=1),
        _c("tags", kind="pairs"),
    ),
)

_V2_MODULES = SheetDef(
    name=MODULES,
    target="reference",
    reference_type=types.MODULE,
    label="Modules",
    columns=(
        _c("code", required=True),
        _c("name"),
        _c("level", "attr:level", required=True, refs=(LEVELS,)),
        _c("programmes", "attr:programmes", kind="list", refs=(PROGRAMMES,)),
        _c("optional", "attr:optional", kind="bool", default=False),
        # Items are a session type with optional settings, so the preset checks them.
        _c("sessions", "attr:sessions", kind="list"),
        _c("tags", kind="pairs"),
    ),
)


def _v2_sheets() -> tuple[SheetDef, ...]:
    """The sheets of format version 2, in the order of spec 03 section 2a."""
    by_name = {s.name: s for s in SHEETS}
    by_name[GROUPS] = _v2_groups()
    by_name[TEACHERS] = _v2_teachers()
    by_name[MODULES] = _V2_MODULES
    by_name[SESSION_TYPES] = _V2_SESSION_TYPES
    order = (
        "_meta", "Days", "Periods", "StartPatterns", UNIVERSITIES, LEVELS, PROGRAMMES, GROUPS,
        TEACHERS, CAMPUSES, BUILDINGS, ROOMS, SESSION_TYPES, MODULES, "Availability", "Constraints",
    )  # fmt: skip
    return tuple(by_name[name] for name in order)


SHEETS_V2: tuple[SheetDef, ...] = _v2_sheets()
