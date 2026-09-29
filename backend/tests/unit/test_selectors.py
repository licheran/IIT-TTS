import pytest
from hypothesis import given
from hypothesis import strategies as st

from tts.core.model import Dataset, Event, FixedRequirement, Resource, ResourceType
from tts.core.selectors import (
    _OPS,
    ALL,
    AttrClause,
    CodeClause,
    KindClause,
    RefClause,
    Selector,
    SelectorError,
    Selectors,
    TagClause,
    TypeClause,
    UnderClause,
    UsesClause,
    check_target,
    format_selector,
    parse,
    select_events,
    select_resources,
)

# --- Parsing ------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["all", "  all  "])
def test_all_parses_to_the_empty_selector(text: str) -> None:
    assert parse(text) == ALL
    assert parse(text).is_all


@pytest.mark.parametrize(
    ("text", "clause"),
    [
        ("type:Seat", TypeClause("Seat")),
        ("under:Block A", UnderClause("Block A")),
        ("under:L6 SE / G1", UnderClause("L6 SE / G1")),
        ("ref:M-101", RefClause("M-101")),
        ("code:a,b, c", CodeClause(("a", "b", "c"))),
        ("kind:LEC,TUT", KindClause(("LEC", "TUT"))),
        ("tag:room_type=lab", TagClause("room_type", "lab")),
        ("tag:room_type!=lab", TagClause("room_type", "lab", negate=True)),
        ("attr:capacity>=30", AttrClause("capacity", ">=", "30")),
        ("attr:capacity<30", AttrClause("capacity", "<", "30")),
        ("attr:floor!=2", AttrClause("floor", "!=", "2")),
        ("attr:floor=2", AttrClause("floor", "=", "2")),
        ("attr:floor<=2", AttrClause("floor", "<=", "2")),
        ("attr:floor>2", AttrClause("floor", ">", "2")),
        ("uses:(under:X)", UsesClause(Selector((UnderClause("X"),)))),
        ("uses:(all)", UsesClause(ALL)),
    ],
)
def test_each_clause_parses(text: str, clause: object) -> None:
    assert parse(text) == Selector((clause,))  # type: ignore[arg-type]


def test_clauses_combine_with_semicolons_and_whitespace_is_trimmed() -> None:
    parsed = parse("  type : Seat ;  attr:capacity >= 30 ; tag: k = v ")
    assert parsed == Selector(
        (TypeClause("Seat"), AttrClause("capacity", ">=", "30"), TagClause("k", "v"))
    )


def test_quoted_values_may_contain_separators_and_keep_their_spaces() -> None:
    assert parse('code:"a;b","c,d", e') == Selector((CodeClause(("a;b", "c,d", "e")),))
    assert parse('tag:"a b"=" x ;y"') == Selector((TagClause("a b", " x ;y"),))
    assert parse('type:"has,comma"') == Selector((TypeClause("has,comma"),))


def test_escapes_inside_quotes() -> None:
    assert parse(r'code:"say \"hi\"", "back\\slash"') == Selector(
        (CodeClause(('say "hi"', "back\\slash")),)
    )


def test_uses_holds_a_full_selector_including_separators_and_quotes() -> None:
    parsed = parse('kind:LEC;uses:(under:X;tag:"a;b"=c);ref:M')
    assert parsed == Selector(
        (
            KindClause(("LEC",)),
            UsesClause(Selector((UnderClause("X"), TagClause("a;b", "c")))),
            RefClause("M"),
        )
    )


def test_uses_may_nest() -> None:
    parsed = parse("uses:(code:a;type:T)")
    assert isinstance(parsed.clauses[0], UsesClause)
    assert parse("uses:(uses:(all))") == Selector((UsesClause(Selector((UsesClause(ALL),))),))


def test_a_closing_paren_inside_quotes_does_not_end_uses() -> None:
    parsed = parse('uses:(code:"a)b")')
    assert parsed == Selector((UsesClause(Selector((CodeClause(("a)b",)),))),))


@pytest.mark.parametrize(
    ("text", "position", "fragment"),
    [
        ("", 0, "empty selector"),
        ("   ", 0, "empty selector"),
        ("teacher:", 0, 'unknown clause "teacher:"'),
        ("type:A;bogus:x", 7, 'unknown clause "bogus:"'),
        ("type", 0, 'expected "name:value"'),
        ("type:", 5, "type: needs a value"),
        ("type:A;", 7, "expected a clause"),
        ("type:A;;type:B", 7, 'expected "name:value"'),
        ("type:A,B", 5, "must be quoted"),
        ('code:"a', 5, "unterminated"),
        ('code:"a"b', 8, "unexpected text after a quoted value"),
        ('code:a"b', 6, "unexpected quote"),
        ("code:a,,b", 7, "code: needs a value"),
        ("tag:x", 0, "tag: needs an operator"),
        ("tag:=v", 4, "tag: needs a name"),
        ("attr:>5", 5, "attr: needs a name"),
        ("attr:capacity", 0, "attr: needs an operator"),
        ("uses:type:A", 5, "uses: expects a selector in parentheses"),
        ("uses:(type:A", 5, 'unclosed "("'),
        ("uses:(bogus:1)", 6, 'unknown clause "bogus:"'),
        ("uses:()", 6, "empty selector"),
        ("uses:(type:A)x", 13, 'expected ";"'),
    ],
)
def test_errors_carry_a_position_and_a_message(text: str, position: int, fragment: str) -> None:
    with pytest.raises(SelectorError) as caught:
        parse(text)
    assert fragment in caught.value.message
    assert caught.value.position == position


# --- Printing -----------------------------------------------------------------------------------


def test_format_is_canonical() -> None:
    assert format_selector(parse("  type : A ;  code: b , c ")) == "type:A;code:b,c"
    assert format_selector(ALL) == "all"
    assert format_selector(parse("uses:( kind:LEC )")) == "uses:(kind:LEC)"


def test_format_quotes_only_when_needed() -> None:
    assert format_selector(parse("under:L6 SE / G1")) == "under:L6 SE / G1"
    assert format_selector(parse('code:"a;b"')) == 'code:"a;b"'
    assert format_selector(parse(r'code:"a\"b"')) == r'code:"a\"b"'
    assert format_selector(parse('tag:"a=b"=c')) == 'tag:"a=b"=c'
    assert format_selector(parse('attr:x<"=5"')) == 'attr:x<"=5"'


VALUE_CHARS = st.sampled_from(list('abAB01 ;,"\\():=!<>/[]-_'))
values = st.text(VALUE_CHARS, min_size=1, max_size=6).filter(lambda s: s.strip() != "")
leaf_clauses = st.one_of(
    values.map(TypeClause),
    values.map(UnderClause),
    values.map(RefClause),
    st.lists(values, min_size=1, max_size=3).map(lambda v: CodeClause(tuple(v))),
    st.lists(values, min_size=1, max_size=3).map(lambda v: KindClause(tuple(v))),
    st.builds(TagClause, key=values, value=values, negate=st.booleans()),
    st.builds(AttrClause, name=values, op=st.sampled_from(_OPS), value=values),
)


def _selector_of(clauses: list[object]) -> Selector:
    return Selector(tuple(clauses))  # type: ignore[arg-type]


selectors = st.recursive(
    st.one_of(
        st.just(ALL),
        st.lists(leaf_clauses, min_size=1, max_size=3).map(_selector_of),
    ),
    lambda inner: st.lists(
        st.one_of(leaf_clauses, inner.map(UsesClause)), min_size=1, max_size=3
    ).map(_selector_of),
    max_leaves=6,
)


@given(selectors)
def test_printing_then_parsing_returns_the_same_tree(selector: Selector) -> None:
    assert parse(format_selector(selector)) == selector


@given(selectors)
def test_printing_is_stable(selector: Selector) -> None:
    text = format_selector(selector)
    assert format_selector(parse(text)) == text


# --- Evaluation ---------------------------------------------------------------------------------


@pytest.fixture
def ds() -> Dataset:
    return Dataset(
        resource_types=(
            ResourceType(code="N", exclusive=False),
            ResourceType(code="R", exclusive=True, has_capacity=True),
            ResourceType(code="S", exclusive=True, has_capacity=True),
            ResourceType(code="Q", exclusive=False),
            ResourceType(code="P", exclusive=True),
        ),
        resources=(
            Resource(code="site", type="N"),
            Resource(code="b1", type="N", parent="site"),
            Resource(
                code="r1",
                type="R",
                parent="b1",
                capacity=30,
                tags={"room_type": "lab"},
                attributes={"floor": 1, "wing": "east", "heated": True},
            ),
            Resource(
                code="r2",
                type="R",
                parent="b1",
                capacity=60,
                tags={"room_type": "lab"},
                attributes={"floor": 2, "heated": False},
            ),
            Resource(
                code="r3",
                type="R",
                parent="site",
                capacity=250,
                tags={"room_type": "hall"},
                attributes={"floor": 1},
            ),
            Resource(code="top", type="Q"),
            Resource(code="q1", type="S", parent="top", capacity=30),
            Resource(code="q2", type="S", parent="top", capacity=30),
            Resource(code="q3", type="S", parent="top", capacity=30),
            Resource(code="t1", type="P"),
        ),
        events=(
            Event(
                code="e1",
                kind="LEC",
                duration=1,
                start_pattern="s",
                reference="m1",
                tags={"week": "odd"},
            ),
            Event(code="e2", kind="TUT", duration=1, start_pattern="s", reference="m1"),
            Event(code="e3", kind="LEC", duration=1, start_pattern="s", reference="m2"),
        ),
        fixed=(
            FixedRequirement(event="e1", resource="q1"),
            FixedRequirement(event="e1", resource="q2"),
            FixedRequirement(event="e1", resource="t1"),
            FixedRequirement(event="e2", resource="q3"),
            FixedRequirement(event="e3", resource="top"),
        ),
    )


ALL_RESOURCES = {"site", "b1", "r1", "r2", "r3", "top", "q1", "q2", "q3", "t1"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("all", ALL_RESOURCES),
        ("type:R", {"r1", "r2", "r3"}),
        ("type:Nothing", set()),
        ("under:b1", {"r1", "r2"}),
        ("under:site", {"r1", "r2", "r3"}),
        ("under:top", {"q1", "q2", "q3"}),
        ("under:r1", set()),
        ("under:missing", set()),
        ("code:r1,q1,missing", {"r1", "q1"}),
        ("tag:room_type=lab", {"r1", "r2"}),
        ("tag:room_type!=lab", ALL_RESOURCES - {"r1", "r2"}),
        ("attr:capacity>=60", {"r2", "r3"}),
        ("attr:capacity>60", {"r3"}),
        ("attr:capacity<30", set()),
        ("attr:capacity<=30", {"r1", "q1", "q2", "q3"}),
        ("attr:capacity=30", {"r1", "q1", "q2", "q3"}),
        ("attr:capacity!=30", {"r2", "r3"}),
        ("attr:floor=1", {"r1", "r3"}),
        ("attr:wing=east", {"r1"}),
        ("attr:wing>a", {"r1"}),
        ("attr:heated=true", {"r1"}),
        ("attr:heated=FALSE", {"r2"}),
        ("type:R;under:b1;attr:capacity>=60", {"r2"}),
        ("type:R;type:S", set()),
    ],
)
def test_resource_selection(ds: Dataset, text: str, expected: set[str]) -> None:
    assert Selectors(ds).resources(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("all", {"e1", "e2", "e3"}),
        ("kind:LEC", {"e1", "e3"}),
        ("kind:LEC,TUT", {"e1", "e2", "e3"}),
        ("kind:LAB", set()),
        ("ref:m1", {"e1", "e2"}),
        ("code:e2,e9", {"e2"}),
        ("tag:week=odd", {"e1"}),
        ("tag:week!=odd", {"e2", "e3"}),
        ("uses:(code:q1)", {"e1"}),
        ("uses:(type:S)", {"e1", "e2"}),
        ("uses:(code:top)", {"e3"}),
        ("uses:(type:P)", {"e1"}),
        ("uses:(all)", {"e1", "e2", "e3"}),
        ("uses:(type:Nothing)", set()),
        ("kind:LEC;uses:(type:P)", {"e1"}),
        ("kind:TUT;uses:(type:P)", set()),
    ],
)
def test_event_selection(ds: Dataset, text: str, expected: set[str]) -> None:
    assert Selectors(ds).events(text) == expected


def test_uses_matches_a_fixed_resource_and_not_its_descendants(ds: Dataset) -> None:
    """`e3` is fixed on `top`, and `under:top` excludes `top` itself, so `uses:(under:top)`
    skips it. This is the literal reading of "has a fixed resource matching" (spec 02 section 5).
    """
    assert Selectors(ds).events("uses:(under:top)") == {"e1", "e2"}


def test_a_selector_object_can_be_evaluated_as_well_as_text(ds: Dataset) -> None:
    sel = parse("type:R")
    assert Selectors(ds).resources(sel) == {"r1", "r2", "r3"}


def test_module_level_helpers_match_the_class(ds: Dataset) -> None:
    assert select_resources(ds, "type:R") == Selectors(ds).resources("type:R")
    assert select_events(ds, "kind:LEC") == Selectors(ds).events("kind:LEC")


@pytest.mark.parametrize(
    ("text", "position"),
    [("kind:LEC", 0), ("type:R;ref:m1", 7), ("uses:(all)", 0)],
)
def test_event_clauses_do_not_select_resources(ds: Dataset, text: str, position: int) -> None:
    with pytest.raises(SelectorError) as caught:
        Selectors(ds).resources(text)
    assert "does not select resources" in caught.value.message
    assert caught.value.position == position


@pytest.mark.parametrize(
    ("text", "position"),
    [("type:R", 0), ("kind:LEC;under:x", 9), ("attr:capacity>1", 0)],
)
def test_resource_clauses_do_not_select_events(ds: Dataset, text: str, position: int) -> None:
    with pytest.raises(SelectorError) as caught:
        Selectors(ds).events(text)
    assert "does not select events" in caught.value.message
    assert caught.value.position == position


def test_the_inside_of_uses_must_select_resources(ds: Dataset) -> None:
    with pytest.raises(SelectorError) as caught:
        Selectors(ds).events("uses:(kind:LEC)")
    assert "does not select resources" in caught.value.message
    assert caught.value.position == 6


def test_check_target_validates_without_a_dataset() -> None:
    check_target("type:R;code:x", "resource")
    check_target("kind:LEC;code:x;uses:(type:R)", "event")
    with pytest.raises(SelectorError):
        check_target("kind:LEC", "resource")


def test_a_bad_attribute_value_reports_the_clause_position(ds: Dataset) -> None:
    with pytest.raises(SelectorError, match="is a number") as caught:
        Selectors(ds).resources("type:R;attr:floor=high")
    assert caught.value.position == 7
    with pytest.raises(SelectorError, match="true or false"):
        Selectors(ds).resources("attr:heated=maybe")
