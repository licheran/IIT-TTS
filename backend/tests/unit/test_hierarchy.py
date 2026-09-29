from collections.abc import Sequence

from tts.core.hierarchy import Hierarchy, detect_cycles
from tts.core.model import Dataset, Event, FixedRequirement, Resource, ResourceType


def build(
    resources: Sequence[tuple[str, str, str | None]],
    fixed: Sequence[tuple[str, str]] = (),
) -> Dataset:
    """Resources as (code, type, parent). Type `N` is non-exclusive, `E` is exclusive."""
    events = sorted({event for event, _ in fixed})
    return Dataset(
        resource_types=(
            ResourceType(code="N", exclusive=False),
            ResourceType(code="E", exclusive=True),
        ),
        resources=tuple(Resource(code=c, type=t, parent=p) for c, t, p in resources),
        events=tuple(Event(code=e, kind="K", duration=1, start_pattern="s") for e in events),
        fixed=tuple(FixedRequirement(event=e, resource=r) for e, r in fixed),
    )


# A grouping parent "top" (non-exclusive) with three exclusive children.
GROUPING = [
    ("top", "N", None),
    ("c1", "E", "top"),
    ("c2", "E", "top"),
    ("c3", "E", "top"),
]


def test_children_are_sorted_and_direct_only() -> None:
    h = Hierarchy(build([*GROUPING, ("c1a", "E", "c1")]))
    assert h.children("top") == ("c1", "c2", "c3")
    assert h.children("c1") == ("c1a",)
    assert h.children("c2") == ()
    assert h.children("unknown") == ()


def test_ancestors_run_from_parent_to_root() -> None:
    h = Hierarchy(build([("root", "N", None), ("mid", "N", "root"), ("leaf", "E", "mid")]))
    assert h.ancestors("leaf") == ("mid", "root")
    assert h.ancestors("root") == ()
    assert h.parent("leaf") == "mid"
    assert h.parent("root") is None


def test_event_on_a_grouping_parent_occupies_its_exclusive_children() -> None:
    h = Hierarchy(build(GROUPING, [("e", "top")]))
    assert h.occupied_resources("e") == {"top", "c1", "c2", "c3"}
    assert h.occupied_exclusive("e") == {"c1", "c2", "c3"}


def test_event_on_a_child_does_not_occupy_the_parent_or_siblings() -> None:
    h = Hierarchy(build(GROUPING, [("e", "c1")]))
    assert h.occupied_resources("e") == {"c1"}
    assert "top" not in h.occupied_resources("e")


def test_two_children_of_one_parent_do_not_share_occupied_resources() -> None:
    h = Hierarchy(build(GROUPING, [("e1", "c1"), ("e2", "c2")]))
    assert h.occupied_exclusive("e1") & h.occupied_exclusive("e2") == frozenset()


def test_event_on_the_parent_and_event_on_a_child_share_the_child() -> None:
    h = Hierarchy(build(GROUPING, [("whole", "top"), ("part", "c2")]))
    assert h.occupied_exclusive("whole") & h.occupied_exclusive("part") == {"c2"}


def test_nested_subgroups_are_all_occupied() -> None:
    resources = [
        ("top", "N", None),
        ("c1", "E", "top"),
        ("c1a", "E", "c1"),
        ("c1b", "E", "c1"),
        ("c1a-i", "E", "c1a"),
        ("c2", "E", "top"),
    ]
    h = Hierarchy(build(resources, [("e", "c1"), ("f", "top")]))
    assert h.occupied_resources("e") == {"c1", "c1a", "c1b", "c1a-i"}
    assert h.occupied_exclusive("f") == {"c1", "c1a", "c1b", "c1a-i", "c2"}


def test_exclusive_descendants_pass_through_non_exclusive_nodes() -> None:
    resources = [("l", "N", None), ("p", "N", "l"), ("g", "E", "p"), ("h", "N", "p")]
    h = Hierarchy(build(resources))
    assert h.exclusive_descendants("l") == {"g"}
    assert h.descendants("l") == {"p", "g", "h"}
    assert h.exclusive_descendants("g") == frozenset()


def test_chosen_pooled_resources_are_occupied_too() -> None:
    h = Hierarchy(build([*GROUPING, ("r1", "E", None), ("r2", "E", None)], [("e", "c1")]))
    assert h.occupied_resources("e", ["r1"]) == {"c1", "r1"}
    assert h.occupied_exclusive("e", ["r1", "r2"]) == {"c1", "r1", "r2"}


def test_event_without_fixed_resources_occupies_only_its_choices() -> None:
    h = Hierarchy(build([("r1", "E", None)]))
    assert h.occupied_resources("ghost") == frozenset()
    assert h.occupied_resources("ghost", ["r1"]) == {"r1"}
    assert h.fixed_resources("ghost") == ()


def test_is_exclusive_follows_the_resource_type() -> None:
    h = Hierarchy(build(GROUPING))
    assert h.is_exclusive("c1")
    assert not h.is_exclusive("top")
    assert not h.is_exclusive("unknown")


# --- Cycles ------------------------------------------------------------------------------------


def test_acyclic_hierarchy_has_no_cycles() -> None:
    assert detect_cycles(build(GROUPING)) == []


def test_self_parent_is_a_cycle() -> None:
    assert detect_cycles(build([("a", "E", "a")])) == [("a",)]


def test_two_and_three_cycles_start_at_their_smallest_code() -> None:
    resources = [
        ("b", "E", "a"),
        ("a", "E", "b"),
        ("z", "E", "y"),
        ("y", "E", "x"),
        ("x", "E", "z"),
    ]
    assert detect_cycles(build(resources)) == [("a", "b"), ("x", "z", "y")]


def test_a_node_leading_into_a_cycle_is_not_part_of_it() -> None:
    resources = [("tail", "E", "a"), ("a", "E", "b"), ("b", "E", "a")]
    assert detect_cycles(build(resources)) == [("a", "b")]


def test_unknown_parents_are_not_cycles() -> None:
    assert detect_cycles(build([("a", "E", "ghost")])) == []


def test_queries_terminate_on_a_cyclic_hierarchy() -> None:
    h = Hierarchy(build([("a", "E", "b"), ("b", "E", "a")], [("e", "a")]))
    assert h.ancestors("a") == ("b",)
    assert h.descendants("a") == {"b"}
    assert h.occupied_exclusive("e") == {"a", "b"}


def test_validate_invariants_reports_hierarchy_cycles() -> None:
    issues = build([("a", "E", "b"), ("b", "E", "a"), ("ok", "E", None)]).validate_invariants()
    assert [(i.kind, i.key, i.message) for i in issues] == [
        ("hierarchy_cycle", "a", "parent cycle: a → b → a")
    ]
