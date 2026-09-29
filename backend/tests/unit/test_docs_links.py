"""Every relative link in the repository's markdown points at a file that exists (P0.8).

Links to other sites and to an anchor in the same page are not followed.
"""

import re
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[3]
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
REFERENCE = re.compile(r"^\[[^\]]+\]:\s*(?P<target>\S+)", re.MULTILINE)
FENCE = re.compile(r"```.*?```", re.DOTALL)


def markdown_files() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "backend" / "CLAUDE.md"]
    files += [ROOT / "backend" / "README.md"]
    files += [
        ROOT / "web" / "CLAUDE.md",
        ROOT / "backend" / "tests" / "fixtures" / "l6" / "README.md",
    ]
    files += sorted((ROOT / "docs").rglob("*.md"))
    return [f for f in files if f.exists()]


def links_in(path: Path) -> list[str]:
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    targets = [m["target"] for m in LINK.finditer(text)]
    return targets + [m["target"] for m in REFERENCE.finditer(text)]


def is_relative(target: str) -> bool:
    return not re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target, re.IGNORECASE)


def test_markdown_files_were_found() -> None:
    names = {f.name for f in markdown_files()}
    assert {"STATUS.md", "ROADMAP.md", "CLAUDE.md", "README.md"} <= names
    assert len(markdown_files()) >= 20


def test_the_link_finder_understands_the_syntax(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text(
        "See [a](one.md), [b](two.md#part), ![img](pic.png) and [c](https://example.com).\n"
        "```\n[not a link](inside-code.md)\n```\n[ref]: three.md\n",
        encoding="utf-8",
    )
    assert links_in(page) == ["one.md", "two.md#part", "https://example.com", "three.md"]
    assert [t for t in links_in(page) if is_relative(t)] == ["one.md", "two.md#part", "three.md"]
    assert not is_relative("#top") and not is_relative("mailto:a@b.c")


def broken_links(path: Path) -> list[str]:
    """Relative link targets in `path` that do not exist."""
    broken = []
    for target in links_in(path):
        if not is_relative(target):
            continue
        file_part = unquote(target.split("#", 1)[0])
        if file_part and not (path.parent / file_part).resolve().exists():
            broken.append(target)
    return broken


def test_a_link_to_a_missing_file_is_found(tmp_path: Path) -> None:
    (tmp_path / "there.md").write_text("hello", encoding="utf-8")
    page = tmp_path / "page.md"
    page.write_text("[ok](there.md#top) [gone](missing.md) [web](https://x.y/z)", encoding="utf-8")
    assert broken_links(page) == ["missing.md"]


@pytest.mark.parametrize("path", markdown_files(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_relative_links_resolve(path: Path) -> None:
    assert broken_links(path) == [], f"{path.relative_to(ROOT)} links to missing files"
