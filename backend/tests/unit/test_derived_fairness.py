"""The fairness rules a configuration implies (spec 04 section 3, ADR-0008)."""

from academic_config import dataset, replaced, with_sessions

from tts.api.expansion import prepare_with_preset
from tts.core.model import Constraint, Dataset, Event
from tts.presets import derive_constraints
from tts.presets.academic_weekly.configuration import derived_constraints


def by_code(ds: Dataset) -> dict[str, Constraint]:
    return {c.code: c for c in derived_constraints(ds)}


def test_a_teacher_with_max_hours_gets_a_hard_weekly_cap_in_periods() -> None:
    ds = replaced(dataset(), "T1", max_hours=18)
    cap = by_code(ds)["LOAD-T1"]
    assert (cap.type, cap.scope, cap.hard) == ("max_load", "code:T1", True)
    assert cap.params == {"max": 18, "unit": "periods"}


def test_a_teacher_without_max_hours_has_no_cap() -> None:
    assert [c for c in by_code(dataset()) if c.startswith("LOAD-")] == []


def test_a_zero_cap_is_a_cap() -> None:
    assert by_code(replaced(dataset(), "T3", max_hours=0))["LOAD-T3"].params["max"] == 0


def test_a_module_with_two_teachers_gets_a_soft_balance_rule() -> None:
    found = by_code(dataset())
    balance = found["FAIR-M1"]  # T1 teaches M1, T2 teaches its tutorials
    assert (balance.type, balance.scope, balance.hard, balance.weight) == (
        "balance_load",
        "code:T1,T2",
        False,
        2,
    )
    assert balance.params == {"unit": "periods"}
    assert "FAIR-M2" not in found and "FAIR-M3" not in found  # one teacher each


def test_a_session_row_with_two_teachers_gets_a_soft_continuity_rule() -> None:
    found = by_code(dataset())
    keep = found["CONT-M1-TUT"]  # T1 and T2 can take the tutorials
    assert (keep.type, keep.scope, keep.hard, keep.weight) == (
        "same_resource",
        "ref:M1;kind:TUT",
        False,
        3,
    )
    assert keep.params == {"type": "Teacher", "per": "StudentGroup"}
    assert "CONT-M1-LEC" not in found  # only T1 can take the lectures


def test_a_session_type_the_module_lacks_makes_no_continuity_rule() -> None:
    ds = with_sessions(dataset(), "M1", "LEC")
    assert "CONT-M1-TUT" not in by_code(ds)


def test_only_configured_datasets_get_derived_rules() -> None:
    assert len(derive_constraints(dataset())) > 0
    typed = Event(code="E1", kind="LEC", duration=2, start_pattern="2H")
    hand_made = dataset().model_copy(update={"events": (typed,)})
    assert hand_made.kind == "hand_made"
    assert derive_constraints(hand_made) == ()


def test_the_prepared_dataset_carries_the_derived_rules_and_stores_none() -> None:
    ds = dataset()
    assert ds.constraints == ()
    prepared = prepare_with_preset(ds)
    assert {"FAIR-M1", "CONT-M1-TUT"} <= {c.code for c in prepared.constraints}
    assert [c.code for c in prepared.constraints] == sorted(c.code for c in prepared.constraints)


def test_a_stored_constraint_with_the_same_code_wins() -> None:
    off = Constraint(
        code="FAIR-M1", type="balance_load", scope="code:T1,T2", hard=False, weight=9, active=False
    )
    prepared = prepare_with_preset(dataset(constraints=(off,)))
    assert [c for c in prepared.constraints if c.code == "FAIR-M1"] == [off]


def test_derived_rules_are_valid_for_the_core() -> None:
    prepared = prepare_with_preset(replaced(dataset(), "T1", max_hours=10))
    assert [i for i in prepared.validate_invariants() if i.table == "constraint"] == []
