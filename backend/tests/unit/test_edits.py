"""A run's timetable with the edits applied (`core/demands.with_edits`, ADR-0007)."""

from fixtures import at, demand, make_dataset, pick, res
from tts.core.demands import with_edits
from tts.core.model import CapacityRule, CreatedEvent, Dataset, Event, Pin, PooledSpec, Result
from tts.core.verifier import hard_violations, verify


def groups(n: int) -> list:  # type: ignore[type-arg]
    return [res(f"g{i}", "G", capacity=10) for i in range(1, n + 1)]


def scene(edit_pin: Pin | None = None, edit_groups=("g1", "g2")) -> tuple[Dataset, Result]:  # type: ignore[no-untyped-def]
    """Two sessions the solver made (d1-K-01 for g1 and g2, d1-K-02 for g3 and g4), and an edit
    of the first one: a declared event with the same code."""
    rooms = PooledSpec(resource_type="R", capacity_rule=CapacityRule.parse("sum_of_fixed:G"))
    teachers = PooledSpec(resource_type="T", ordinal=1, filter="code:t1,t2")
    d = demand(participants=["g1", "g2", "g3", "g4"], limit=2, pooled=(rooms, teachers))
    edit = Event(code="d1-K-01", kind="K", duration=1, start_pattern="all", demand="d1")
    ds = make_dataset(
        days=2,
        periods=4,
        resources=[
            *groups(4),
            res("r1", "R", capacity=20),
            res("r2", "R", capacity=20),
            res("t1", "T"),
            res("t2", "T"),
        ],
        events=[edit],
        fixed=[("d1-K-01", g) for g in edit_groups],
        pins=[edit_pin] if edit_pin else [],
        demands=[d],
        validate=False,
    )
    result = Result(
        assignments=(
            at("d1-K-01", "d1", "p1", pick(0, "r1"), pick(1, "t1")),
            at("d1-K-02", "d1", "p2", pick(0, "r1"), pick(1, "t2")),
        ),
        created=(
            CreatedEvent(code="d1-K-01", demand="d1", participants=("g1", "g2")),
            CreatedEvent(code="d1-K-02", demand="d1", participants=("g3", "g4")),
        ),
    )
    return ds, result


def placed(result: Result, code: str):  # type: ignore[no-untyped-def]
    return next(a for a in result.assignments if a.event == code)


def test_a_result_with_no_edits_is_unchanged() -> None:
    ds, result = scene()
    plain = ds.model_copy(update={"events": (), "fixed": (), "pins": ()})
    assert with_edits(plain, result) == result


def test_an_edited_session_is_no_longer_a_created_event() -> None:
    ds, result = scene()
    drafted = with_edits(ds, result)
    assert [c.code for c in drafted.created] == ["d1-K-02"]


def test_an_edited_day_and_start_replace_the_runs() -> None:
    ds, result = scene(Pin(event="d1-K-01", day="d2", start_period="p3"))
    moved = placed(with_edits(ds, result), "d1-K-01")
    assert (moved.day, moved.start_period) == ("d2", "p3")


def test_an_edit_that_sets_only_the_day_keeps_the_start() -> None:
    ds, result = scene(Pin(event="d1-K-01", day="d2"))
    moved = placed(with_edits(ds, result), "d1-K-01")
    assert (moved.day, moved.start_period) == ("d2", "p1")


def test_an_edited_room_and_teacher_go_to_the_requirement_of_their_type() -> None:
    ds, result = scene(Pin(event="d1-K-01", resources=("r2", "t2")))
    choices = {c.ordinal: c.resources for c in placed(with_edits(ds, result), "d1-K-01").chosen}
    assert choices == {0: ("r2",), 1: ("t2",)}


def test_an_edit_of_the_room_alone_keeps_the_runs_teacher() -> None:
    ds, result = scene(Pin(event="d1-K-01", resources=("r2",)))
    choices = {c.ordinal: c.resources for c in placed(with_edits(ds, result), "d1-K-01").chosen}
    assert choices == {0: ("r2",), 1: ("t1",)}


def test_the_sessions_that_were_not_edited_keep_their_place() -> None:
    ds, result = scene(Pin(event="d1-K-01", day="d2", start_period="p3"))
    assert placed(with_edits(ds, result), "d1-K-02") == placed(result, "d1-K-02")


def test_the_edited_timetable_is_verified_like_any_other() -> None:
    ds, result = scene(Pin(event="d1-K-01", day="d2", start_period="p3"))
    drafted = with_edits(ds, result)
    assert hard_violations(verify(ds, drafted)) == []


def test_moving_an_edit_onto_another_session_shows_the_clash_at_once() -> None:
    """d1-K-01 moved to d1 p2 with room r1 double-books the room of d1-K-02."""
    ds, result = scene(Pin(event="d1-K-01", day="d1", start_period="p2"))
    found = hard_violations(verify(ds, with_edits(ds, result)))
    assert any(v.code == "no_overlap" and "r1" in v.message for v in found)


def test_moving_a_group_into_another_block_shows_the_problem_at_once() -> None:
    """An edit that keeps g1, g2 and g3 together leaves g4 alone and the blocks uneven."""
    ds, result = scene(edit_groups=("g1", "g2", "g3"))
    found = hard_violations(verify(ds, with_edits(ds, result)))
    assert any(v.code == "demand_cover" for v in found)
