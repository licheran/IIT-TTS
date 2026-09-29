"""Resource hierarchy and the occupancy rule (spec 02 section 3).

`Hierarchy.occupied_resources` is the only implementation of the occupancy rule. The verifier and
the solver both call it, so they cannot drift apart.

An event occupies, in every slot it covers:
1. each of its fixed resources,
2. each exclusive descendant of each fixed resource, and
3. each pooled resource chosen for it.

It never occupies ancestors.
"""

from collections.abc import Iterable, Mapping

from tts.core.model import Dataset


class Hierarchy:
    """Parent/child index over a dataset's resources. Build once, query many times.

    Queries are safe on a cyclic hierarchy (they never loop), though the answers are only
    meaningful once `detect_cycles` reports nothing.
    """

    def __init__(self, dataset: Dataset) -> None:
        exclusive_types = {t.code for t in dataset.resource_types if t.exclusive}
        self._parent: dict[str, str] = {}
        children: dict[str, list[str]] = {}
        self._exclusive: set[str] = set()
        self._known: set[str] = set()
        for r in dataset.resources:  # sorted by code, so children come out sorted too
            self._known.add(r.code)
            if r.type in exclusive_types:
                self._exclusive.add(r.code)
            if r.parent is not None:
                self._parent[r.code] = r.parent
                children.setdefault(r.parent, []).append(r.code)
        self._children = {code: tuple(kids) for code, kids in children.items()}
        fixed: dict[str, list[str]] = {}
        for f in dataset.fixed:
            fixed.setdefault(f.event, []).append(f.resource)
        self._fixed = {event: tuple(codes) for event, codes in fixed.items()}
        self._exclusive_descendants: dict[str, frozenset[str]] = {}

    def is_exclusive(self, code: str) -> bool:
        return code in self._exclusive

    def parent(self, code: str) -> str | None:
        return self._parent.get(code)

    def children(self, code: str) -> tuple[str, ...]:
        """Direct children, sorted by code."""
        return self._children.get(code, ())

    def ancestors(self, code: str) -> tuple[str, ...]:
        """Parent first, then its parent, and so on."""
        chain: list[str] = []
        seen = {code}
        current = self._parent.get(code)
        while current is not None and current not in seen:
            chain.append(current)
            seen.add(current)
            current = self._parent.get(current)
        return tuple(chain)

    def descendants(self, code: str) -> frozenset[str]:
        """Every resource below `code`, at any depth, excluding `code` itself."""
        found: set[str] = set()
        stack = list(self.children(code))
        while stack:
            current = stack.pop()
            if current in found or current == code:
                continue
            found.add(current)
            stack.extend(self.children(current))
        return frozenset(found)

    def exclusive_descendants(self, code: str) -> frozenset[str]:
        """Exclusive resources below `code`, at any depth, even through non-exclusive nodes."""
        cached = self._exclusive_descendants.get(code)
        if cached is None:
            cached = frozenset(d for d in self.descendants(code) if d in self._exclusive)
            self._exclusive_descendants[code] = cached
        return cached

    def fixed_resources(self, event: str) -> tuple[str, ...]:
        """The event's fixed resources, in dataset order."""
        return self._fixed.get(event, ())

    def occupied_resources(self, event: str, chosen: Iterable[str] = ()) -> frozenset[str]:
        """Everything the event occupies given its chosen pooled resources.

        Includes non-exclusive fixed resources (a clash is only possible on exclusive ones, see
        `occupied_exclusive`).
        """
        occupied: set[str] = set(chosen)
        for code in self.fixed_resources(event):
            occupied.add(code)
            occupied |= self.exclusive_descendants(code)
        return frozenset(occupied)

    def occupied_exclusive(self, event: str, chosen: Iterable[str] = ()) -> frozenset[str]:
        """The occupied resources that can clash: the exclusive ones."""
        return frozenset(c for c in self.occupied_resources(event, chosen) if c in self._exclusive)


def detect_cycles(dataset: Dataset) -> list[tuple[str, ...]]:
    """Every parent cycle among a dataset's resources. See `find_cycles`."""
    return find_cycles({r.code: r.parent for r in dataset.resources if r.parent is not None})


def find_cycles(parent: Mapping[str, str]) -> list[tuple[str, ...]]:
    """Every cycle in a child-to-parent map, each reported once as codes in walk order.

    A cycle starts at its smallest code. A node that only leads into a cycle is not part of it.
    Parents that are not keys of the map are ignored (an unresolved reference is reported
    separately).
    """
    state: dict[str, int] = {}  # 1 = on the current walk, 2 = finished
    cycles: list[tuple[str, ...]] = []
    for start in sorted(parent):
        if start in state:
            continue
        walk: list[str] = []
        node: str | None = start
        while node is not None and node not in state:
            state[node] = 1
            walk.append(node)
            node = parent.get(node)
        if node is not None and state.get(node) == 1:
            cycle = walk[walk.index(node) :]
            pivot = cycle.index(min(cycle))
            cycles.append(tuple(cycle[pivot:] + cycle[:pivot]))
        for visited in walk:
            state[visited] = 2
    return sorted(cycles)
