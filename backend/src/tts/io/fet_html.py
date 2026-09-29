"""Reader for the "groups" HTML timetable that FET exports (`docs/plan/phase-02-l6-fixture.md`).

Layout of the export:

- One `<table id="table_N">` per student group, named by `span.name` in its caption.
- A header row with one `th.xAxis` per day, then one body row per period, each starting with a
  `th.yAxis` holding the period's start time (`08:30`).
- One cell per day. `---` is an empty slot. A session spans `rowspan` periods, and the rows it
  covers hold an `<!-- span -->` comment in its column instead of a cell, so a comment still
  counts as a column.
- Cell lines, in order: for a joint session the comma-separated groups, then
  `<MODULE> <KIND>, [<time label>]` optionally followed by `, [ONLINE]`, then the teachers and,
  unless online, the room.
- A joint session appears in every one of its groups' tables, so sessions are deduplicated.

The grid position is authoritative. The time label is kept only to flag disagreements.
"""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from bs4 import BeautifulSoup, Comment, Tag

from tts.core.model import (
    Assignment,
    CapacityRule,
    Dataset,
    Day,
    Event,
    FixedRequirement,
    Period,
    PooledChoice,
    PooledRequirement,
    Reference,
    Resource,
    Result,
    StartPattern,
    TimeModel,
)
from tts.core.selectors import Selector, TagClause, format_selector
from tts.presets.academic_weekly import PRESET_NAME, types

_MODULE_LINE = re.compile(
    r"^(?P<module>\S+)\s+(?P<kind>[A-Z]+),\s*\[(?P<label>[^\]]*)\](?P<online>,\s*\[ONLINE\])?\s*$"
)
_LABEL_START = re.compile(r"(\d{1,2})\.(\d{2})\s*(am|pm)", re.IGNORECASE)
_EMPTY = "---"


class FetParseError(ValueError):
    """The HTML is not a FET groups export, or a cell does not have the expected shape."""


@dataclass(frozen=True, slots=True)
class FetSession:
    """One session, with its start given by grid position."""

    day: str
    day_index: int
    start: str
    start_index: int
    duration: int
    module: str
    kind: str
    groups: tuple[str, ...]
    teachers: tuple[str, ...]
    room: str | None
    online: bool
    label: str


@dataclass(frozen=True, slots=True)
class FetTimetable:
    institution: str
    days: tuple[str, ...]
    periods: tuple[str, ...]  # period start times, in order
    groups: tuple[str, ...]  # in file order
    sessions: tuple[FetSession, ...]  # sorted by day, start, module, kind, groups
    anomalies: tuple[str, ...]  # sessions whose time label disagrees with their grid position


def parse_fet_groups_html(path: Path | str) -> FetTimetable:
    """Read a FET groups export from a file."""
    return parse_fet_groups_html_text(Path(path).read_text(encoding="utf-8"))


def parse_fet_groups_html_text(html: str) -> FetTimetable:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", id=re.compile(r"^table_\d+$"))
    if not tables:
        raise FetParseError('no group tables found (expected <table id="table_N">)')

    institution = ""
    groups: list[str] = []
    days: tuple[str, ...] | None = None
    periods: tuple[str, ...] | None = None
    found: dict[tuple[object, ...], FetSession] = {}

    for table in tables:
        name_tag = table.select_one("caption span.name")
        if name_tag is None:
            raise FetParseError(f"{table.get('id')}: no group name (caption span.name)")
        group = name_tag.get_text(strip=True)
        groups.append(group)
        if not institution:
            institution_tag = table.select_one("caption span.institution")
            institution = institution_tag.get_text(strip=True) if institution_tag else ""

        table_days = tuple(th.get_text(strip=True) for th in table.select("thead th.xAxis"))
        if not table_days:
            raise FetParseError(f"{group}: no day headers")
        if days is None:
            days = table_days
        elif table_days != days:
            raise FetParseError(f"{group}: days differ from the first table")

        table_periods, sessions = _read_table(table, group, days)
        if periods is None:
            periods = table_periods
        elif table_periods != periods:
            raise FetParseError(f"{group}: periods differ from the first table")
        for session in sessions:
            key = (
                session.day_index,
                session.start_index,
                session.module,
                session.kind,
                session.groups,
                session.teachers,
                session.room,
            )
            found.setdefault(key, session)

    assert days is not None and periods is not None
    ordered = tuple(
        sorted(
            found.values(),
            key=lambda s: (s.day_index, s.start_index, s.module, s.kind, s.groups),
        )
    )
    return FetTimetable(
        institution=institution,
        days=days,
        periods=periods,
        groups=tuple(groups),
        sessions=ordered,
        anomalies=tuple(a for s in ordered if (a := _anomaly(s)) is not None),
    )


def _read_table(
    table: Tag, group: str, days: tuple[str, ...]
) -> tuple[tuple[str, ...], list[FetSession]]:
    body = table.find("tbody")
    if not isinstance(body, Tag):
        raise FetParseError(f"{group}: no table body")
    periods: list[str] = []
    sessions: list[FetSession] = []
    for row in body.find_all("tr", recursive=False):
        if "foot" in (row.get("class") or []):
            continue
        header = row.find("th", class_="yAxis")
        if header is None:
            raise FetParseError(f"{group}: a row has no period label (th.yAxis)")
        start = header.get_text(strip=True)
        start_index = len(periods)
        periods.append(start)

        column = 0
        for child in row.children:
            if isinstance(child, Comment):
                if child.strip() == "span":
                    column += 1
                continue
            if not isinstance(child, Tag) or child.name != "td":
                continue
            if column >= len(days):
                raise FetParseError(f"{group} {start}: more cells than days")
            lines = list(child.stripped_strings)
            if lines and lines != [_EMPTY]:
                where = f"{group} {days[column]} {start}"
                duration = int(str(child.get("rowspan", "1")))
                sessions.append(
                    _read_cell(
                        lines, group, where, days[column], column, start, start_index, duration
                    )
                )
            column += 1
        if column != len(days):
            raise FetParseError(f"{group} {start}: {column} columns, expected {len(days)}")
    return tuple(periods), sessions


def _read_cell(
    lines: list[str],
    group: str,
    where: str,
    day: str,
    day_index: int,
    start: str,
    start_index: int,
    duration: int,
) -> FetSession:
    position = next((i for i, line in enumerate(lines) if _MODULE_LINE.match(line)), None)
    if position is None:
        raise FetParseError(f'{where}: no "<MODULE> <KIND>, [time]" line in {lines!r}')
    if position > 1:
        raise FetParseError(f"{where}: more than one line before the session line: {lines!r}")
    header = _MODULE_LINE.match(lines[position])
    assert header is not None

    groups = _split(lines[0]) if position == 1 else [group]
    online = header["online"] is not None
    rest = lines[position + 1 :]
    if online:
        if len(rest) != 1:
            raise FetParseError(f"{where}: an online session has teachers only, got {rest!r}")
        teachers, room = _split(rest[0]), None
    else:
        if len(rest) != 2:
            raise FetParseError(f"{where}: expected teachers and a room, got {rest!r}")
        teachers, room = _split(rest[0]), rest[1]

    return FetSession(
        day=day,
        day_index=day_index,
        start=start,
        start_index=start_index,
        duration=duration,
        module=header["module"],
        kind=header["kind"],
        groups=tuple(sorted(groups)),
        teachers=tuple(sorted(teachers)),
        room=room,
        online=online,
        label=header["label"].strip(),
    )


def _split(line: str) -> list[str]:
    return [part.strip() for part in line.split(",") if part.strip()]


def _label_start(label: str) -> str | None:
    """The start time of a label such as `8.30am - 10.30am`, as `HH:MM`."""
    match = _LABEL_START.search(label)
    if match is None:
        return None
    hour, minute, meridiem = int(match[1]), match[2], match[3].lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"


def _anomaly(session: FetSession) -> str | None:
    label_start = _label_start(session.label)
    if label_start is None or label_start == session.start:
        return None
    return (
        f"{session.module} {session.kind} on {session.day} at {session.start}: "
        f"the label says [{session.label}]"
    )


# --- Conversion to a dataset ----------------------------------------------------------------------


class FetConversionError(ValueError):
    """The parsed timetable cannot be turned into a valid dataset."""


@dataclass(frozen=True, slots=True)
class Assumptions:
    """Values a FET export does not contain. Each one is recorded, never silently invented.

    The defaults are the L6 fixture's (`backend/tests/fixtures/l6/README.md`). Replace them when
    real data arrives.
    """

    group_size: int = 30
    auditorium_name: str = "Auditorium"
    auditorium_capacity: int = 250
    auditorium_room_type: str = "auditorium"
    other_room_type: str = "lab"
    campus: str = "MAIN"
    default_building: str = "GP"
    break_starts: tuple[str, ...] = ("12:30",)
    start_times: tuple[str, ...] = ("08:30", "10:30", "13:30", "15:30", "17:30")

    def describe(self) -> str:
        """The text recorded in the workbook's `_meta.assumptions`."""
        return "\n".join(
            [
                f"Group size: {self.group_size} for every group.",
                f'Room capacity: "{self.auditorium_name}" {self.auditorium_capacity}; every other '
                f"room {self.group_size} x the most groups seen in one event in that room.",
                f'Room types: "{self.auditorium_name}" is {self.auditorium_room_type}, '
                f"every other room is {self.other_room_type}.",
                'Buildings: the suffix after "-" in a room name (for example "[2LA] -GP"); '
                f'rooms without one are in "{self.default_building}", under campus '
                f'"{self.campus}".',
                f"Breaks: periods starting at {', '.join(self.break_starts)} are breaks.",
                f"Start pattern: events may start at {', '.join(self.start_times)}.",
                "Period length: the gap to the next period; the last period repeats the "
                "previous gap.",
                "Constraints: none are known from the export. Only the implicit hard "
                "constraints apply.",
            ]
        )


def to_dataset(
    fet: FetTimetable,
    preset: str = PRESET_NAME,
    assumptions: Assumptions | None = None,
) -> tuple[Dataset, Result]:
    """The dataset a FET export describes, and its original placements as a result.

    Structure: one level and programmes read from the group names (`<programme> / <group>`, the
    level being the programme's first word), groups under their programme, a campus and
    buildings, rooms, teachers, modules, one event per session and a room requirement for every
    session that is not online.
    """
    if preset != PRESET_NAME:
        raise FetConversionError(f'unsupported preset "{preset}"')
    assume = assumptions or Assumptions()

    time_model, period_codes, day_codes = _time_model(fet, assume)
    resources = _resources(fet, assume)
    room_types = {r.code: r.tag(types.ROOM_TYPE_TAG) for r in resources if r.type == types.ROOM}

    modules = sorted({s.module for s in fet.sessions})
    events: list[Event] = []
    fixed: list[FixedRequirement] = []
    pooled: list[PooledRequirement] = []
    assignments: list[Assignment] = []
    numbering: Counter[tuple[str, str]] = Counter()
    for session in fet.sessions:
        numbering[(session.module, session.kind)] += 1
        number = numbering[(session.module, session.kind)]
        code = f"{session.module}-{session.kind}-{number:02d}"
        events.append(
            Event(
                code=code,
                kind=session.kind,
                duration=session.duration,
                start_pattern=f"{session.duration}H",
                reference=session.module,
                delivery=types.ONLINE if session.online else types.IN_PERSON,
                tags={"fet_label": session.label},
            )
        )
        fixed += [FixedRequirement(event=code, resource=g) for g in session.groups]
        fixed += [FixedRequirement(event=code, resource=t) for t in session.teachers]
        chosen: tuple[PooledChoice, ...] = ()
        if session.room is not None:
            room_type = room_types[session.room]
            if room_type is None:
                raise FetConversionError(f'room "{session.room}" has no room type')
            room_filter = Selector((TagClause(types.ROOM_TYPE_TAG, room_type),))
            pooled.append(
                PooledRequirement(
                    event=code,
                    resource_type=types.ROOM,
                    filter=format_selector(room_filter),
                    capacity_rule=CapacityRule(
                        kind="sum_of_fixed", resource_type=types.STUDENT_GROUP
                    ),
                )
            )
            chosen = (PooledChoice(ordinal=0, resources=(session.room,)),)
        assignments.append(
            Assignment(
                event=code,
                day=day_codes[session.day_index],
                start_period=period_codes[session.start_index],
                chosen=chosen,
            )
        )

    dataset = Dataset(
        preset=PRESET_NAME,
        resource_types=types.RESOURCE_TYPES,
        resources=tuple(resources),
        reference_types=types.REFERENCE_TYPES,
        references=tuple(Reference(code=m, type=types.MODULE, name=m) for m in modules),
        time=time_model,
        events=tuple(events),
        fixed=tuple(fixed),
        pooled=tuple(pooled),
    )
    issues = dataset.validate_invariants()
    if issues:
        raise FetConversionError("; ".join(f"{i.table} {i.key}: {i.message}" for i in issues))
    return dataset, Result(assignments=tuple(assignments))


def _minutes(label: str) -> int:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", label)
    if match is None:
        raise FetConversionError(f'period label "{label}" is not HH:MM')
    return int(match[1]) * 60 + int(match[2])


def _clock(minutes: int) -> time:
    if not 0 <= minutes < 24 * 60:
        raise FetConversionError("a period ends after midnight")
    return time(minutes // 60, minutes % 60)


def _time_model(fet: FetTimetable, assume: Assumptions) -> tuple[TimeModel, list[str], list[str]]:
    day_codes = [name[:3] for name in fet.days]
    if len(set(day_codes)) != len(day_codes):
        raise FetConversionError(f"day names {fet.days} do not have distinct 3-letter codes")
    period_codes = [f"P{i + 1:02d}" for i in range(len(fet.periods))]
    starts = [_minutes(label) for label in fet.periods]
    gaps = [b - a for a, b in zip(starts, starts[1:], strict=False)]
    ends = [*starts[1:], starts[-1] + (gaps[-1] if gaps else 60)]

    by_label = dict(zip(fet.periods, period_codes, strict=True))
    missing = [t for t in assume.start_times if t not in by_label]
    if missing:
        raise FetConversionError(f"start times {missing} are not periods of the export")
    start_periods = tuple(by_label[t] for t in assume.start_times)

    model = TimeModel(
        days=tuple(
            Day(code=code, label=name, order=i + 1)
            for i, (code, name) in enumerate(zip(day_codes, fet.days, strict=True))
        ),
        periods=tuple(
            Period(
                code=code,
                start=_clock(start),
                end=_clock(end),
                order=i + 1,
                is_break=label in assume.break_starts,
            )
            for i, (code, label, start, end) in enumerate(
                zip(period_codes, fet.periods, starts, ends, strict=True)
            )
        ),
        start_patterns=tuple(
            StartPattern(code=f"{d}H", duration=d, start_periods=start_periods)
            for d in sorted({s.duration for s in fet.sessions})
        ),
    )
    return model, period_codes, day_codes


def _resources(fet: FetTimetable, assume: Assumptions) -> list[Resource]:
    resources: list[Resource] = []

    programmes: dict[str, str] = {}  # programme code -> level code
    for group in fet.groups:
        programme, separator, _ = group.partition(" / ")
        if not separator or not programme.strip():
            raise FetConversionError(f'group "{group}" is not named "<programme> / <group>"')
        programmes.setdefault(programme, programme.split()[0])
    for level in sorted(set(programmes.values())):
        resources.append(Resource(code=level, type=types.LEVEL, name=level))
    for programme, level in programmes.items():
        resources.append(
            Resource(code=programme, type=types.PROGRAMME, name=programme, parent=level)
        )
    for group in fet.groups:
        resources.append(
            Resource(
                code=group,
                type=types.STUDENT_GROUP,
                name=group,
                parent=group.partition(" / ")[0],
                capacity=assume.group_size,
            )
        )

    for teacher in sorted({t for s in fet.sessions for t in s.teachers}):
        resources.append(Resource(code=teacher, type=types.TEACHER, name=teacher))

    most_groups: dict[str, int] = {}
    for session in fet.sessions:
        if session.room is not None:
            most_groups[session.room] = max(most_groups.get(session.room, 0), len(session.groups))
    building_of = {room: _building(room, assume) for room in most_groups}
    resources.append(Resource(code=assume.campus, type=types.CAMPUS, name=assume.campus))
    for building in sorted(set(building_of.values())):
        resources.append(
            Resource(code=building, type=types.BUILDING, name=building, parent=assume.campus)
        )
    for room, count in sorted(most_groups.items()):
        is_auditorium = room == assume.auditorium_name
        room_type = assume.auditorium_room_type if is_auditorium else assume.other_room_type
        resources.append(
            Resource(
                code=room,
                type=types.ROOM,
                name=room,
                parent=building_of[room],
                capacity=assume.auditorium_capacity if is_auditorium else assume.group_size * count,
                tags={types.ROOM_TYPE_TAG: room_type},
            )
        )
    return resources


def _building(room: str, assume: Assumptions) -> str:
    match = re.search(r"-\s*([A-Za-z0-9]+)\s*$", room)
    return match[1] if match else assume.default_building
