"""Quality gate 4 (spec 06 section 8): every catalogue type is fully implemented and tested.

For each declared type of `docs/spec/04-constraints.md` there must be a `core/constraints/<type>.py`
with `TYPE`, `Params` and `verify`, a `solver/constraints/<type>.py` with `compile`, an entry in
both registries, and `tests/unit/constraints/test_<type>.py` with the three tests of spec 04
section 4: verify cases (`test_verify_*`), solver-matches-verifier (`test_solver_*`) and the hard
infeasible instance named by the explanation (`test_hard_*`).
"""

import ast
import importlib
from pathlib import Path

import pytest

from tts.core.constraints.catalogue import CATALOGUE
from tts.core.constraints.registry import DECLARED
from tts.solver.registry import COMPILERS

TESTS = Path(__file__).parent / "constraints"


@pytest.mark.parametrize("type_name", sorted(CATALOGUE))
def test_the_core_module_verifies_the_type(type_name: str) -> None:
    module = importlib.import_module(f"tts.core.constraints.{type_name}")
    assert type_name == module.TYPE
    assert callable(module.verify)
    assert hasattr(module.Params, "model_validate")
    assert DECLARED[type_name] is module


@pytest.mark.parametrize("type_name", sorted(CATALOGUE))
def test_the_solver_module_compiles_the_type(type_name: str) -> None:
    module = importlib.import_module(f"tts.solver.constraints.{type_name}")
    assert COMPILERS[type_name] is module.compile


@pytest.mark.parametrize("type_name", sorted(CATALOGUE))
def test_the_type_has_the_three_kinds_of_test(type_name: str) -> None:
    path = TESTS / f"test_{type_name}.py"
    assert path.exists(), f"missing {path.name}"
    names = [
        node.name
        for node in ast.parse(path.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef)
    ]
    for prefix in ("test_verify_", "test_solver_", "test_hard_"):
        assert any(n.startswith(prefix) for n in names), f"{path.name} has no {prefix}* test"
    assert sum(n.startswith("test_verify_") for n in names) >= 3  # 0, 1 and several violations


def test_nothing_is_registered_outside_the_catalogue() -> None:
    assert set(DECLARED) == set(COMPILERS) == set(CATALOGUE)
