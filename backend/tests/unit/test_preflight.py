"""Pre-flight checks (spec 05 section 3): one hand-made dataset per row of the table."""

from fixtures import ev, make_dataset, pool, res, unavailable
from tts.core.model import Constraint, Pin, Ref
from tts.preflight.checks import Issue, has_errors, run_preflight


def kinds(issues: list[Issue]) -> list[str]:
    return [i.kind for i in issues]


def only(issues: list[Issue], kind: str) -> Issue:
    found = [i for i in issues if i.kind == kind]
    assert len(found) == 1, issues
    return found[0]


def event_ref(code: str) -> Ref:
    return Ref(kind="event", code=code)


def resource_ref(code: str) -> Ref:
    return Ref(kind="resource", code=code)


def small_dataset(**changes):  # type: ignore[no-untyped-def]
    """Two groups, a teacher, two rooms and two events: nothing wrong with it."""
    options = {
        "resources": [
            res("g1", capacity=20),
            res("g2", capacity=25),
            res("t1", "T"),
            res("r1", "R", capacity=30),
            res("r2", "R", capacity=50),
        ],
        "events": [ev("e1"), ev("e2")],
        "fixed": [("e1", "g1"), ("e1", "t1"), ("e2", "g2")],
        "pooled": [pool("e1"), pool("e2")],
    }
    options.update(changes)
    return make_dataset(**options)


# --- A clean dataset --------------------------------------------------------------------------


def test_a_sound_dataset_has_no_issues() -> None:
    assert run_preflight(small_dataset()) == []


def test_has_errors_ignores_warnings() -> None:
    warning = Issue(severity="warning", kind="unused_resource", message="x")
    error = Issue(severity="error", kind="over_demand", message="y")
    assert not has_errors([warning])
    assert has_errors([warning, error])


def test_the_issues_are_the_same_on_every_run_and_errors_come_first() -> None:
    ds = small_dataset(
        events=[ev("e1", duration=3), ev("e2")],
        pooled=[pool("e1", rule="sum_of_fixed:G"), pool("e2")],
        resources=[
            res("g1", capacity=20),
            res("g2", capacity=25),
            res("t1", "T"),
            res("r1", "R", capacity=10),
        ],
        breaks=[2],
    )
    first, again = run_preflight(ds), run_preflight(ds)
    assert first == again
    severities = [i.severity for i in first]
    assert severities == sorted(severities, key=lambda s: s != "error")
    assert has_errors(first)


# --- Unresolved references and cycles -------------------------------------------------------


def test_an_unknown_reference_is_an_error_and_stops_the_other_checks() -> None:
    ds = small_dataset(
        fixed=[("e1", "g1"), ("e1", "ghost")],
        events=[ev("e1", duration=9), ev("e2")],  # would also be an empty start domain
        validate=False,
    )
    issues = run_preflight(ds)
    assert kinds(issues) == ["unknown_reference"]
    issue = issues[0]
    assert issue.severity == "error"
    assert issue.message == 'fixed "e1/ghost": unknown resource "ghost"'
    assert issue.refs == (event_ref("e1"), resource_ref("ghost"))


def test_an_unknown_reference_in_a_pin_points_at_the_event() -> None:
    ds = small_dataset(pins=[Pin(event="e1", day="nowhere")], validate=False)
    issue = only(run_preflight(ds), "unknown_reference")
    assert issue.refs == (event_ref("e1"),)


def test_a_hierarchy_cycle_is_an_error() -> None:
    ds = make_dataset(
        resources=[res("a", "N", parent="b"), res("b", "N", parent="a")], validate=False
    )
    issue = only(run_preflight(ds), "hierarchy_cycle")
    assert issue.severity == "error"
    assert issue.message == 'resource "a": parent cycle: a → b → a'
    assert issue.refs == (resource_ref("a"),)


# --- Empty start domain -------------------------------------------------------------------


def test_an_event_with_no_allowed_start_is_an_error() -> None:
    ds = small_dataset(events=[ev("e1", duration=3), ev("e2")], breaks=[2], periods=4)
    issue = only(run_preflight(ds), "empty_start_domain")
    assert issue.severity == "error"
    assert issue.message == "e1: no allowed start fits duration 3"
    assert issue.refs == (event_ref("e1"),)


def test_an_event_that_fits_somewhere_is_fine() -> None:
    ds = small_dataset(events=[ev("e1", duration=2), ev("e2")], breaks=[3], periods=4)
    assert "empty_start_domain" not in kinds(run_preflight(ds))


# --- Pooled candidates ------------------------------------------------------------------------


def test_a_requirement_no_resource_can_serve_is_an_error() -> None:
    ds = small_dataset(
        resources=[res("g1", capacity=20), res("g2", capacity=25), res("r1", "R", capacity=10)],
        fixed=[("e1", "g1"), ("e2", "g2")],
        pooled=[pool("e1", rule="sum_of_fixed:G"), pool("e2")],
    )
    issue = only(run_preflight(ds), "no_candidate")
    assert issue.severity == "error"
    assert issue.message == 'e1: no R matching "all" with capacity ≥ 20'
    assert issue.refs == (event_ref("e1"),)


def test_the_filter_appears_in_the_message() -> None:
    ds = small_dataset(pooled=[pool("e1", filter="tag:kind=z"), pool("e2")])
    issue = only(run_preflight(ds), "no_candidate")
    assert issue.message == 'e1: no R matching "tag:kind=z"'


def test_too_few_candidates_for_the_count_is_an_error() -> None:
    ds = small_dataset(pooled=[pool("e1", count=3), pool("e2")])
    issue = only(run_preflight(ds), "no_candidate")
    assert issue.message == 'e1: needs 3 R but only 2 match "all"'


def test_a_bad_filter_is_reported_instead_of_crashing() -> None:
    ds = small_dataset(pooled=[pool("e1", filter="nonsense:x"), pool("e2")])
    issue = only(run_preflight(ds), "invalid_selector")
    assert issue.severity == "error"
    assert issue.message.startswith('e1#0: filter "nonsense:x"')
    assert issue.refs == (event_ref("e1"),)


# --- Over-demand ----------------------------------------------------------------------------


def test_a_resource_needing_more_periods_than_it_has_is_an_error() -> None:
    ds = make_dataset(
        days=1,
        periods=4,
        resources=[res("t1", "T")],
        events=[ev("e1", duration=2), ev("e2", duration=2)],
        fixed=[("e1", "t1"), ("e2", "t1")],
        availability=[unavailable("t1", "d1", "p1"), unavailable("t1", "d1", "p2")],
    )
    issue = only(run_preflight(ds), "over_demand")
    assert issue.severity == "error"
    assert issue.message == "T t1: needs 4 periods, 2 available"
    assert issue.refs == (resource_ref("t1"),)


def test_breaks_are_not_available_and_are_not_counted_twice() -> None:
    ds = make_dataset(
        days=1,
        periods=4,
        breaks=[2],
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2"), ev("e3"), ev("e4")],
        fixed=[("e1", "t1"), ("e2", "t1"), ("e3", "t1"), ("e4", "t1")],
        availability=[unavailable("t1", "d1", "p2")],  # already a break: costs nothing more
    )
    issue = only(run_preflight(ds), "over_demand")
    assert issue.message == "T t1: needs 4 periods, 3 available"


def test_a_preference_to_avoid_does_not_reduce_availability() -> None:
    ds = make_dataset(
        days=1,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
        availability=[unavailable("t1", "d1", "p1", status="avoid")],
    )
    assert "over_demand" not in kinds(run_preflight(ds))


def test_demand_equal_to_availability_is_allowed() -> None:
    ds = make_dataset(
        days=1,
        periods=2,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
    )
    assert "over_demand" not in kinds(run_preflight(ds))


def test_an_event_on_a_grouping_node_loads_its_exclusive_children() -> None:
    ds = make_dataset(
        days=1,
        periods=4,
        resources=[res("top", "N"), res("g1", parent="top", capacity=5)],
        events=[ev("e1", duration=2), ev("e2", duration=2), ev("e3", duration=2)],
        fixed=[("e1", "top"), ("e2", "top"), ("e3", "top")],
    )
    issue = only(run_preflight(ds), "over_demand")
    assert issue.message == "G g1: needs 6 periods, 4 available"  # "top" is not exclusive


def test_the_type_word_comes_from_the_label_function() -> None:
    ds = make_dataset(
        days=1,
        periods=1,
        resources=[res("t1", "T")],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "t1"), ("e2", "t1")],
    )
    issue = only(
        run_preflight(ds, label=lambda code: {"T": "Teacher"}.get(code, code)), "over_demand"
    )
    assert issue.message == "Teacher t1: needs 2 periods, 1 available"


# --- Pooled pressure --------------------------------------------------------------------------


def test_pooled_demand_above_supply_is_a_warning() -> None:
    ds = make_dataset(
        days=1,
        periods=2,
        resources=[res("r1", "R", capacity=10)],
        events=[ev("e1"), ev("e2"), ev("e3")],
        pooled=[pool("e1"), pool("e2"), pool("e3")],
    )
    issue = only(run_preflight(ds), "pooled_pressure")
    assert issue.severity == "warning"
    assert issue.message == "R all: 3 periods needed, 2 available"
    assert not has_errors(run_preflight(ds))


def test_supply_counts_only_the_candidates_of_that_filter() -> None:
    ds = make_dataset(
        days=1,
        periods=2,
        resources=[res("r1", "R", kind="a"), res("r2", "R", kind="b"), res("r3", "R", kind="b")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        pooled=[pool(c, filter="tag:kind=a") for c in ("e1", "e2", "e3")],
    )
    issue = only(run_preflight(ds), "pooled_pressure")
    assert issue.message == "R tag:kind=a: 3 periods needed, 2 available"


def test_a_resource_unavailable_reduces_pooled_supply() -> None:
    ds = make_dataset(
        days=1,
        periods=2,
        resources=[res("r1", "R", capacity=10), res("r2", "R", capacity=10)],
        events=[ev("e1"), ev("e2"), ev("e3")],
        pooled=[pool("e1"), pool("e2"), pool("e3")],
        availability=[unavailable("r1", "d1", "p1"), unavailable("r1", "d1", "p2")],
    )
    issue = only(run_preflight(ds), "pooled_pressure")
    assert issue.message == "R all: 3 periods needed, 2 available"


# --- Conflicting pins ------------------------------------------------------------------------


def pinned(event: str, day: str, period: str, *resources: str) -> Pin:
    return Pin(event=event, day=day, start_period=period, resources=resources)


def test_two_events_pinned_to_one_resource_and_slot_are_an_error() -> None:
    ds = small_dataset(pins=[pinned("e1", "d1", "p1", "r1"), pinned("e2", "d1", "p1", "r1")])
    issue = only(run_preflight(ds), "conflicting_pins")
    assert issue.severity == "error"
    assert issue.message == "Pins: 2 activities pinned to r1 on d1 p1"
    assert issue.refs == (
        resource_ref("r1"),
        event_ref("e1"),
        event_ref("e2"),
        Ref(kind="slot", code="d1/p1"),
    )


def test_pins_that_only_overlap_in_time_are_an_error() -> None:
    ds = small_dataset(
        events=[ev("e1", duration=2), ev("e2")],
        pins=[pinned("e1", "d1", "p1", "r1"), pinned("e2", "d1", "p2", "r1")],
    )
    issue = only(run_preflight(ds), "conflicting_pins")
    assert issue.message == "Pins: 2 activities pinned to r1 with overlapping times from d1 p1"


def test_pins_that_share_a_fixed_resource_are_an_error() -> None:
    ds = small_dataset(
        fixed=[("e1", "t1"), ("e2", "t1")],
        pins=[pinned("e1", "d1", "p2"), pinned("e2", "d1", "p2")],
    )
    issue = only(run_preflight(ds), "conflicting_pins")
    assert issue.message == "Pins: 2 activities pinned to t1 on d1 p2"


def test_pins_that_do_not_collide_are_fine() -> None:
    ds = small_dataset(
        pins=[
            pinned("e1", "d1", "p1", "r1"),
            pinned("e2", "d1", "p1", "r2"),  # another room
        ]
    )
    assert "conflicting_pins" not in kinds(run_preflight(ds))
    ds = small_dataset(pins=[pinned("e1", "d1", "p1", "r1"), pinned("e2", "d2", "p1", "r1")])
    assert "conflicting_pins" not in kinds(run_preflight(ds))
    ds = small_dataset(
        pins=[Pin(event="e1", day="d1", resources=("r1",)), Pin(event="e2", resources=("r1",))]
    )  # no exact time: nothing to compare yet
    assert "conflicting_pins" not in kinds(run_preflight(ds))


def test_three_pins_on_one_slot_are_reported_once() -> None:
    ds = make_dataset(
        resources=[res("r1", "R")],
        events=[ev("e1"), ev("e2"), ev("e3")],
        pooled=[pool("e1"), pool("e2"), pool("e3")],
        pins=[pinned(e, "d1", "p1", "r1") for e in ("e1", "e2", "e3")],
    )
    issue = only(run_preflight(ds), "conflicting_pins")
    assert issue.message == "Pins: 3 activities pinned to r1 on d1 p1"


# --- Unused resources -----------------------------------------------------------------------


def test_a_resource_of_a_pooled_type_that_no_requirement_can_use_is_a_warning() -> None:
    ds = small_dataset(
        resources=[
            res("g1", capacity=20),
            res("g2", capacity=25),
            res("t1", "T"),
            res("r1", "R", capacity=30),
            res("r2", "R", capacity=5),
        ],
        pooled=[pool("e1", rule="sum_of_fixed:G"), pool("e2", rule="sum_of_fixed:G")],
    )
    issue = only(run_preflight(ds), "unused_resource")
    assert issue.severity == "warning"
    assert issue.message == "R r2 is never a candidate"
    assert issue.refs == (resource_ref("r2"),)


def test_a_type_nobody_requests_is_not_reported_as_unused() -> None:
    ds = small_dataset(pooled=[])
    assert "unused_resource" not in kinds(run_preflight(ds))


# --- Constraint scopes ------------------------------------------------------------------------


def soft(code: str, scope: str, type_: str = "max_gaps", **changes: object) -> Constraint:
    return Constraint(code=code, type=type_, scope=scope, hard=False, **changes)  # type: ignore[arg-type]


def test_a_soft_constraint_on_an_empty_scope_is_a_warning() -> None:
    ds = small_dataset(constraints=[soft("C1", "type:nothing")])
    issue = only(run_preflight(ds), "empty_scope")
    assert issue.severity == "warning"
    assert issue.message == "C1: scope matches nothing"
    assert issue.refs == (Ref(kind="constraint", code="C1"),)


def test_a_scope_that_matches_something_is_fine() -> None:
    ds = small_dataset(constraints=[soft("C1", "type:T")])
    assert run_preflight(ds) == []


def test_event_scopes_are_checked_against_events() -> None:
    ds = small_dataset(constraints=[soft("C2", "kind:none", "same_day")])
    assert kinds(run_preflight(ds)) == ["empty_scope"]
    ds = small_dataset(constraints=[soft("C2", "all", "same_day")])
    assert run_preflight(ds) == []


def test_hard_inactive_and_unknown_constraints_are_not_checked_for_scope() -> None:
    ds = small_dataset(
        constraints=[
            Constraint(code="C1", type="max_gaps", scope="type:nothing", hard=True),
            soft("C2", "type:nothing", active=False),
            soft("C3", "type:nothing", type_="not_a_type"),
        ]
    )
    assert "empty_scope" not in kinds(run_preflight(ds))


def test_a_scope_that_is_not_a_valid_selector_is_an_error() -> None:
    ds = small_dataset(constraints=[soft("C1", "nonsense:x")])
    issue = only(run_preflight(ds), "invalid_selector")
    assert issue.severity == "error"
    assert issue.message.startswith('C1: scope "nonsense:x"')
    assert issue.refs == (Ref(kind="constraint", code="C1"),)
