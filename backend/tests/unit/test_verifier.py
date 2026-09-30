from types import SimpleNamespace
from typing import Any

import pytest

from fixtures import at, ev, make_dataset, make_result, pick, pool, res, unavailable
from tts.core.constraints.base import NoParams
from tts.core.constraints.context import VerifyContext
from tts.core.constraints.registry import DECLARED
from tts.core.model import Constraint, Dataset, Ref, Result, Violation
from tts.core.verifier import UNSUPPORTED, hard_violations, verify


def good_dataset() -> Dataset:
    return make_dataset(
        resources=[
            res("top", "N"),
            res("c1", "G", "top", capacity=30),
            res("c2", "G", "top", capacity=30),
            res("r1", "R", capacity=60, kind="lab"),
            res("r2", "R", capacity=10, kind="lab"),
        ],
        events=[ev("e1"), ev("e2")],
        fixed=[("e1", "top"), ("e2", "c1")],
        pooled=[
            pool("e1", filter="tag:kind=lab", rule="sum_of_fixed:G"),
            pool("e2", filter="tag:kind=lab", rule="sum_of_fixed:G"),
        ],
    )


def good_result() -> Result:
    return make_result(
        at("e1", "d1", "p1", pick(0, "r1")),
        at("e2", "d1", "p2", pick(0, "r1")),
    )


def test_a_valid_result_has_no_violations() -> None:
    assert verify(good_dataset(), good_result()) == []


def test_violations_from_every_rule_are_returned_in_catalogue_order() -> None:
    ds = make_dataset(
        resources=[
            res("top", "N"),
            res("c1", "G", "top", capacity=30),
            res("r1", "R", capacity=10, kind="hall"),
        ],
        events=[ev("e1"), ev("e2"), ev("e3")],
        fixed=[("e1", "top"), ("e2", "c1"), ("e3", "c1")],
        pooled=[
            pool("e1", filter="tag:kind=lab", rule="sum_of_fixed:G"),
            pool("e2"),
        ],
        availability=[unavailable("c1", "d1", "p3")],
    )
    result = make_result(
        at("e1", "d1", "p1", pick(0, "r1")),  # capacity 10 < 30 (H3), hall is not a lab (H4)
        at("e2", "d1", "p1", pick(0, "r1")),  # c1 clashes with e1 (H1), r1 double-booked (H1)
        # e3 is not placed (H0)
    )
    codes = [v.constraint_code for v in verify(ds, result)]
    assert codes == sorted(codes)  # H0 < H1 < H2 < H3 < H4 < H5
    assert set(codes) == {"H0", "H1", "H3", "H4"}
    # e1 (on the parent) and e2 clash on c1 and on r1: one violation per resource.
    assert codes.count("H1") == 2


def test_the_result_can_be_checked_without_any_solver() -> None:
    """An externally supplied result (for example an import of another tool's timetable)."""
    external = make_result(at("e1", "d1", "p1", pick(0, "r2")))
    found = verify(good_dataset(), external)
    assert {v.constraint_code for v in found} == {"H0", "H3"}


def test_hard_violations_filters_by_severity() -> None:
    ds = good_dataset().model_copy(
        update={"constraints": (Constraint(code="C-X", type="not_a_type", hard=False),)}
    )
    found = verify(ds, make_result())
    assert {v.severity for v in found} == {"hard", "warning"}
    assert all(v.severity == "hard" for v in hard_violations(found))
    assert len(hard_violations(found)) == 2  # both events unplaced


# --- Declared constraints -------------------------------------------------------------------


def with_constraints(*constraints: Constraint) -> Dataset:
    return good_dataset().model_copy(update={"constraints": constraints})


def test_a_declared_type_without_a_verifier_gives_one_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(DECLARED, "max_days")
    ds = with_constraints(Constraint(code="C1", type="max_days", scope="type:G", params={"max": 1}))
    found = verify(ds, good_result())
    assert len(found) == 1
    v = found[0]
    assert (v.code, v.constraint_code, v.severity, v.penalty) == (UNSUPPORTED, "C1", "warning", 0)
    assert v.refs == (Ref(kind="constraint", code="C1"),)
    assert '"max_days"' in v.message


def test_each_unsupported_instance_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(DECLARED, "max_days")
    ds = with_constraints(
        Constraint(code="C1", type="max_days"),
        Constraint(code="C2", type="max_days"),
        Constraint(code="C3", type="never_heard_of_it"),
    )
    assert [v.constraint_code for v in verify(ds, good_result())] == ["C1", "C2", "C3"]


def test_inactive_constraints_are_ignored() -> None:
    ds = with_constraints(Constraint(code="C1", type="max_days", active=False))
    assert verify(ds, good_result()) == []


@pytest.fixture
def fake_type(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    calls: list[tuple[Dataset, Result, VerifyContext | None]] = []

    def fake_verify(
        dataset: Dataset, result: Result, context: VerifyContext | None = None
    ) -> list[Violation]:
        calls.append((dataset, result, context))
        return [
            Violation(code="fake", constraint_code=c.code, severity="soft", penalty=2)
            for c in dataset.constraints
            if c.type == "fake" and c.active
        ]

    fake: Any = SimpleNamespace(Params=NoParams, verify=fake_verify, calls=calls)
    monkeypatch.setitem(DECLARED, "fake", fake)
    return fake


def test_a_registered_declared_type_is_verified_once_with_the_shared_context(
    fake_type: SimpleNamespace,
) -> None:
    ds = with_constraints(
        Constraint(code="C1", type="fake", hard=False),
        Constraint(code="C2", type="fake", hard=False),
        Constraint(code="C3", type="fake", active=False),
    )
    found = verify(ds, good_result())
    assert [(v.constraint_code, v.severity, v.penalty) for v in found] == [
        ("C1", "soft", 2),
        ("C2", "soft", 2),
    ]
    assert len(fake_type.calls) == 1
    assert isinstance(fake_type.calls[0][2], VerifyContext)


def test_a_type_with_only_inactive_instances_is_not_called(fake_type: SimpleNamespace) -> None:
    ds = with_constraints(Constraint(code="C1", type="fake", active=False))
    assert verify(ds, good_result()) == []
    assert fake_type.calls == []


def test_the_output_does_not_depend_on_input_order() -> None:
    a = good_dataset()
    b = Dataset(
        resource_types=tuple(reversed(a.resource_types)),
        resources=tuple(reversed(a.resources)),
        time=a.time,
        events=tuple(reversed(a.events)),
        fixed=tuple(reversed(a.fixed)),
        pooled=tuple(reversed(a.pooled)),
    )
    bad = make_result(at("e1", "d1", "p1", pick(0, "r2")), at("e2", "d1", "p1", pick(0, "r2")))
    assert verify(a, bad) == verify(b, bad)
    assert verify(a, bad) == verify(a, bad)
