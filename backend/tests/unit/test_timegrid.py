from datetime import time

import pytest

from tts.core.model import Day, Event, Period, StartPattern, TimeModel
from tts.core.timegrid import TimeGrid, TimeGridError, allowed_starts, covered_slots


def make_time(
    periods: int = 4,
    days: int = 2,
    breaks: tuple[int, ...] = (),
    patterns: tuple[StartPattern, ...] | None = None,
) -> TimeModel:
    """`days` days d1.. with `periods` periods p1.. (1-based). `breaks` lists 1-based periods."""
    return TimeModel(
        days=tuple(Day(code=f"d{i}", order=i) for i in range(1, days + 1)),
        periods=tuple(
            Period(
                code=f"p{i}",
                start=time(7 + i, 0),
                end=time(8 + i, 0),
                order=i,
                is_break=i in breaks,
            )
            for i in range(1, periods + 1)
        ),
        start_patterns=patterns
        if patterns is not None
        else (
            StartPattern(
                code="all", duration=1, start_periods=tuple(f"p{i}" for i in range(1, periods + 1))
            ),
        ),
    )


def event(duration: int, pattern: str = "all") -> Event:
    return Event(code="e", kind="K", duration=duration, start_pattern=pattern)


def test_covered_slots() -> None:
    assert list(covered_slots(5, 3)) == [5, 6, 7]
    assert list(covered_slots(0, 1)) == [0]


def test_slot_index_follows_day_and_period_order() -> None:
    grid = TimeGrid(make_time(periods=4, days=3))
    assert grid.periods_per_day == 4
    assert grid.slot_count == 12
    assert grid.slot("d1", "p1") == 0
    assert grid.slot("d1", "p4") == 3
    assert grid.slot("d2", "p1") == 4
    assert grid.slot("d3", "p2") == 9
    assert grid.day_index(9) == 2
    assert grid.period_index(9) == 1


def test_slot_and_codes_round_trip() -> None:
    grid = TimeGrid(make_time(periods=4, days=3))
    for t in range(grid.slot_count):
        assert grid.slot(*grid.codes(t)) == t


def test_codes_rejects_a_slot_outside_the_grid() -> None:
    grid = TimeGrid(make_time(periods=2, days=1))
    with pytest.raises(TimeGridError):
        grid.codes(2)
    with pytest.raises(TimeGridError):
        grid.codes(-1)


def test_unknown_codes_raise_a_typed_error() -> None:
    grid = TimeGrid(make_time())
    with pytest.raises(TimeGridError, match='unknown day "dx"'):
        grid.slot("dx", "p1")
    with pytest.raises(TimeGridError, match='unknown period "px"'):
        grid.slot("d1", "px")
    with pytest.raises(TimeGridError, match='unknown start pattern "nope"'):
        grid.allowed_starts(event(1, pattern="nope"))


def test_indexes_follow_order_not_input_order() -> None:
    tm = TimeModel(
        days=(Day(code="late", order=2), Day(code="early", order=1)),
        periods=(
            Period(code="b", start=time(9), end=time(10), order=2),
            Period(code="a", start=time(8), end=time(9), order=1),
        ),
        start_patterns=(StartPattern(code="s", duration=1, start_periods=("a", "b")),),
    )
    grid = TimeGrid(tm)
    assert grid.slot("early", "a") == 0
    assert grid.slot("late", "b") == 3


def test_duration_one_may_start_in_every_period_of_every_day() -> None:
    grid = TimeGrid(make_time(periods=4, days=2))
    assert grid.allowed_starts(event(1)) == (0, 1, 2, 3, 4, 5, 6, 7)


def test_an_event_may_not_run_past_the_end_of_the_day() -> None:
    grid = TimeGrid(make_time(periods=4, days=2))
    # Duration 2: the last start in a day is period 3. Period 4 would cross into the next day.
    assert grid.allowed_starts(event(2)) == (0, 1, 2, 4, 5, 6)
    # Duration 3: only periods 1 and 2 can start.
    assert grid.allowed_starts(event(3)) == (0, 1, 4, 5)


def test_a_duration_longer_than_the_day_has_no_start() -> None:
    assert TimeGrid(make_time(periods=4, days=2)).allowed_starts(event(5)) == ()


def test_a_break_inside_the_span_forbids_the_start() -> None:
    grid = TimeGrid(make_time(periods=5, days=1, breaks=(3,)))
    # Duration 2 covers p2+p3 or p3+p4 when starting at p2 or p3: both touch the break at p3.
    assert grid.allowed_starts(event(2)) == (0, 3)
    assert grid.is_break(2)
    assert not grid.is_break(1)


def test_starting_on_a_break_is_forbidden_even_for_duration_one() -> None:
    grid = TimeGrid(make_time(periods=3, days=1, breaks=(2,)))
    assert grid.allowed_starts(event(1)) == (0, 2)


def test_a_pattern_restricts_the_start_periods() -> None:
    pattern = StartPattern(code="odd", duration=2, start_periods=("p1", "p3"))
    grid = TimeGrid(make_time(periods=4, days=2, patterns=(pattern,)))
    assert grid.allowed_starts(event(2, "odd")) == (0, 2, 4, 6)


def test_a_pattern_restricts_the_days() -> None:
    pattern = StartPattern(code="d2only", duration=1, start_periods=("p1", "p2"), days=("d2",))
    grid = TimeGrid(make_time(periods=4, days=3, patterns=(pattern,)))
    assert grid.allowed_starts(event(1, "d2only")) == (4, 5)


def test_a_pattern_with_no_days_uses_every_day() -> None:
    pattern = StartPattern(code="s", duration=1, start_periods=("p1",))
    assert TimeGrid(make_time(periods=2, days=3, patterns=(pattern,))).allowed_starts(
        event(1, "s")
    ) == (0, 2, 4)


def test_repeated_pattern_entries_do_not_repeat_starts() -> None:
    pattern = StartPattern(code="s", duration=1, start_periods=("p1", "p1"), days=("d1", "d1"))
    assert TimeGrid(make_time(periods=2, days=2, patterns=(pattern,))).allowed_starts(
        event(1, "s")
    ) == (0,)


def test_a_two_hour_pattern_on_a_fourteen_period_week() -> None:
    """Shape of the L6 grid: 6 days x 14 periods, a break at period 5, five 2-period starts."""
    pattern = StartPattern(code="2H", duration=2, start_periods=("p1", "p3", "p6", "p8", "p10"))
    tm = make_time(periods=14, days=6, breaks=(5,), patterns=(pattern,))
    starts = allowed_starts(event(2, "2H"), tm)
    assert len(starts) == 30
    assert starts[:5] == (0, 2, 5, 7, 9)
    assert all(t % 14 in (0, 2, 5, 7, 9) for t in starts)
    # p3+p4 stay clear of the break at p5, and p6+p7 start right after it.
    assert TimeGrid(tm).slot("d2", "p6") == 14 + 5
    assert 14 + 5 in starts


def test_module_level_allowed_starts_matches_the_grid() -> None:
    tm = make_time(periods=4, days=2)
    assert allowed_starts(event(2), tm) == TimeGrid(tm).allowed_starts(event(2))


def test_a_pattern_naming_an_unknown_period_or_day_raises() -> None:
    bad_period = StartPattern(code="s", duration=1, start_periods=("nope",))
    with pytest.raises(TimeGridError, match='unknown period "nope"'):
        TimeGrid(make_time(patterns=(bad_period,))).allowed_starts(event(1, "s"))
    bad_day = StartPattern(code="s", duration=1, start_periods=("p1",), days=("nope",))
    with pytest.raises(TimeGridError, match='unknown day "nope"'):
        TimeGrid(make_time(patterns=(bad_day,))).allowed_starts(event(1, "s"))


def test_day_and_period_numbers_follow_order() -> None:
    grid = TimeGrid(make_time(periods=4, days=3))
    assert [grid.day_number(f"d{i}") for i in (1, 2, 3)] == [0, 1, 2]
    assert [grid.period_number(f"p{i}") for i in (1, 4)] == [0, 3]
    with pytest.raises(TimeGridError):
        grid.day_number("dx")
    with pytest.raises(TimeGridError):
        grid.period_number("px")
