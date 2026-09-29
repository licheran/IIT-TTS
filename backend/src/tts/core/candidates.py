"""Which resources can ever serve a pooled requirement (spec 05 section 4.1).

`Candidates.of` is the one place that applies the parts of a requirement that depend on the dataset
alone: the resource type, the filter selector (H4) and the capacity rule (H3). The solver narrows
the answer further by availability, and pre-flight uses it as it is, so the two cannot disagree
about what a requirement can use.
"""

from collections import defaultdict
from dataclasses import dataclass

from tts.core.constraints.capacity import required_capacity
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, PooledRequirement
from tts.core.selectors import Selectors


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """The resources a requirement may use, sorted by code, and the capacity it asked for."""

    codes: tuple[str, ...]
    needed: int


class Candidates:
    """Candidate sets of one dataset's pooled requirements. Build once, ask many times."""

    def __init__(
        self,
        dataset: Dataset,
        hierarchy: Hierarchy | None = None,
        selectors: Selectors | None = None,
    ) -> None:
        self._hierarchy = hierarchy if hierarchy is not None else Hierarchy(dataset)
        self._selectors = (
            selectors if selectors is not None else Selectors(dataset, self._hierarchy)
        )
        self._resources = {r.code: r for r in dataset.resources}
        self._by_type: dict[str, list[str]] = defaultdict(list)
        for resource in dataset.resources:  # sorted by code
            self._by_type[resource.type].append(resource.code)
        self._matches: dict[str, frozenset[str]] = {}

    def needed(self, requirement: PooledRequirement) -> int:
        """The capacity the requirement's rule asks for (0 when it has no rule)."""
        resource_type = requirement.capacity_rule.resource_type
        if resource_type is None:
            return 0
        return required_capacity(self._hierarchy, self._resources, requirement.event, resource_type)

    def of(self, requirement: PooledRequirement) -> CandidateSet:
        """The candidates of `requirement`.

        Raises `SelectorError` if its filter is not a valid selector for resources.
        """
        matching = self._matches.get(requirement.filter)
        if matching is None:
            matching = self._selectors.resources(requirement.filter)
            self._matches[requirement.filter] = matching
        needed = self.needed(requirement)
        codes = tuple(
            code
            for code in self._by_type.get(requirement.resource_type, ())
            if code in matching and (self._resources[code].capacity or 0) >= needed
        )
        return CandidateSet(codes=codes, needed=needed)
