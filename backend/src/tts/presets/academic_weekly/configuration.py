"""From configuration to demands (ADR-0007, spec 02 section 6.1, spec 03 section 2a).

A configured academic dataset holds no activities. Its modules say which session types they have,
its teachers which modules they teach, its programmes which groups they contain, and its groups
which optional modules they take. `demands` turns that into the core's demands, one per module
and session type, and `configuration_issues` finds the mistakes the sheet columns cannot (an option
that is not optional, a teacher for a session type the module lacks, ...).

Both are pure functions of a dataset. They hold no scheduling logic: what a demand asks for is
data, and the solver decides the rest.
"""

import re
from collections import defaultdict
from dataclasses import dataclass

from tts.core.model import CapacityRule, Dataset, Demand, PooledSpec, Reference, Resource
from tts.core.selectors import CodeClause, Selector, format_selector
from tts.core.sheets import ConfigIssue
from tts.presets.academic_weekly import types

LIST_SEP = ";"
SETTINGS = ("start_pattern", "delivery", "room_type", "max_groups", "teachers", "weekly")
ROOM_ORDINAL = 0
TEACHER_ORDINAL = 1

_ITEM = re.compile(r"^(?P<code>[^()]+?)\s*(?:\((?P<settings>.*)\))?$")


def split_list(text: object) -> tuple[str, ...]:
    """The items of a `;`-separated attribute (none for a missing or blank one)."""
    if not isinstance(text, str):
        return ()
    return tuple(part.strip() for part in text.split(LIST_SEP) if part.strip())


@dataclass(frozen=True, slots=True)
class SessionItem:
    """One entry of `Modules.sessions`: a session type and the settings it overrides."""

    code: str
    settings: tuple[tuple[str, str], ...] = ()
    problem: str | None = None  # why the entry cannot be read


def parse_session_item(text: str) -> SessionItem:
    match = _ITEM.match(text.strip())
    if match is None:
        return SessionItem(text.strip(), problem=f'cannot read "{text.strip()}"')
    code = match["code"].strip()
    raw = match["settings"]
    if raw is None:
        return SessionItem(code)
    settings: list[tuple[str, str]] = []
    for part in raw.split(","):
        if not part.strip():
            continue
        name, equals, value = part.partition("=")
        if not equals or not name.strip():
            return SessionItem(code, problem=f'cannot read "{text.strip()}": expected name=value')
        if name.strip() not in SETTINGS:
            known = ", ".join(SETTINGS)
            return SessionItem(code, problem=f'unknown setting "{name.strip()}" (known: {known})')
        settings.append((name.strip(), value.strip()))
    return SessionItem(code, tuple(settings))


def parse_teacher_item(text: str) -> tuple[str, str | None]:
    """`module` or `module:KIND` as (module, kind or None)."""
    module, colon, kind = text.partition(":")
    return module.strip(), (kind.strip() if colon else None)


class _Tables:
    """The configuration's rows, indexed once."""

    def __init__(self, dataset: Dataset) -> None:
        self.ds = dataset
        self.modules: dict[str, Reference] = {
            r.code: r for r in dataset.references if r.type == types.MODULE
        }
        self.session_types: dict[str, Reference] = {
            r.code: r for r in dataset.references if r.type == types.SESSION_TYPE
        }
        self.by_type: dict[str, list[Resource]] = defaultdict(list)
        for resource in dataset.resources:
            self.by_type[resource.type].append(resource)
        self.resources = {r.code: r for r in dataset.resources}
        self.patterns = {p.code: p for p in dataset.time.start_patterns}

    def attribute(self, row: Reference | Resource, name: str) -> object:
        return dict(row.attributes).get(name)

    def programmes_of(self, module: Reference) -> tuple[str, ...]:
        """The programmes that take the module: the listed ones, else those at its level."""
        listed = split_list(self.attribute(module, "programmes"))
        if listed:
            return listed
        level = self.attribute(module, "level")
        return tuple(r.code for r in self.by_type[types.PROGRAMME] if r.parent == level)

    def level_of_group(self, group: Resource) -> str | None:
        parent = self.resources.get(group.parent or "")
        return parent.parent if parent is not None and parent.type == types.PROGRAMME else None


def _setting(session_type: Reference, item: SessionItem, name: str, tables: _Tables) -> object:
    overridden = dict(item.settings)
    if name in overridden:
        return overridden[name]
    return tables.attribute(session_type, name)


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        return int(value.strip())
    return None


def _teacher_pool(tables: _Tables, module: str, kind: str) -> tuple[str, ...]:
    """The teachers that list the module for every kind, or for this kind."""
    pool = []
    for teacher in tables.by_type[types.TEACHER]:
        for item in split_list(tables.attribute(teacher, "modules")):
            wanted, only = parse_teacher_item(item)
            if wanted == module and only in (None, kind):
                pool.append(teacher.code)
                break
    return tuple(sorted(pool))


def participants_of(tables: _Tables, module: Reference) -> tuple[str, ...]:
    """The groups that take the module: every group of its programmes when it is mandatory, only
    the groups that list it among their options when it is optional."""
    programmes = set(tables.programmes_of(module))
    optional = bool(tables.attribute(module, "optional"))
    found = []
    for group in tables.by_type[types.STUDENT_GROUP]:
        if group.parent not in programmes:
            continue
        if optional and module.code not in split_list(tables.attribute(group, "options")):
            continue
        found.append(group.code)
    return tuple(sorted(found))


def demands(dataset: Dataset) -> tuple[Demand, ...]:
    """One demand for each module and session type of the configuration.

    Entries that cannot be made into a demand (an unknown session type, a setting that is not a
    number) are skipped: `configuration_issues` reports them.
    """
    tables = _Tables(dataset)
    found: list[Demand] = []
    for module in sorted(tables.modules.values(), key=lambda r: r.code):
        participants = participants_of(tables, module)
        for text in split_list(tables.attribute(module, "sessions")):
            item = parse_session_item(text)
            session_type = tables.session_types.get(item.code)
            if item.problem is not None or session_type is None:
                continue
            made = _demand(tables, module, session_type, item, participants)
            if made is not None:
                found.append(made)
    return tuple(found)


def _demand(
    tables: _Tables,
    module: Reference,
    session_type: Reference,
    item: SessionItem,
    participants: tuple[str, ...],
) -> Demand | None:
    pattern = _setting(session_type, item, "start_pattern", tables)
    start = tables.patterns.get(str(pattern))
    if start is None:
        return None
    limit = _as_int(_setting(session_type, item, "max_groups", tables))
    weekly = _as_int(_setting(session_type, item, "weekly", tables))
    teachers = _as_int(_setting(session_type, item, "teachers", tables))
    delivery = _setting(session_type, item, "delivery", tables) or types.IN_PERSON
    room_type = _setting(session_type, item, "room_type", tables)
    if (limit is not None and limit < 1) or (weekly is not None and weekly < 1):
        return None
    if teachers is not None and teachers < 0:
        return None

    pooled: list[PooledSpec] = []
    if delivery != types.ONLINE and room_type:
        pooled.append(
            PooledSpec(
                resource_type=types.ROOM,
                ordinal=ROOM_ORDINAL,
                filter=f"tag:{types.ROOM_TYPE_TAG}={room_type}",
                capacity_rule=CapacityRule.parse(f"sum_of_fixed:{types.STUDENT_GROUP}"),
            )
        )
    count = 1 if teachers is None else teachers
    if count > 0:
        pool = _teacher_pool(tables, module.code, session_type.code)
        pooled.append(
            PooledSpec(
                resource_type=types.TEACHER,
                ordinal=TEACHER_ORDINAL,
                count=count,
                # With nobody listed the filter matches nothing, which pre-flight reports.
                filter=format_selector(Selector((CodeClause(pool or ("(nobody)",)),))),
            )
        )
    return Demand(
        code=f"{module.code}-{session_type.code}",
        kind=session_type.code,
        reference=module.code,
        participants=participants,
        max_participants=limit,
        repeat=weekly or 1,
        duration=start.duration,
        start_pattern=start.code,
        delivery=str(delivery),
        pooled=tuple(pooled),
        # A session carries its type's tags, and its module's tags win over them.
        tags=tuple({**dict(session_type.tags), **dict(module.tags)}.items()),
    )


def configuration_issues(dataset: Dataset) -> list[ConfigIssue]:
    """What is wrong with the configuration, by sheet, row code and column (spec 03 section 3)."""
    tables = _Tables(dataset)
    found: list[ConfigIssue] = []
    _session_types(tables, found)
    _modules(tables, found)
    _teachers(tables, found)
    _groups(tables, found)
    return found


def _session_types(tables: _Tables, found: list[ConfigIssue]) -> None:
    for session_type in tables.session_types.values():
        delivery = tables.attribute(session_type, "delivery") or types.IN_PERSON
        if delivery == types.ONLINE and tables.attribute(session_type, "room_type"):
            found.append(
                ConfigIssue(
                    "SessionTypes",
                    session_type.code,
                    "room_type",
                    "an online session cannot have a room type",
                )
            )


def _modules(tables: _Tables, found: list[ConfigIssue]) -> None:
    for module in tables.modules.values():
        level = tables.attribute(module, "level")
        for code in split_list(tables.attribute(module, "programmes")):
            programme = tables.resources.get(code)
            if programme is not None and programme.parent != level:
                found.append(
                    ConfigIssue(
                        "Modules",
                        module.code,
                        "programmes",
                        f'programme "{code}" belongs to level "{programme.parent}", not "{level}"',
                    )
                )
        for text in split_list(tables.attribute(module, "sessions")):
            item = parse_session_item(text)
            if item.problem is not None:
                found.append(ConfigIssue("Modules", module.code, "sessions", item.problem))
            elif item.code not in tables.session_types:
                found.append(
                    ConfigIssue("Modules", module.code, "sessions", f'unknown code "{item.code}"')
                )
            else:
                _settings(tables, module, text, item, found)


def _settings(
    tables: _Tables, module: Reference, text: str, item: SessionItem, found: list[ConfigIssue]
) -> None:
    for name, value in item.settings:
        wrong = None
        if name == "delivery" and value not in (types.IN_PERSON, types.ONLINE):
            wrong = "delivery must be in_person or online"
        elif name in ("max_groups", "weekly") and (_as_int(value) is None or _as_int(value) < 1):  # type: ignore[operator]
            wrong = f"{name} must be an integer ≥ 1"
        elif name == "teachers" and (_as_int(value) is None or _as_int(value) < 0):  # type: ignore[operator]
            wrong = "teachers must be an integer ≥ 0"
        elif name == "start_pattern" and value not in tables.patterns:
            wrong = f'unknown start pattern "{value}"'
        if wrong is not None:
            found.append(
                ConfigIssue("Modules", module.code, "sessions", f'cannot read "{text}": {wrong}')
            )


def _teachers(tables: _Tables, found: list[ConfigIssue]) -> None:
    for teacher in tables.by_type[types.TEACHER]:
        for text in split_list(tables.attribute(teacher, "modules")):
            code, kind = parse_teacher_item(text)
            module = tables.modules.get(code)
            if module is None:
                found.append(
                    ConfigIssue("Teachers", teacher.code, "modules", f'unknown code "{code}"')
                )
                continue
            kinds = {
                parse_session_item(t).code for t in split_list(tables.attribute(module, "sessions"))
            }
            if kind is not None and kind not in kinds:
                found.append(
                    ConfigIssue(
                        "Teachers",
                        teacher.code,
                        "modules",
                        f'"{text}": module "{code}" has no session type "{kind}"',
                    )
                )


def _groups(tables: _Tables, found: list[ConfigIssue]) -> None:
    for group in tables.by_type[types.STUDENT_GROUP]:
        level = tables.level_of_group(group)
        for code in split_list(tables.attribute(group, "options")):
            module = tables.modules.get(code)
            if module is None:
                continue  # an unknown code is reported by the sheet's reference check
            if not tables.attribute(module, "optional"):
                found.append(
                    ConfigIssue("Groups", group.code, "options", f'module "{code}" is not optional')
                )
            elif tables.attribute(module, "level") != level:
                found.append(
                    ConfigIssue(
                        "Groups",
                        group.code,
                        "options",
                        f'module "{code}" is at level "{tables.attribute(module, "level")}", '
                        f'the group is at level "{level}"',
                    )
                )
            elif group.parent not in tables.programmes_of(module):
                found.append(
                    ConfigIssue(
                        "Groups",
                        group.code,
                        "options",
                        f'module "{code}" is not offered to programme "{group.parent}"',
                    )
                )
