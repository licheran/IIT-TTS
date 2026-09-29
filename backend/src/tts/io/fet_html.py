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
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Comment, Tag

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
