"""H6 `demand_cover`, and H0-H5 on events the solver created (ADR-0007, spec 04 section 1)."""

from fixtures import at, demand, ev, make_dataset, pick, res
from tts.core.constraints import demand_cover
from tts.core.constraints.registry import implicit_types
from tts.core.model import CreatedEvent, Dataset, Event, Result, Violation
from tts.core.verifier import verify

GROUPS = tuple(res(f"g{i}", "G", capacity=10) for i in (1, 2, 3, 4))
ROOM = res("r1", "R", capacity=40)


def configured(*demands, events=(), fixed=(), groups=GROUPS, room=ROOM) -> Dataset:  # type: ignore[no-untyped-def]
    return make_dataset(
        resources=(*groups, room),
        events=events,
        fixed=fixed,
        demands=demands or (demand(participants=("g1", "g2", "g3", "g4")),),
    )


def made(code: str, *participants: str, of: str = "d1") -> CreatedEvent:
    return CreatedEvent(code=code, demand=of, participants=participants)


def cover(dataset: Dataset, *created: CreatedEvent, assignments=()) -> list[Violation]:  # type: ignore[no-untyped-def]
    found = verify(dataset, Result(assignments=assignments, created=created))
    return [v for v in found if v.code == demand_cover.TYPE]


def messages(found: list[Violation]) -> list[str]:
    return [v.message for v in found]


def edit(code: str, demand_code: str = "d1", duration: int = 1) -> Event:
    return ev(code, duration=duration).model_copy(update={"demand": demand_code})


def test_h6_is_an_implicit_rule_registered_after_the_pin_rule() -> None:
    assert demand_cover.CODE == "H6"
    assert implicit_types()[-1] is demand_cover


def test_a_correct_split_has_no_violation() -> None:
    assert cover(configured(), made("e1", "g1", "g2"), made("e2", "g3", "g4")) == []


def test_a_group_left_out_is_reported() -> None:
    found = cover(configured(), made("e1", "g1", "g2"), made("e2", "g3"))
    assert messages(found) == ['demand "d1": "g4" attends no session']
    assert [(r.kind, r.code) for r in found[0].refs] == [("demand", "d1"), ("resource", "g4")]


def test_a_group_in_two_blocks_is_reported() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2)
    found = cover(configured(d), made("e1", "g1", "g2"), made("e2", "g2", "g3"))
    assert messages(found) == ['demand "d1": "g2" is in 2 blocks']


def test_a_block_with_too_many_groups_is_reported() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2)
    found = cover(configured(d), made("e1", "g1", "g2", "g3"))
    assert 'demand "d1": block g1, g2, g3 has 3 participants, more than the limit of 2' in messages(
        found
    )
    assert 'demand "d1": 1 block(s), expected 2' in messages(found)


def test_uneven_blocks_are_reported() -> None:
    groups = tuple(res(f"g{i:02d}", "G", capacity=10) for i in range(1, 11))
    d = demand(participants=tuple(g.code for g in groups), limit=3)
    blocks = [("g01", "g02", "g03"), ("g04", "g05", "g06"), ("g07", "g08", "g09"), ("g10",)]
    found = cover(
        configured(d, groups=groups), *(made(f"e{i}", *b) for i, b in enumerate(blocks, 1))
    )
    assert messages(found) == [
        'demand "d1": block sizes 3, 3, 3, 1 are uneven (they may differ by 1)'
    ]


def test_three_three_two_two_is_accepted() -> None:
    groups = tuple(res(f"g{i:02d}", "G", capacity=10) for i in range(1, 11))
    d = demand(participants=tuple(g.code for g in groups), limit=3)
    blocks = [
        ("g01", "g02", "g03"),
        ("g04", "g05", "g06"),
        ("g07", "g08"),
        ("g09", "g10"),
    ]
    made_all = [made(f"e{i}", *b) for i, b in enumerate(blocks, 1)]
    assert cover(configured(d, groups=groups), *made_all) == []


def test_a_block_with_a_session_missing_is_reported() -> None:
    d = demand(participants=("g1", "g2"), limit=2, repeat=2)
    found = cover(configured(d), made("e1", "g1", "g2"))
    assert messages(found) == ['demand "d1": block g1, g2 has 1 session(s), expected 2']


def test_two_sessions_with_the_same_groups_complete_a_block() -> None:
    d = demand(participants=("g1", "g2"), limit=2, repeat=2)
    assert cover(configured(d), made("e1", "g1", "g2"), made("e2", "g1", "g2")) == []


def test_a_repetition_with_other_companions_is_reported() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2, repeat=2)
    found = cover(configured(d), made("e1", "g1", "g2"), made("e2", "g1", "g3"))
    assert 'demand "d1": "g1" is in 2 blocks' in messages(found)
    assert any("has 1 session(s), expected 2" in m for m in messages(found))


def test_an_edit_and_a_created_session_complete_a_block() -> None:
    d = demand(participants=("g1", "g2"), limit=2, repeat=2)
    ds = configured(d, events=(edit("edited"),), fixed=(("edited", "g1"), ("edited", "g2")))
    assert cover(ds, made("e1", "g1", "g2")) == []


def test_an_edit_with_no_participants_is_reported() -> None:
    found = cover(configured(events=(edit("edited"),)), made("e1", "g1", "g2"))
    assert 'event "edited": belongs to demand "d1" but has no participants' in messages(found)


def test_an_event_that_differs_from_its_demand_is_reported() -> None:
    d = demand(participants=("g1", "g2"), limit=2, duration=1)
    ds = configured(
        d, events=(edit("edited", duration=2),), fixed=(("edited", "g1"), ("edited", "g2"))
    )
    found = cover(ds)
    assert 'event "edited": duration 2, the demand says 1' in messages(found)


def test_a_created_event_of_an_unknown_demand_is_reported() -> None:
    found = cover(configured(), made("e1", "g1", of="nope"))
    assert 'created event "e1": unknown demand "nope"' in messages(found)


def test_a_created_event_that_reuses_a_declared_code_is_reported() -> None:
    ds = configured(events=(edit("e1"),), fixed=(("e1", "g1"), ("e1", "g2")))
    found = cover(ds, made("e1", "g3", "g4"))
    assert 'created event "e1": code "e1" is already an event' in messages(found)


def test_a_dataset_without_demands_has_nothing_to_check() -> None:
    ds = make_dataset(resources=GROUPS, events=(ev("e1"),))
    assert [v for v in verify(ds, Result()) if v.code == demand_cover.TYPE] == []


def test_a_demand_with_no_participants_has_no_blocks() -> None:
    assert cover(configured(demand(participants=()))) == []


# --- H0 to H5 hold for created events --------------------------------------------------------


def verified(dataset: Dataset, result: Result) -> list[tuple[str, str]]:
    return sorted((v.code, v.message) for v in verify(dataset, result) if v.severity == "hard")


def test_a_created_event_left_unplaced_is_reported_by_the_placement_rule() -> None:
    found = verified(configured(), Result(created=(made("e1", "g1", "g2"), made("e2", "g3", "g4"))))
    assert ("placement", 'event "e1" has no assignment') in found
    assert ("placement", 'event "e2" has no assignment') in found


def test_a_room_too_small_for_a_created_events_groups_is_reported() -> None:
    small = res("r1", "R", capacity=15)
    ds = configured(room=small)
    result = Result(
        created=(made("e1", "g1", "g2"), made("e2", "g3", "g4")),
        assignments=(
            at("e1", "d1", "p1", pick(0, "r1")),
            at("e2", "d1", "p2", pick(0, "r1")),
        ),
    )
    codes = [c for c, _ in verified(ds, result)]
    assert codes.count("capacity") == 2  # 20 students in a room for 15, twice


def test_two_created_events_with_a_shared_group_at_one_time_clash() -> None:
    d = demand(participants=("g1", "g2", "g3"), limit=2)
    ds = configured(d)
    result = Result(
        created=(made("e1", "g1", "g2"), made("e2", "g2", "g3")),
        assignments=(
            at("e1", "d1", "p1", pick(0, "r1")),
            at("e2", "d1", "p1", pick(0, "r1")),
        ),
    )
    codes = {c for c, _ in verified(ds, result)}
    assert {"no_overlap", "demand_cover"} <= codes


def test_a_correct_timetable_of_created_events_has_no_hard_violation() -> None:
    result = Result(
        created=(made("e1", "g1", "g2"), made("e2", "g3", "g4")),
        assignments=(
            at("e1", "d1", "p1", pick(0, "r1")),
            at("e2", "d1", "p2", pick(0, "r1")),
        ),
    )
    assert verified(configured(), result) == []
