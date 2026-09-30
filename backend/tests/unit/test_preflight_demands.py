"""Pre-flight checks for demands (spec 05 section 3, ADR-0007)."""

from constraint_helpers import rule

from fixtures import demand, ev, make_dataset, res
from tts.core.model import Dataset, Event, PooledSpec
from tts.preflight.checks import Issue, run_preflight

GROUPS = tuple(res(f"g{i}", "G", capacity=10) for i in (1, 2, 3))


def configured(*demands, resources=(), events=(), fixed=(), room=40, **more) -> Dataset:  # type: ignore[no-untyped-def]
    return make_dataset(
        days=2,
        periods=4,
        resources=(*GROUPS, res("r1", "R", capacity=room), *resources),
        events=events,
        fixed=fixed,
        demands=demands or (demand(),),
        validate=False,
        **more,
    )


def check(dataset: Dataset) -> list[Issue]:
    """Pre-flight without the unused-resource warnings, which these small datasets trigger."""
    return [i for i in run_preflight(dataset) if i.kind != "unused_resource"]


def kinds(issues: list[Issue]) -> list[str]:
    return sorted(i.kind for i in issues)


def of_kind(issues: list[Issue], kind: str) -> list[Issue]:
    return [i for i in issues if i.kind == kind]


def test_a_sound_configured_dataset_has_no_issue() -> None:
    assert check(configured()) == []


# --- pooled candidates ---------------------------------------------------------------------


def test_a_room_smaller_than_the_biggest_block_that_cannot_be_avoided_is_an_error() -> None:
    # three participants of 10 in two blocks: one block holds at least 15
    found = check(configured(room=12))
    assert [(i.severity, i.kind) for i in found] == [("error", "no_candidate")]
    assert found[0].message == 'd1: no R matching "all" with capacity ≥ 15'


def test_a_room_that_seats_the_unavoidable_block_is_enough() -> None:
    assert check(configured(room=15)) == []


def test_the_biggest_participant_alone_must_fit_a_room() -> None:
    big = (res("g1", "G", capacity=50), res("g2", "G", capacity=10), res("g3", "G", capacity=10))
    ds = make_dataset(
        days=2,
        periods=4,
        resources=(*big, res("r1", "R", capacity=40)),
        demands=(demand(limit=1),),
        validate=False,
    )
    assert [i.message for i in check(ds)] == ['d1: no R matching "all" with capacity ≥ 50']


def test_a_pool_smaller_than_the_count_asked_is_an_error() -> None:
    spec = PooledSpec(resource_type="T", count=2, filter="code:t1")
    ds = configured(demand(pooled=(spec,)), resources=(res("t1", "T"), res("t2", "T")))
    found = check(ds)
    assert [i.message for i in found] == ['d1: needs 2 T but only 1 match "code:t1"']
    assert found[0].kind == "no_candidate"


def test_a_bad_filter_is_an_error() -> None:
    spec = PooledSpec(resource_type="T", filter="nonsense:x")
    found = check(configured(demand(pooled=(spec,)), resources=(res("t1", "T"),)))
    assert [i.kind for i in found] == ["invalid_selector"]


# --- over-demand and pressure --------------------------------------------------------------


def test_a_participant_that_needs_more_periods_than_it_has_is_an_error() -> None:
    # 5 sessions a week of 2 periods = 10 periods, but 2 days of 4 periods = 8
    found = of_kind(check(configured(demand(repeat=5, duration=2, pattern="all"))), "over_demand")
    assert sorted(i.message for i in found) == [
        "G g1: needs 10 periods, 8 available",
        "G g2: needs 10 periods, 8 available",
        "G g3: needs 10 periods, 8 available",
    ]


def test_a_full_week_is_not_over_demand() -> None:
    found = check(configured(demand(repeat=4, duration=2, limit=3)))
    assert of_kind(found, "over_demand") == []


def test_an_edit_is_not_counted_twice() -> None:
    edit = Event(code="edit", kind="K", duration=2, start_pattern="all", demand="d1")
    ds = configured(
        demand(repeat=4, duration=2, limit=3),
        events=(edit,),
        fixed=(("edit", "g1"), ("edit", "g2"), ("edit", "g3")),
    )
    assert of_kind(check(ds), "over_demand") == []


def test_rooms_that_cannot_hold_all_the_sessions_give_a_warning() -> None:
    # 2 blocks x 3 sessions x 2 periods = 12 room periods, one room has 8
    found = check(configured(demand(repeat=3, duration=2)))
    assert [(i.severity, i.kind) for i in found] == [("warning", "pooled_pressure")]
    assert found[0].message == "R all: 12 periods needed, 8 available"


# --- nothing to schedule -------------------------------------------------------------------


def test_a_demand_with_no_participants_gives_a_warning() -> None:
    found = check(configured(demand(participants=())))
    assert [(i.severity, i.kind, i.message) for i in found] == [
        ("warning", "empty_demand", "d1: no participants, nothing to schedule")
    ]


def test_a_dataset_with_nothing_to_schedule_gives_a_warning() -> None:
    found = check(make_dataset(resources=GROUPS))
    assert [(i.severity, i.kind) for i in found] == [("warning", "nothing_to_schedule")]


def test_a_dataset_with_events_has_something_to_schedule() -> None:
    ds = make_dataset(resources=GROUPS, events=(ev("e1"),), fixed=(("e1", "g1"),))
    assert of_kind(check(ds), "nothing_to_schedule") == []


# --- scopes that depend on the solver's grouping -------------------------------------------


def test_a_code_scope_that_names_no_declared_event_gives_a_warning() -> None:
    ds = configured(constraints=[rule("same_day", "code:e1,e2", hard=False)])
    assert len(of_kind(check(ds), "code_scope_with_demands")) == 1


def test_a_code_scope_that_names_a_declared_edit_is_fine() -> None:
    edit = Event(code="edit", kind="K", duration=1, start_pattern="all", demand="d1")
    ds = configured(
        events=(edit,),
        fixed=(("edit", "g1"),),
        constraints=[rule("same_day", "code:edit", hard=False)],
    )
    assert of_kind(check(ds), "code_scope_with_demands") == []


def test_a_hard_uses_scope_is_an_error_when_there_are_demands() -> None:
    ds = configured(constraints=[rule("same_day", "uses:(code:g1)", hard=True)])
    found = of_kind(check(ds), "uses_scope_unsupported")
    assert [i.severity for i in found] == ["error"]
    assert found[0].refs[0].code == "C"


def test_a_soft_uses_scope_is_a_warning_when_there_are_demands() -> None:
    ds = configured(constraints=[rule("same_day", "uses:(code:g1)", hard=False)])
    found = of_kind(check(ds), "uses_scope_declared_only")
    assert [i.severity for i in found] == ["warning"]


def test_uses_scopes_are_fine_without_demands() -> None:
    ds = make_dataset(
        resources=GROUPS,
        events=(ev("e1"),),
        fixed=(("e1", "g1"),),
        constraints=[rule("same_day", "uses:(code:g1)", hard=True)],
    )
    found = check(ds)
    assert of_kind(found, "uses_scope_unsupported") == []
    assert of_kind(found, "uses_scope_declared_only") == []


def test_an_edit_outside_its_demand_is_reported_as_an_invariant() -> None:
    edit = Event(code="edit", kind="K", duration=1, start_pattern="all", demand="d1")
    ds = configured(
        demand(participants=("g1", "g2")),
        events=(edit,),
        fixed=(("edit", "g3"),),
    )
    found = check(ds)
    assert kinds(found) == ["edit_outside_demand"]
    assert found[0].refs[0].code == "edit"
