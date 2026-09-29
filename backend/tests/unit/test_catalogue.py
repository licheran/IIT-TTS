import re
from pathlib import Path

from tts.core.constraints.catalogue import CATALOGUE
from tts.core.constraints.registry import DECLARED

SPEC = Path(__file__).resolve().parents[3] / "docs" / "spec" / "04-constraints.md"


def spec_types() -> dict[str, str]:
    """Declared type -> scope target, from the table in spec 04 section 2."""
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("## 2. Declared constraints", 1)[1].split(
        "Rules for every declared type", 1
    )[0]
    found = {}
    for line in section.splitlines():
        match = re.match(r"^\| C\d+ \| `(?P<type>[a-z_]+)` \| (?P<scope>resources|events) \|", line)
        if match:
            found[match["type"]] = "resource" if match["scope"] == "resources" else "event"
    return found


def test_the_spec_table_was_found() -> None:
    assert len(spec_types()) == 14


def test_the_catalogue_matches_the_spec_table() -> None:
    assert spec_types() == CATALOGUE


def test_the_catalogue_keeps_the_specs_order() -> None:
    assert list(CATALOGUE) == list(spec_types())


def test_every_registered_declared_type_is_in_the_catalogue() -> None:
    assert set(DECLARED) <= set(CATALOGUE)
