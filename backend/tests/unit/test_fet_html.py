import json
from collections import Counter
from pathlib import Path

import pytest

from tts.io.fet_html import (
    FetParseError,
    parse_fet_groups_html,
    parse_fet_groups_html_text,
)

L6 = Path(__file__).resolve().parents[1] / "fixtures" / "l6"

SPAN = "<!-- span -->"
EMPTY = "<td>---</td>"


def cell(*lines: str, rowspan: int = 1) -> str:
    span = f' rowspan="{rowspan}"' if rowspan != 1 else ""
    return f"<td{span}>" + "".join(f"{line}<br />" for line in lines) + "</td>"


def table(number: int, group: str, rows: list[tuple[str, list[str]]], days: str = "Mon Tue") -> str:
    head = "".join(f'<th class="xAxis">{d}</th>' for d in days.split())
    body = "".join(
        f'<tr><th class="yAxis">{start}</th>{"".join(cells)}</tr>' for start, cells in rows
    )
    return (
        f'<table id="table_{number}"><caption><span class="institution">Inst</span><br />'
        f'<span class="name">{group}</span></caption><thead><tr><td></td>{head}</tr></thead>'
        f"<tbody>{body}"
        '<tr class="foot"><td></td><td colspan="2">generated</td></tr></tbody></table>'
    )


def page(*tables: str) -> str:
    info = "<table><tr><th>Institution name:</th><td>x</td></tr></table>"
    return f"<html><body>{info}{''.join(tables)}</body></html>"


LEC = "M1 LEC, [8.30am - 10.30am]"


def test_a_session_spans_rows_and_a_span_comment_counts_as_a_column() -> None:
    html = page(
        table(
            2,
            "G1",
            [
                ("08:30", [cell(LEC, "T1", "Room A", rowspan=2), EMPTY]),
                ("09:30", [SPAN, cell("M2 TUT, [9.30am - 10.30am]", "T2", "Room B")]),
                ("10:30", [EMPTY, EMPTY]),
            ],
        )
    )
    fet = parse_fet_groups_html_text(html)
    assert fet.days == ("Mon", "Tue")
    assert fet.periods == ("08:30", "09:30", "10:30")
    assert fet.groups == ("G1",)
    first, second = fet.sessions
    assert (first.day, first.day_index, first.start, first.start_index, first.duration) == (
        "Mon",
        0,
        "08:30",
        0,
        2,
    )
    assert (first.module, first.kind, first.groups, first.teachers, first.room) == (
        "M1",
        "LEC",
        ("G1",),
        ("T1",),
        "Room A",
    )
    # The second cell of the "09:30" row belongs to Tuesday because the comment took Monday.
    assert (second.day, second.day_index, second.start, second.duration) == ("Tue", 1, "09:30", 1)
    assert second.room == "Room B"


def test_a_joint_session_lists_its_groups_and_appears_once() -> None:
    joint = cell("A, B", LEC, "T1, T2", "Hall", rowspan=2)
    solo_a = cell("M2 TUT, [10.30am -12.30pm]", "T3", "Room A")
    solo_b = cell("M2 TUT, [10.30am -12.30pm]", "T4", "Room B")
    rows_a = [("08:30", [joint, EMPTY]), ("09:30", [SPAN, EMPTY]), ("10:30", [solo_a, EMPTY])]
    rows_b = [("08:30", [joint, EMPTY]), ("09:30", [SPAN, EMPTY]), ("10:30", [solo_b, EMPTY])]
    fet = parse_fet_groups_html_text(page(table(2, "A", rows_a), table(4, "B", rows_b)))
    assert fet.groups == ("A", "B")
    assert [(s.module, s.kind, s.groups, s.teachers) for s in fet.sessions] == [
        ("M1", "LEC", ("A", "B"), ("T1", "T2")),
        ("M2", "TUT", ("A",), ("T3",)),
        ("M2", "TUT", ("B",), ("T4",)),
    ]


def test_an_online_session_has_no_room() -> None:
    online = cell("M3 LEC, [8.30am - 10.30am], [ONLINE]", "T1, T2", rowspan=2)
    fet = parse_fet_groups_html_text(
        page(table(2, "G1", [("08:30", [online, EMPTY]), ("09:30", [SPAN, EMPTY])]))
    )
    (session,) = fet.sessions
    assert session.online
    assert session.room is None
    assert session.teachers == ("T1", "T2")


def test_sessions_are_sorted_by_day_then_start_then_module() -> None:
    late = cell("B1 LEC, [10.30am - 11.30am]", "T", "R")
    early = cell("A1 LEC, [8.30am - 9.30am]", "T", "R")
    rows = [("08:30", [EMPTY, early]), ("09:30", [late, EMPTY]), ("10:30", [EMPTY, EMPTY])]
    fet = parse_fet_groups_html_text(page(table(2, "G", rows)))
    assert [(s.day_index, s.start_index, s.module) for s in fet.sessions] == [
        (0, 1, "B1"),
        (1, 0, "A1"),
    ]


def test_a_label_that_disagrees_with_the_grid_is_reported_but_the_grid_wins() -> None:
    odd = cell("M1 LEC, [6.00pm -8.00pm]", "T", "R", rowspan=2)
    rows = [("17:30", [odd, EMPTY]), ("18:30", [SPAN, EMPTY])]
    fet = parse_fet_groups_html_text(page(table(2, "G", rows)))
    assert fet.sessions[0].start == "17:30"
    assert fet.sessions[0].label == "6.00pm -8.00pm"
    assert fet.anomalies == ("M1 LEC on Mon at 17:30: the label says [6.00pm -8.00pm]",)


@pytest.mark.parametrize(
    ("label", "grid"),
    [
        ("8.30am - 10.30am", "08:30"),
        ("10.30am -12.30pm", "10:30"),
        ("12.30pm - 2.30pm", "12:30"),
        ("1.30pm - 3.30pm", "13:30"),
        ("12.00am - 1.00am", "00:00"),
    ],
)
def test_matching_labels_are_not_anomalies(label: str, grid: str) -> None:
    c = cell(f"M1 LEC, [{label}]", "T", "R")
    fet = parse_fet_groups_html_text(page(table(2, "G", [(grid, [c, EMPTY])])))
    assert fet.anomalies == ()


@pytest.mark.parametrize(
    ("cell_html", "fragment"),
    [
        (cell("T1", "Room"), 'no "<MODULE> <KIND>, [time]" line'),
        (cell("A", "B", LEC, "T", "R"), "more than one line before"),
        (cell(LEC, "T1"), "expected teachers and a room"),
        (cell(LEC, "T1", "R", "extra"), "expected teachers and a room"),
        (
            cell("M1 LEC, [8.30am - 10.30am], [ONLINE]", "T1", "R"),
            "online session has teachers only",
        ),
    ],
)
def test_a_cell_of_the_wrong_shape_is_an_error_naming_where(cell_html: str, fragment: str) -> None:
    html = page(table(2, "G1", [("08:30", [cell_html, EMPTY])]))
    with pytest.raises(FetParseError) as caught:
        parse_fet_groups_html_text(html)
    assert fragment in str(caught.value)
    assert "G1 Mon 08:30" in str(caught.value) or "more than one line" in str(caught.value)


def test_a_row_with_the_wrong_number_of_columns_is_an_error() -> None:
    short = page(table(2, "G1", [("08:30", [EMPTY])]))
    with pytest.raises(FetParseError, match="1 columns, expected 2"):
        parse_fet_groups_html_text(short)
    long = page(table(2, "G1", [("08:30", [EMPTY, EMPTY, EMPTY])]))
    with pytest.raises(FetParseError, match="more cells than days"):
        parse_fet_groups_html_text(long)


def test_tables_that_disagree_on_days_or_periods_are_an_error() -> None:
    a = table(2, "A", [("08:30", [EMPTY, EMPTY])])
    with pytest.raises(FetParseError, match="days differ"):
        parse_fet_groups_html_text(page(a, table(4, "B", [("08:30", [EMPTY])], days="Mon")))
    with pytest.raises(FetParseError, match="periods differ"):
        parse_fet_groups_html_text(page(a, table(4, "B", [("09:30", [EMPTY, EMPTY])])))


def test_html_without_group_tables_is_an_error() -> None:
    with pytest.raises(FetParseError, match="no group tables"):
        parse_fet_groups_html_text("<html><body><table><tr><td>x</td></tr></table></body></html>")


def test_a_file_can_be_parsed_by_path(tmp_path: Path) -> None:
    path = tmp_path / "export.html"
    path.write_text(page(table(2, "G1", [("08:30", [cell(LEC, "T", "R"), EMPTY])])), "utf-8")
    assert len(parse_fet_groups_html(path).sessions) == 1
    assert len(parse_fet_groups_html(str(path)).sessions) == 1


# --- The real export, against the figures in expected.json -------------------------------------


@pytest.fixture(scope="module")
def expected() -> dict[str, object]:
    return json.loads((L6 / "expected.json").read_text("utf-8"))  # type: ignore[no-any-return]


@pytest.fixture(scope="module")
def fet():  # type: ignore[no-untyped-def]
    return parse_fet_groups_html(L6 / "fet-groups-export.html")


def test_l6_structure_matches_expected(fet, expected) -> None:  # type: ignore[no-untyped-def]
    assert list(fet.groups) == expected["groups"]
    assert list(fet.days) == expected["time"]["days"]
    assert list(fet.periods) == expected["time"]["periods"]
    assert fet.institution == "Informatics Institute of Technology"


def test_l6_session_counts_match_expected(fet, expected) -> None:  # type: ignore[no-untyped-def]
    counts = expected["counts"]
    assert len(fet.sessions) == counts["events"]
    assert dict(Counter(s.kind for s in fet.sessions)) == counts["events_by_kind"]
    assert sum(s.online for s in fet.sessions) == counts["online_events"]
    assert sum(s.room is None for s in fet.sessions) == counts["events_without_room"]
    assert dict(Counter(str(s.duration) for s in fet.sessions)) == expected["time"]["durations"]
    assert {s.start for s in fet.sessions} == set(expected["time"]["start_periods_used"])
    by_day = Counter(s.day for s in fet.sessions)
    assert {d: by_day.get(d, 0) for d in fet.days} == expected["time"]["events_by_day"]


def test_l6_groups_rooms_teachers_modules_match_expected(fet, expected) -> None:  # type: ignore[no-untyped-def]
    periods: Counter[str] = Counter()
    for s in fet.sessions:
        for g in s.groups:
            periods[g] += s.duration
    assert dict(periods) == expected["group_periods_per_week"]

    rooms: dict[str, dict[str, int]] = {}
    for s in fet.sessions:
        if s.room is not None:
            info = rooms.setdefault(s.room, {"events": 0, "max_groups_in_one_event": 0})
            info["events"] += 1
            info["max_groups_in_one_event"] = max(info["max_groups_in_one_event"], len(s.groups))
    assert rooms == expected["rooms"]

    teachers = Counter(t for s in fet.sessions for t in s.teachers)
    assert dict(teachers) == expected["teachers"]
    assert len(teachers) == expected["counts"]["teachers"]

    modules: dict[str, dict[str, object]] = {}
    for s in fet.sessions:
        info = modules.setdefault(s.module, {"events": 0, "LEC": 0, "TUT": 0, "groups": set()})
        info["events"] += 1  # type: ignore[operator]
        info[s.kind] += 1  # type: ignore[operator]
        info["groups"] |= set(s.groups)  # type: ignore[operator]
    for code, info in expected["modules"].items():
        found = modules[code]
        assert found["events"] == info["events"]
        assert (found["LEC"], found["TUT"]) == (info["LEC"], info["TUT"])
        assert found["groups"] == set(info["groups"])
    assert set(modules) == set(expected["modules"])

    assert max(len(s.groups) for s in fet.sessions) == expected["max_groups_in_one_event"]
    assert max(len(s.teachers) for s in fet.sessions) == expected["max_teachers_in_one_event"]


def test_l6_has_exactly_the_known_anomaly(fet, expected) -> None:  # type: ignore[no-untyped-def]
    (known,) = expected["known_anomalies"]
    event = known["event"]
    assert fet.anomalies == (
        f"{event['module']} {event['kind']} on {event['day']} at {event['start']}: "
        "the label says [6.00pm -8.00pm]",
    )
    (session,) = [
        s for s in fet.sessions if (s.module, s.kind, s.day) == ("6CCGD007C", "LEC", "Thursday")
    ]
    assert session.start == "17:30"
    assert session.online
