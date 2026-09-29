"""Selector language: parser, printer and evaluator (spec 02 section 5).

A selector is `all` or clauses joined by `;` (AND). Clause names and what they select:

| clause                 | selects   |
|------------------------|-----------|
| `type:T`               | resources |
| `under:C`              | resources |
| `attr:NAME<op>VALUE`   | resources |
| `kind:K1,K2`           | events    |
| `ref:C`                | events    |
| `uses:(SELECTOR)`      | events    |
| `code:C1,C2`           | both      |
| `tag:K=V`, `tag:K!=V`  | both      |

Unquoted values are trimmed and may not contain `;` or `,`. Quote a value with double quotes to
include them. Inside quotes `\\"` is a quote and `\\\\` is a backslash. `uses:(...)` holds a
resource selector in parentheses, so an unquoted value inside it may not contain parentheses.
"""

import operator
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset

Target = Literal["resource", "event"]
Op = Literal["=", "!=", "<", "<=", ">", ">="]

_NAMES = frozenset({"type", "code", "under", "tag", "attr", "kind", "ref", "uses"})
_NAME = re.compile(r"[A-Za-z_]+")
_OPS: tuple[Op, ...] = ("!=", "<=", ">=", "=", "<", ">")


class SelectorError(ValueError):
    """Invalid selector text. `position` is a character offset into the original string."""

    def __init__(self, position: int, message: str) -> None:
        super().__init__(f"{message} (at {position})")
        self.position = position
        self.message = message


# --- Syntax tree --------------------------------------------------------------------------------
# `position` is excluded from equality so a re-parsed printout equals the original tree.


@dataclass(frozen=True, slots=True)
class TypeClause:
    value: str
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class CodeClause:
    codes: tuple[str, ...]
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class UnderClause:
    code: str
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class TagClause:
    key: str
    value: str
    negate: bool = False
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class AttrClause:
    name: str
    op: Op
    value: str
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class KindClause:
    kinds: tuple[str, ...]
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class RefClause:
    code: str
    position: int = field(default=0, compare=False, kw_only=True)


@dataclass(frozen=True, slots=True)
class UsesClause:
    inner: "Selector"
    position: int = field(default=0, compare=False, kw_only=True)


Clause = (
    TypeClause
    | CodeClause
    | UnderClause
    | TagClause
    | AttrClause
    | KindClause
    | RefClause
    | UsesClause
)


@dataclass(frozen=True, slots=True)
class Selector:
    """No clauses means `all`."""

    clauses: tuple[Clause, ...] = ()

    @property
    def is_all(self) -> bool:
        return not self.clauses


ALL = Selector()

_APPLIES: dict[type, frozenset[Target]] = {
    TypeClause: frozenset({"resource"}),
    UnderClause: frozenset({"resource"}),
    AttrClause: frozenset({"resource"}),
    KindClause: frozenset({"event"}),
    RefClause: frozenset({"event"}),
    UsesClause: frozenset({"event"}),
    CodeClause: frozenset({"resource", "event"}),
    TagClause: frozenset({"resource", "event"}),
}
_CLAUSE_NAME: dict[type, str] = {
    TypeClause: "type",
    UnderClause: "under",
    AttrClause: "attr",
    KindClause: "kind",
    RefClause: "ref",
    UsesClause: "uses",
    CodeClause: "code",
    TagClause: "tag",
}


# --- Parser -------------------------------------------------------------------------------------


class _Parser:
    def __init__(self, text: str, offset: int = 0) -> None:
        self.s = text
        self.i = 0
        self.offset = offset

    def fail(self, position: int, message: str) -> SelectorError:
        return SelectorError(self.offset + position, message)

    def skip_ws(self) -> None:
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def at_end(self) -> bool:
        return self.i >= len(self.s)

    def parse(self) -> Selector:
        if not self.s.strip():
            raise self.fail(0, "empty selector")
        if self.s.strip() == "all":
            return ALL
        clauses: list[Clause] = []
        while True:
            self.skip_ws()
            clauses.append(self.clause())
            self.skip_ws()
            if self.at_end():
                return Selector(tuple(clauses))
            if self.s[self.i] != ";":
                raise self.fail(self.i, f'expected ";" but found "{self.s[self.i]}"')
            self.i += 1

    def clause(self) -> Clause:
        start = self.i
        if self.at_end():
            raise self.fail(start, "expected a clause")
        match = _NAME.match(self.s, self.i)
        colon = match.end() if match else start
        while colon < len(self.s) and self.s[colon].isspace():
            colon += 1  # tolerate "name : value"
        if match is None or colon >= len(self.s) or self.s[colon] != ":":
            raise self.fail(start, f'expected "name:value" but found "{self.s[start:].strip()}"')
        name = match[0]
        if name not in _NAMES:
            raise self.fail(start, f'unknown clause "{name}:"')
        self.i = colon + 1
        self.skip_ws()
        if name == "uses":
            return self.uses(start)
        if name == "type":
            return TypeClause(self.single(name), position=self.offset + start)
        if name == "under":
            return UnderClause(self.single(name), position=self.offset + start)
        if name == "ref":
            return RefClause(self.single(name), position=self.offset + start)
        if name == "code":
            return CodeClause(self.items(name), position=self.offset + start)
        if name == "kind":
            return KindClause(self.items(name), position=self.offset + start)
        if name == "tag":
            return self.tag(start)
        return self.attr(start)

    def uses(self, start: int) -> UsesClause:
        if self.at_end() or self.s[self.i] != "(":
            raise self.fail(self.i, 'uses: expects a selector in parentheses, "uses:(...)"')
        open_at = self.i
        depth = 0
        j = open_at
        while j < len(self.s):
            c = self.s[j]
            if c == '"':
                j = self.quoted_end(j)
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        else:
            raise self.fail(open_at, 'unclosed "(" in uses:')
        inner = _Parser(self.s[open_at + 1 : j], self.offset + open_at + 1).parse()
        self.i = j + 1
        return UsesClause(inner, position=self.offset + start)

    def quoted_end(self, open_at: int) -> int:
        """Index of the closing quote for the quote at `open_at`."""
        j = open_at + 1
        while j < len(self.s):
            if self.s[j] == "\\":
                j += 2
                continue
            if self.s[j] == '"':
                return j
            j += 1
        raise self.fail(open_at, "unterminated quoted value")

    def value(self, stops: str, what: str) -> str:
        """One quoted or raw value, ending before a char in `stops` or at the end."""
        self.skip_ws()
        start = self.i
        if not self.at_end() and self.s[self.i] == '"':
            end = self.quoted_end(self.i)
            text = re.sub(r"\\(.)", r"\1", self.s[self.i + 1 : end], flags=re.DOTALL)
            self.i = end + 1
            self.skip_ws()
            if not self.at_end() and self.s[self.i] not in stops:
                raise self.fail(self.i, "unexpected text after a quoted value")
        else:
            j = start
            while j < len(self.s) and self.s[j] not in stops:
                if self.s[j] == '"':
                    raise self.fail(j, 'unexpected quote, quote the whole value with "..."')
                j += 1
            text = self.s[start:j].strip()
            self.i = j
        if not text:
            raise self.fail(start, f"{what} needs a value")
        return text

    def single(self, name: str) -> str:
        return self.single_value(f"{name}:")

    def items(self, name: str) -> tuple[str, ...]:
        found = [self.value(",;", f"{name}:")]
        while not self.at_end() and self.s[self.i] == ",":
            self.i += 1
            found.append(self.value(",;", f"{name}:"))
        return tuple(found)

    def name_and_op(
        self, start: int, name_stops: str, ops: tuple[Op, ...], what: str
    ) -> tuple[str, Op]:
        self.skip_ws()
        begin = self.i
        if not self.at_end() and self.s[self.i] == '"':
            end = self.quoted_end(self.i)
            name = re.sub(r"\\(.)", r"\1", self.s[self.i + 1 : end], flags=re.DOTALL)
            self.i = end + 1
            self.skip_ws()
        else:
            j = begin
            while j < len(self.s) and self.s[j] not in name_stops + ";":
                j += 1
            name = self.s[begin:j].strip()
            self.i = j
        for op in ops:
            if self.s.startswith(op, self.i):
                if not name:
                    raise self.fail(begin, f"{what} needs a name")
                self.i += len(op)
                return name, op
        raise self.fail(self.i if not self.at_end() else start, f"{what} needs an operator")

    def tag(self, start: int) -> TagClause:
        key, op = self.name_and_op(start, "=!", ("!=", "="), "tag:")
        return TagClause(
            key, self.single_value("tag:"), negate=op == "!=", position=self.offset + start
        )

    def attr(self, start: int) -> AttrClause:
        name, op = self.name_and_op(start, "=!<>", _OPS, "attr:")
        return AttrClause(name, op, self.single_value("attr:"), position=self.offset + start)

    def single_value(self, what: str) -> str:
        self.skip_ws()
        start = self.i
        quoted = not self.at_end() and self.s[self.i] == '"'
        text = self.value(";", what)
        if "," in text and not quoted:
            raise self.fail(start, 'a value containing "," must be quoted')
        return text


def parse(text: str) -> Selector:
    """Parse selector text. Raises `SelectorError` with a character position."""
    return _Parser(text).parse()


# --- Printer ------------------------------------------------------------------------------------

_NEEDS_QUOTES = set(';,"\\()')
_NAME_NEEDS_QUOTES = _NEEDS_QUOTES | set("=!<>:")


def _quote(value: str, special: set[str]) -> str:
    if value != value.strip() or value.startswith("=") or any(c in special for c in value):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def format_selector(selector: Selector) -> str:
    """Canonical text for a selector. `parse(format_selector(s)) == s` for every tree."""
    if selector.is_all:
        return "all"
    return ";".join(_format_clause(c) for c in selector.clauses)


def _format_clause(clause: Clause) -> str:
    q = _quote
    match clause:
        case TypeClause(value):
            return f"type:{q(value, _NEEDS_QUOTES)}"
        case UnderClause(code):
            return f"under:{q(code, _NEEDS_QUOTES)}"
        case RefClause(code):
            return f"ref:{q(code, _NEEDS_QUOTES)}"
        case CodeClause(codes):
            return "code:" + ",".join(q(c, _NEEDS_QUOTES) for c in codes)
        case KindClause(kinds):
            return "kind:" + ",".join(q(k, _NEEDS_QUOTES) for k in kinds)
        case TagClause(key, value, negate):
            op = "!=" if negate else "="
            return f"tag:{q(key, _NAME_NEEDS_QUOTES)}{op}{q(value, _NEEDS_QUOTES)}"
        case AttrClause(name, op, value):
            return f"attr:{q(name, _NAME_NEEDS_QUOTES)}{op}{q(value, _NEEDS_QUOTES)}"
        case UsesClause(inner):
            return f"uses:({format_selector(inner)})"
    raise AssertionError(f"unhandled clause {clause!r}")


# --- Evaluation ---------------------------------------------------------------------------------


def _as_selector(selector: Selector | str) -> Selector:
    return parse(selector) if isinstance(selector, str) else selector


def check_target(selector: Selector | str, target: Target) -> None:
    """Raise `SelectorError` if a clause does not apply to `target` (resources or events)."""
    for clause in _as_selector(selector).clauses:
        if target not in _APPLIES[type(clause)]:
            noun = "resources" if target == "resource" else "events"
            raise SelectorError(
                clause.position, f'clause "{_CLAUSE_NAME[type(clause)]}:" does not select {noun}'
            )
        if isinstance(clause, UsesClause):
            check_target(clause.inner, "resource")


class Selectors:
    """Evaluates selectors against one dataset. Build once, evaluate many times."""

    def __init__(self, dataset: Dataset, hierarchy: Hierarchy | None = None) -> None:
        self._ds = dataset
        self._hierarchy = hierarchy if hierarchy is not None else Hierarchy(dataset)

    def resources(self, selector: Selector | str) -> frozenset[str]:
        """Codes of the resources the selector matches."""
        sel = _as_selector(selector)
        check_target(sel, "resource")
        matched = frozenset(r.code for r in self._ds.resources)
        for clause in sel.clauses:
            matched &= self._resource_clause(clause)
        return matched

    def events(self, selector: Selector | str) -> frozenset[str]:
        """Codes of the events the selector matches."""
        sel = _as_selector(selector)
        check_target(sel, "event")
        matched = frozenset(e.code for e in self._ds.events)
        for clause in sel.clauses:
            matched &= self._event_clause(clause)
        return matched

    def _resource_clause(self, clause: Clause) -> frozenset[str]:
        resources = self._ds.resources
        match clause:
            case TypeClause(value):
                return frozenset(r.code for r in resources if r.type == value)
            case CodeClause(codes):
                return frozenset(r.code for r in resources if r.code in codes)
            case UnderClause(code):
                return self._hierarchy.exclusive_descendants(code)
            case TagClause(key, value, negate):
                return frozenset(
                    r.code for r in resources if _tag_matches(r.tag(key), value, negate)
                )
            case AttrClause():
                compare = _attribute_test(clause)
                found: set[str] = set()
                for r in resources:
                    stored = r.capacity if clause.name == "capacity" else r.attribute(clause.name)
                    if stored is not None and compare(stored):
                        found.add(r.code)
                return frozenset(found)
        raise AssertionError(f"clause {clause!r} does not select resources")

    def _event_clause(self, clause: Clause) -> frozenset[str]:
        events = self._ds.events
        match clause:
            case CodeClause(codes):
                return frozenset(e.code for e in events if e.code in codes)
            case TagClause(key, value, negate):
                return frozenset(
                    e.code for e in events if _tag_matches(dict(e.tags).get(key), value, negate)
                )
            case KindClause(kinds):
                return frozenset(e.code for e in events if e.kind in kinds)
            case RefClause(code):
                return frozenset(e.code for e in events if e.reference == code)
            case UsesClause(inner):
                # An event uses a resource when the resource is one of its fixed resources.
                used = self.resources(inner)
                return frozenset(
                    e.code
                    for e in events
                    if any(r in used for r in self._hierarchy.fixed_resources(e.code))
                )
        raise AssertionError(f"clause {clause!r} does not select events")


def _tag_matches(stored: str | None, value: str, negate: bool) -> bool:
    # A missing tag is "not equal" to any value.
    return (stored != value) if negate else (stored == value)


def _attribute_test(clause: AttrClause) -> Callable[[str | int | bool], bool]:
    """A predicate over a stored attribute value, converting the clause value to its type."""

    def compare(stored: str | int | bool) -> bool:
        wanted: str | int | bool
        if isinstance(stored, bool):
            lowered = clause.value.lower()
            if lowered not in ("true", "false"):
                raise SelectorError(
                    clause.position,
                    f'attribute "{clause.name}" is true or false, got "{clause.value}"',
                )
            wanted = lowered == "true"
        elif isinstance(stored, int):
            try:
                wanted = int(clause.value)
            except ValueError:
                raise SelectorError(
                    clause.position, f'attribute "{clause.name}" is a number, got "{clause.value}"'
                ) from None
        else:
            wanted = clause.value
        # `wanted` was converted to the type of `stored`, so the comparison is well-typed.
        return bool(_COMPARE[clause.op](stored, wanted))

    return compare


_COMPARE: dict[Op, Callable[[Any, Any], Any]] = {
    "=": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def select_resources(dataset: Dataset, selector: Selector | str) -> frozenset[str]:
    """Convenience wrapper. Build a `Selectors` once when evaluating many selectors."""
    return Selectors(dataset).resources(selector)


def select_events(dataset: Dataset, selector: Selector | str) -> frozenset[str]:
    """Convenience wrapper. Build a `Selectors` once when evaluating many selectors."""
    return Selectors(dataset).events(selector)
