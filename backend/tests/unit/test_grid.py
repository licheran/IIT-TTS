"""The weekly grid of one resource and the diff of two results (`core/grid.py`)."""

from typing import Any

from tts.core.grid import build_grid, diff_results, involved
from tts.core.model import Assignment, PooledChoice, Result


def place(event: str, day: str, start: str, *resources: str) -> Assignment:
    chosen = (PooledChoice(ordinal=0, resources=resources),) if resources else ()
    return Assignment(event=event, day=day, start_period=start, chosen=chosen)


def test_l6_grid_of_a_group_holds_its_events_as_single_cells(
    l6_dataset, l6_locked_result, l6_expected: dict[str, Any]
) -> None:
    group = "L6 SE / G1"
    grid = build_grid(l6_dataset, l6_locked_result, group)
    assert sum(c.span for c in grid.cells) == l6_expected["group_periods_per_week"][group]
    assert all(c.span == c.duration == 2 for c in grid.cells)
    assert all(c.lanes == 1 and c.lane == 0 for c in grid.cells)  # a group is never double-booked
    assert len(grid.periods) == 14 and len(grid.days) == 6


def test_a_joint_event_lists_every_fixed_resource_it_serves(l6_dataset, l6_locked_result) -> None:
    joint = max(
        (e for e in l6_dataset.events if sum(1 for f in l6_dataset.fixed if f.event == e.code) > 5),
        key=lambda e: e.code,
    )
    fixed = [f.resource for f in l6_dataset.fixed if f.event == joint.code]
    resource = next(r for r in fixed if r.startswith("L6"))
    cell = next(
        c for c in build_grid(l6_dataset, l6_locked_result, resource).cells if c.event == joint.code
    )
    assert set(cell.fixed) == set(fixed)
    assert cell.chosen  # and the pooled resource picked for it


def test_a_parent_shows_the_events_of_everything_below_it(l6_dataset, l6_locked_result) -> None:
    programme = "L6 SE"
    parent_cells = build_grid(l6_dataset, l6_locked_result, programme).cells
    child_events = {
        c.event
        for r in l6_dataset.resources
        if r.parent == programme
        for c in build_grid(l6_dataset, l6_locked_result, r.code).cells
    }
    assert {c.event for c in parent_cells} == child_events
    assert any(c.lanes > 1 for c in parent_cells)  # parallel tutorials sit side by side


def test_a_room_grid_lists_only_events_placed_in_it(l6_dataset, l6_locked_result) -> None:
    seen = involved(l6_dataset, l6_locked_result)
    room = next(r.code for r in l6_dataset.resources if r.type == "Room")
    grid = build_grid(l6_dataset, l6_locked_result, room)
    assert {c.event for c in grid.cells} == set(seen[room])
    assert all(room in c.chosen for c in grid.cells)


def test_an_unplaced_event_has_no_cell(l6_dataset, l6_locked_result) -> None:
    partial = Result(assignments=l6_locked_result.assignments[1:])
    missing = l6_locked_result.assignments[0].event
    group = next(f.resource for f in l6_dataset.fixed if f.event == missing)
    assert missing not in {c.event for c in build_grid(l6_dataset, partial, group).cells}


def test_diff_reports_moved_added_removed_and_room_changes(l6_locked_result) -> None:
    a = l6_locked_result.assignments
    moved, swapped, removed = a[0], a[1], a[2]
    other_day = "Sat" if moved.day != "Sat" else "Mon"
    changed = [
        place(moved.event, other_day, moved.start_period),
        place(swapped.event, swapped.day, swapped.start_period, "OTHER-ROOM"),
        *a[3:],
    ]
    new = place("NEW-EVENT", "Mon", "P01")
    changes = {
        c.event: c for c in diff_results(Result(assignments=a), Result(assignments=(*changed, new)))
    }
    assert changes[moved.event].kind == "moved"
    assert changes[moved.event].after.day == other_day  # type: ignore[union-attr]
    assert changes[swapped.event].kind == "resources"
    assert changes[removed.event].kind == "removed"
    assert changes["NEW-EVENT"].kind == "added"
    assert len(changes) == 4


def test_diff_of_a_result_with_itself_is_empty(l6_locked_result) -> None:
    assert diff_results(l6_locked_result, l6_locked_result) == ()
