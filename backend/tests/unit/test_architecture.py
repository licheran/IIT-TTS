"""Architecture rules.

Covers the package dependency table (spec 06 section 3) and core purity (CLAUDE.md rule 1).
The scanners take a source root so the meta tests below can prove they catch violations.
"""

import ast
import io
import re
import sys
import tokenize
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "tts"

# --- Dependency rules --------------------------------------------------------------------------

# Internal packages each restricted package may import (always including itself).
ALLOWED_INTERNAL: dict[str, set[str]] = {
    "core": {"core"},
    "expand": {"core", "expand"},
    "preflight": {"core", "preflight"},
    "solver": {"core", "solver"},
    "io": {"core", "presets", "io"},
    "presets": {"core", "presets"},
    "store": {"core", "store"},
}

# Third-party top-level modules each restricted package may import. Extending a list is a
# reviewed change: it widens what the pure packages may depend on.
ALLOWED_THIRD_PARTY: dict[str, set[str]] = {
    "core": {"pydantic"},
    "expand": {"pydantic"},
    "preflight": {"pydantic"},
    "presets": {"pydantic"},
    "solver": {"pydantic", "ortools"},
    "io": {"pydantic", "openpyxl", "bs4", "jinja2", "pandas"},
    "store": {"pydantic", "sqlalchemy", "alembic"},
}
# api, worker and cli (and tts/__init__.py) may import anything.


def _module_parts(root: Path, path: Path) -> tuple[str, ...]:
    rel = path.relative_to(root).with_suffix("")
    return ("tts", *rel.parts)


def _imported_modules(root: Path, path: Path) -> list[str]:
    """Absolute dotted names imported by a file, with relative imports resolved."""
    # The containing package is the module path minus its last part (also for __init__.py).
    package = _module_parts(root, path)[:-1]
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)]
                module = ".".join([*base, *(node.module.split(".") if node.module else [])])
            else:
                module = node.module or ""
            if module == "tts":
                found.extend(f"tts.{alias.name}" for alias in node.names)
            else:
                found.append(module)
    return found


def dependency_violations(root: Path) -> list[str]:
    problems: list[str] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        owner = rel.parts[0].removesuffix(".py")
        if owner not in ALLOWED_INTERNAL:
            continue
        for name in _imported_modules(root, path):
            top = name.split(".")[0]
            if top == "tts":
                target = name.split(".")[1] if "." in name else ""
                if target and target not in ALLOWED_INTERNAL[owner]:
                    problems.append(f"{rel}: '{owner}' may not import tts.{target} ({name})")
            elif top not in sys.stdlib_module_names and top not in ALLOWED_THIRD_PARTY[owner]:
                problems.append(f"{rel}: '{owner}' may not import third-party '{top}'")
    return problems


def test_packages_follow_the_dependency_rules() -> None:
    assert dependency_violations(SRC) == []


def test_core_never_imports_the_solver() -> None:
    offenders = [
        f"{path.relative_to(SRC)} -> {name}"
        for path in (SRC / "core").rglob("*.py")
        for name in _imported_modules(SRC, path)
        if name == "tts.solver" or name.startswith("tts.solver.")
    ]
    assert offenders == []


# --- Core purity -------------------------------------------------------------------------------

PURE_PACKAGES = ("core", "solver", "expand", "preflight")
BANNED_WORDS = {
    "teacher",
    "room",
    "module",
    "student",
    "lecture",
    "tutorial",
    "group",
}
# (relative path, word) -> reason. Every entry is a reviewed exception to CLAUDE.md rule 1.
PURITY_ALLOWLIST: dict[tuple[str, str], str] = {}

_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def _words(text: str) -> set[str]:
    """Lower-case words of an identifier or string, split on non-letters and camelCase.

    Plurals count as the same word.
    """
    result = set()
    for word in _WORD.findall(text):
        lowered = word.lower()
        result.add(lowered)
        if lowered.endswith("s"):
            result.add(lowered[:-1])
    return result


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                lines.update(range(body[0].lineno, (body[0].end_lineno or body[0].lineno) + 1))
    return lines


def banned_words_in(source: str) -> set[str]:
    """Banned words in identifiers and string literals. Comments and docstrings are ignored."""
    skip = _docstring_lines(ast.parse(source))
    hits: set[str] = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.NAME:
            if tok.string.startswith("__") and tok.string.endswith("__"):
                continue
            hits |= _words(tok.string) & BANNED_WORDS
        elif tok.type == tokenize.STRING and tok.start[0] not in skip:
            hits |= _words(tok.string) & BANNED_WORDS
    return hits


def purity_violations(root: Path) -> list[str]:
    problems: list[str] = []
    for package in PURE_PACKAGES:
        for path in sorted((root / package).rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            for word in sorted(banned_words_in(path.read_text(encoding="utf-8"))):
                if (rel, word) not in PURITY_ALLOWLIST:
                    problems.append(f"{rel}: domain word '{word}'")
    return problems


def test_core_packages_contain_no_domain_words() -> None:
    assert purity_violations(SRC) == []


def test_every_purity_allowlist_entry_has_a_reason() -> None:
    assert all(reason.strip() for reason in PURITY_ALLOWLIST.values())


# --- Meta tests: the scanners really catch violations --------------------------------------------


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("rel", "code", "fragment"),
    [
        ("core/a.py", "import tts.solver.compile\n", "may not import tts.solver"),
        ("core/a.py", "from tts import presets\n", "may not import tts.presets"),
        ("core/a.py", "from ..solver import x\n", "may not import tts.solver"),
        ("core/a.py", "import ortools\n", "third-party 'ortools'"),
        ("solver/a.py", "from tts.io import workbook\n", "may not import tts.io"),
        ("expand/a.py", "import fastapi\n", "third-party 'fastapi'"),
    ],
)
def test_dependency_scanner_flags_forbidden_imports(
    tmp_path: Path, rel: str, code: str, fragment: str
) -> None:
    _write(tmp_path, rel, code)
    problems = dependency_violations(tmp_path)
    assert len(problems) == 1
    assert fragment in problems[0]


def test_dependency_scanner_accepts_allowed_imports(tmp_path: Path) -> None:
    _write(tmp_path, "core/a.py", "import json\nfrom pydantic import BaseModel\nfrom . import b\n")
    _write(tmp_path, "solver/a.py", "from tts.core import model\nimport ortools\n")
    _write(tmp_path, "api/a.py", "from tts.solver import solve\nimport fastapi\n")
    assert dependency_violations(tmp_path) == []


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("teacher = 1\n", {"teacher"}),
        ("def assign_room(x): ...\n", {"room"}),
        ("class StudentGroup: ...\n", {"student", "group"}),
        ("x = 'Lecture'\n", {"lecture"}),
        ("rooms = []\n", {"room"}),
    ],
)
def test_purity_scanner_flags_domain_words(code: str, expected: set[str]) -> None:
    assert banned_words_in(code) == expected


@pytest.mark.parametrize(
    "code",
    [
        "# a teacher comment\nx = 1\n",
        '"""Module docstring about rooms."""\nx = 1\n',
        'def f() -> None:\n    """Assign a room."""\n',
        "grouping_node = 1\n",
        "def __module__(): ...\n",
        "roomy = 1\n",
    ],
)
def test_purity_scanner_ignores_comments_docstrings_and_lookalikes(code: str) -> None:
    assert banned_words_in(code) == set()


def test_purity_scanner_reports_the_offending_file(tmp_path: Path) -> None:
    _write(tmp_path, "core/clean.py", "x = 1\n")
    _write(tmp_path, "solver/dirty.py", "teacher = 1\n")
    assert purity_violations(tmp_path) == ["solver/dirty.py: domain word 'teacher'"]
