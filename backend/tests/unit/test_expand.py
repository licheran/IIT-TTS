"""Expanding templates into events (spec 05 section 2)."""

from fixtures import ev, make_dataset, res
from tts.core.model import (
    Dataset,
    FixedRequirement,
    Pin,
    PooledSpec,
    Reference,
    ReferenceType,
    Template,
)
from tts.expand.templates import ORDER_PREFIX, expand

ORDERING = (("A", "B"),)  # kind A comes before kind B


def template(code: str, mode: str = "joint", targets: str = "type:G", **fields) -> Template:
    fields.setdefault("kind", "A")
    fields.setdefault("duration", 1)
    fields.setdefault("start_pattern", "all")
    return Template(code=code, mode=mode, targets=targets, **fields)


def dataset(*templates: Template, events=(), fixed=(), pins=()) -> Dataset:
    ds = make_dataset(
        resources=[
            res("p", "N"),
            *(res(f"g{i}", parent="p") for i in (3, 1, 2)),
            res("t1", "T"),
            res("r1", "R"),
        ],
        events=events,
        fixed=fixed,
        pins=pins,
        validate=False,
    )
    return ds.model_copy(
        update={
            "templates": tuple(sorted(templates, key=lambda t: t.code)),
            "reference_types": (ReferenceType(code="M"),),
            "references": (Reference(code="m1", type="M"), Reference(code="m2", type="M")),
        }
    )


def groups_of(ds: Dataset, event: str) -> list[str]:
    return sorted(f.resource for f in ds.fixed if f.event == event and f.resource.startswith("g"))


def test_joint_gives_one_event_with_every_target() -> None:
    out = expand(dataset(template("J", fixed=("t1",))))
    (event,) = out.dataset.events
    assert event.code == "J-A-01" and event.template == "J"
    assert groups_of(out.dataset, "J-A-01") == ["g1", "g2", "g3"]
    assert FixedRequirement(event="J-A-01", resource="t1") in out.dataset.fixed


def test_each_gives_one_event_per_target_in_code_order() -> None:
    out = expand(dataset(template("E", mode="each")))
    assert [(e.code, groups_of(out.dataset, e.code)) for e in out.dataset.events] == [
        ("E-A-01", ["g1"]),
        ("E-A-02", ["g2"]),
        ("E-A-03", ["g3"]),
    ]


def test_batched_cuts_the_sorted_targets_into_batches() -> None:
    out = expand(dataset(template("B", mode="batched", batch_size=2)))
    assert [groups_of(out.dataset, e.code) for e in out.dataset.events] == [["g1", "g2"], ["g3"]]


def test_sessions_per_week_repeat_every_event() -> None:
    out = expand(dataset(template("S", mode="each", sessions_per_week=2)))
    assert len(out.dataset.events) == 6


def test_codes_use_the_reference_and_skip_codes_taken_by_hand_made_events() -> None:
    ds = dataset(
        template("T1", mode="each", reference="m1"),
        events=[ev("m1-A-02")],
    )
    codes = [e.code for e in expand(ds).dataset.events]
    assert codes == ["m1-A-01", "m1-A-02", "m1-A-03", "m1-A-04"]  # m1-A-02 is the hand-made one


def test_pooled_specs_become_requirements_and_no_pool_sets_the_delivery() -> None:
    spec = PooledSpec(resource_type="R", count=1)
    out = expand(
        dataset(template("P", pooled=(spec,)), template("Q", kind="B")),
        unpooled_delivery="elsewhere",
    )
    by_code = {e.code: e for e in out.dataset.events}
    assert by_code["P-A-01"].delivery == "in_person"
    assert by_code["Q-B-01"].delivery == "elsewhere"
    assert [(q.event, q.resource_type) for q in out.dataset.pooled] == [("P-A-01", "R")]


def test_order_constraints_link_each_earlier_event_to_later_ones_that_share_a_target() -> None:
    ds = dataset(
        template("L", reference="m1", targets="code:g1,g2"),
        template("T", reference="m1", kind="B", mode="each"),
        template("X", reference="m2", kind="B", mode="each"),
    )
    orders = [c for c in expand(ds, ordering=ORDERING).dataset.constraints]
    assert [c.params["sequence"] for c in orders] == [
        ["m1-A-01", "m1-B-01"],
        ["m1-A-01", "m1-B-02"],
    ]
    assert all(c.code.startswith(ORDER_PREFIX) and not c.hard and c.weight == 1 for c in orders)


def test_expanding_twice_changes_nothing() -> None:
    ds = dataset(
        template("L", reference="m1"),
        template("T", reference="m1", kind="B", mode="batched", batch_size=2),
    )
    once = expand(ds, ordering=ORDERING)
    twice = expand(once.dataset, ordering=ORDERING)
    assert twice.dataset == once.dataset
    assert twice.diff.empty


def test_hand_made_events_and_their_rows_are_untouched() -> None:
    ds = dataset(template("J"), events=[ev("mine")], fixed=[("mine", "g1")])
    out = expand(ds).dataset
    assert ev("mine") in out.events
    assert FixedRequirement(event="mine", resource="g1") in out.fixed


def test_changing_a_template_reports_what_was_added_changed_and_removed() -> None:
    before = expand(dataset(template("E", mode="each"))).dataset
    edited = before.model_copy(
        update={"templates": (template("E", mode="each", targets="code:g1,g2", duration=2),)}
    )
    diff = expand(edited).diff
    assert (diff.added, diff.changed, diff.removed) == ((), ("E-A-01", "E-A-02"), ("E-A-03",))


def test_an_inactive_template_removes_its_events() -> None:
    before = expand(dataset(template("E", mode="each"))).dataset
    off = before.model_copy(update={"templates": (template("E", mode="each", active=False),)})
    out = expand(off)
    assert out.dataset.events == () and out.diff.removed == ("E-A-01", "E-A-02", "E-A-03")


def test_pins_stay_on_events_that_still_exist() -> None:
    before = expand(dataset(template("E", mode="each"))).dataset
    pinned = before.model_copy(
        update={
            "pins": (Pin(event="E-A-01", day="d1"), Pin(event="E-A-03", day="d2")),
            "templates": (template("E", mode="each", targets="code:g1,g2"),),
        }
    )
    assert [p.event for p in expand(pinned).dataset.pins] == ["E-A-01"]


def test_a_template_that_cannot_be_expanded_is_reported_and_skipped() -> None:
    out = expand(dataset(template("Bad", targets="nonsense:x"), template("Ok")))
    assert [e.template for e in out.dataset.events] == ["Ok"]
    assert len(out.problems) == 1 and "Bad" in out.problems[0]


def test_the_expanded_dataset_is_sound() -> None:
    ds = dataset(
        template("L", reference="m1", fixed=("t1",), pooled=(PooledSpec(resource_type="R"),)),
        template("T", reference="m1", kind="B", mode="each"),
    )
    assert expand(ds, ordering=ORDERING).dataset.validate_invariants() == []
