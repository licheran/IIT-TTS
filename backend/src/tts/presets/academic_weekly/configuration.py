"""From configuration to demands (ADR-0007, spec 02 section 6.1, spec 03 section 2a).

A configured academic dataset holds no activities. Its `Session` rows say which session types a
module has (a blank setting takes the session type's), its teachers which modules they teach, its
programmes which groups they contain, and its groups which optional modules they take. `demands`
turns that into the core's demands, one per Session row, and `configuration_issues` finds the
mistakes the sheet columns cannot (an option that is not optional, a teacher for a session type the
module lacks, ...).

Both are pure functions of a dataset. They hold no scheduling logic: what a demand asks for is
data, and the solver decides the rest.
"""

import re
from collections import defaultdict

from tts.core.model import (
    CapacityRule,
    Constraint,
    Dataset,
    Demand,
    PooledSpec,
    Reference,
    Resource,
)
from tts.core.selectors import CodeClause, KindClause, RefClause, Selector, format_selector
from tts.core.sheets import ConfigIssue
from tts.presets.academic_weekly import types

LIST_SEP = ";"
ROOM_ORDINAL = 0
TEACHER_ORDINAL = 1


def split_list(text: object) -> tuple[str, ...]:
    """The items of a `;`-separated attribute (none for a missing or blank one)."""
    if not isinstance(text, str):
        return ()
    return tuple(part.strip() for part in text.split(LIST_SEP) if part.strip())


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
        self.sessions: dict[str, list[Reference]] = defaultdict(list)  # Session rows by module
        for row in sorted(dataset.references, key=lambda r: r.code):
            if row.type == types.SESSION:
                self.sessions[str(dict(row.attributes).get("module"))].append(row)
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


def _setting(session_type: Reference, row: Reference, name: str, tables: _Tables) -> object:
    """The Session row's own value, else the session type's."""
    own = tables.attribute(row, name)
    return own if own is not None else tables.attribute(session_type, name)


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
    """One demand for each Session row of the configuration.

    Rows that cannot be made into a demand (an unknown module or session type, a setting that is
    not a number) are skipped: `configuration_issues` and the sheet checks report them.
    """
    tables = _Tables(dataset)
    found: list[Demand] = []
    for module in sorted(tables.modules.values(), key=lambda r: r.code):
        participants = participants_of(tables, module)
        for row in tables.sessions.get(module.code, []):
            session_type = tables.session_types.get(str(tables.attribute(row, "session_type")))
            if session_type is None:
                continue
            made = _demand(tables, module, session_type, row, participants)
            if made is not None:
                found.append(made)
    return tuple(found)


def _demand(
    tables: _Tables,
    module: Reference,
    session_type: Reference,
    row: Reference,
    participants: tuple[str, ...],
) -> Demand | None:
    pattern = _setting(session_type, row, "start_pattern", tables)
    start = tables.patterns.get(str(pattern))
    if start is None:
        return None
    limit = _as_int(_setting(session_type, row, "max_groups", tables))
    weekly = _as_int(_setting(session_type, row, "weekly", tables))
    teachers = _as_int(_setting(session_type, row, "teachers", tables))
    delivery = _setting(session_type, row, "delivery", tables) or types.IN_PERSON
    room_type = _setting(session_type, row, "room_type", tables)
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
        # A session carries its type's tags; its module's tags win over them, and its row's win
        # over both.
        tags=tuple({**dict(session_type.tags), **dict(module.tags), **dict(row.tags)}.items()),
    )


FAIR_WEIGHT = 2
CONTINUITY_WEIGHT = 3


def derived_constraints(dataset: Dataset) -> tuple[Constraint, ...]:
    """The fairness rules the configuration implies (spec 04 section 3, ADR-0008).

    - `LOAD-<teacher>`: a hard weekly cap in periods, for each teacher with `max_hours`;
    - `FAIR-<module>`: soft, the weekly load of the module's teachers is equal, for each module
      with two or more teachers;
    - `CONT-<module>-<kind>`: soft, a group keeps one teacher for a module's sessions of a kind,
      for each Session row whose teachers are two or more.

    They are never stored; a stored constraint with the same code takes their place.
    """
    tables = _Tables(dataset)
    found: list[Constraint] = []
    for teacher in sorted(tables.by_type[types.TEACHER], key=lambda r: r.code):
        hours = _as_int(tables.attribute(teacher, "max_hours"))
        if hours is not None and hours >= 0:
            found.append(
                Constraint(
                    code=f"LOAD-{teacher.code}",
                    type="max_load",
                    scope=format_selector(Selector((CodeClause((teacher.code,)),))),
                    params={"max": hours, "unit": "periods"},
                    hard=True,
                )
            )
    for module in sorted(tables.modules.values(), key=lambda r: r.code):
        pool = _module_teachers(tables, module.code)
        if len(pool) >= 2:
            found.append(
                Constraint(
                    code=f"FAIR-{module.code}",
                    type="balance_load",
                    scope=format_selector(Selector((CodeClause(pool),))),
                    params={"unit": "periods"},
                    hard=False,
                    weight=FAIR_WEIGHT,
                )
            )
        for row in tables.sessions.get(module.code, []):
            kind = str(tables.attribute(row, "session_type"))
            if (
                kind not in tables.session_types
                or len(_teacher_pool(tables, module.code, kind)) < 2
            ):
                continue
            found.append(
                Constraint(
                    code=f"CONT-{module.code}-{kind}",
                    type="same_resource",
                    scope=format_selector(Selector((RefClause(module.code), KindClause((kind,))))),
                    params={"type": types.TEACHER, "per": types.STUDENT_GROUP},
                    hard=False,
                    weight=CONTINUITY_WEIGHT,
                )
            )
    return tuple(found)


def _module_teachers(tables: _Tables, module: str) -> tuple[str, ...]:
    """The teachers that list the module for any kind."""
    return tuple(
        sorted(
            teacher.code
            for teacher in tables.by_type[types.TEACHER]
            if any(
                parse_teacher_item(item)[0] == module
                for item in split_list(tables.attribute(teacher, "modules"))
            )
        )
    )


def configuration_issues(dataset: Dataset) -> list[ConfigIssue]:
    """What is wrong with the configuration, by sheet, row code and column (spec 03 section 3)."""
    tables = _Tables(dataset)
    found: list[ConfigIssue] = []
    _session_types(tables, found)
    _modules(tables, found)
    _session_rows(tables, found)
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
        taken_by = participants_of(tables, module)
        if taken_by and not tables.sessions.get(module.code):
            found.append(
                ConfigIssue(
                    "Modules",
                    module.code,
                    "code",
                    f'module "{module.code}" is taken by {len(taken_by)} groups but has no '
                    "Session rows, so nothing is scheduled for it",
                    warning=True,
                )
            )


def _session_rows(tables: _Tables, found: list[ConfigIssue]) -> None:
    for module_code in sorted(tables.sessions):
        for row in tables.sessions[module_code]:
            session_type = tables.session_types.get(str(tables.attribute(row, "session_type")))
            if session_type is None:
                continue  # an unknown code is reported by the sheet's reference check
            delivery = _setting(session_type, row, "delivery", tables) or types.IN_PERSON
            if delivery == types.ONLINE and tables.attribute(row, "room_type"):
                found.append(
                    ConfigIssue(
                        "Session",
                        row.code,
                        "room_type",
                        "an online session cannot have a room type",
                    )
                )
            elif delivery != types.ONLINE and not _setting(session_type, row, "room_type", tables):
                found.append(
                    ConfigIssue(
                        "Session",
                        row.code,
                        "room_type",
                        "required: the session is in person and neither the row nor session type "
                        f'"{session_type.code}" gives one',
                    )
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
            kinds = {str(tables.attribute(r, "session_type")) for r in tables.sessions[module.code]}
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
