"""The user wiki in `docs/wiki/` must not drift from the code (Phases 13 to 17)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WIKI = ROOT / "docs" / "wiki"
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"```.*?```", re.DOTALL)


def pages() -> list[Path]:
    return sorted(WIKI.rglob("*.md"))


def test_the_wiki_has_a_home_page_and_pages() -> None:
    assert (WIKI / "README.md").is_file()
    assert len(pages()) >= 3


def test_every_relative_link_and_image_in_the_wiki_resolves() -> None:
    broken = []
    for page in pages():
        text = FENCE.sub("", page.read_text("utf-8"))
        for target in LINK.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if not (page.parent / path).resolve().exists():
                broken.append(f"{page.relative_to(ROOT)} -> {target}")
    assert broken == []


def test_every_anchor_link_points_at_a_heading_of_its_page() -> None:
    def slug(heading: str) -> str:
        words = re.sub(r"[^\w\s-]", "", heading.strip().lower())
        return re.sub(r"\s+", "-", words)

    broken = []
    for page in pages():
        text = FENCE.sub("", page.read_text("utf-8"))
        for target in LINK.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            path, _, fragment = target.partition("#")
            if not fragment:
                continue
            destination = page if not path else (page.parent / path).resolve()
            if destination.suffix != ".md" or not destination.exists():
                continue
            headings = {
                slug(h)
                for h in re.findall(
                    r"^#{1,6}\s+(.+)$", FENCE.sub("", destination.read_text("utf-8")), re.M
                )
            }
            if fragment not in headings:
                broken.append(f"{page.relative_to(ROOT)} -> {target}")
    assert broken == []


def test_every_wiki_page_is_reachable_from_the_home_page() -> None:
    reached, todo = set(), [WIKI / "README.md"]
    while todo:
        page = todo.pop()
        if page in reached:
            continue
        reached.add(page)
        for target in LINK.findall(FENCE.sub("", page.read_text("utf-8"))):
            path = target.split("#", 1)[0]
            if path.endswith(".md") and not re.match(r"^[a-z][a-z0-9+.-]*:", path):
                todo.append((page.parent / path).resolve())
    assert [str(p.relative_to(ROOT)) for p in pages() if p.resolve() not in reached] == []


def test_every_tab_of_the_web_app_has_a_wiki_page() -> None:
    routes = (ROOT / "web" / "src" / "routes.tsx").read_text("utf-8")
    block = routes[routes.index("const TABS = [") : routes.index("] as const")]
    tabs = dict(re.findall(r"\['([a-z]+)', '([^']+)'\]", block))
    assert len(tabs) == 6
    names = {
        "tables": "tables.md",
        "io": "import-export.md",
        "preflight": "preflight.md",
        "run": "run.md",
        "results": "timetable.md",
        "runs": "runs.md",
    }
    assert set(tabs) == set(names)
    for path, label in tabs.items():
        page = WIKI / "tabs" / names[path]
        assert page.is_file(), f"no wiki page for the {label} tab"
        assert f"{label}" in page.read_text("utf-8")
    assert (WIKI / "tabs" / "datasets.md").is_file()
    assert (WIKI / "tabs" / "templates-expand.md").is_file()


def test_every_tab_page_has_the_standard_sections_and_a_picture() -> None:
    for page in sorted((WIKI / "tabs").glob("*.md")):
        text = page.read_text("utf-8")
        headings = re.findall(r"^## (.+)$", text, re.M)
        assert headings[0] == "What it's for", page.name
        assert "How to use it" in headings and headings[-1] == "Related", page.name
        assert "Example" in headings, page.name
        assert "](../img/" in text, f"{page.name} has no picture"
