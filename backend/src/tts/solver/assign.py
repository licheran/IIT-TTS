"""Default choices for small pools (spec 05 section 7): the pooled requirements that only a few
resources can serve are decided by balancing the load, before the search starts.

On a large dataset the search over *which* of a few resources serves each event is as hard as the
search over times, and the two interact (overlapping pools). A default that spreads the load
evenly, like the default split of a demand's groups, is tried first. If no timetable exists with
it, the solver is free to choose, as before.
"""

from collections import Counter

from tts.core.candidates import Candidates
from tts.core.hierarchy import Hierarchy
from tts.core.model import Dataset, PooledRequirement
from tts.core.selectors import CodeClause, Selector, SelectorError, Selectors, format_selector


def pooled_candidates(dataset: Dataset) -> dict[tuple[str, int], tuple[str, ...]]:
    """The static candidates of every pooled requirement (type, filter and capacity)."""
    hierarchy = Hierarchy(dataset)
    static = Candidates(dataset, hierarchy, Selectors(dataset, hierarchy))
    found = {}
    for q in dataset.pooled:
        try:
            found[(q.event, q.ordinal)] = static.of(q).codes
        except SelectorError:
            found[(q.event, q.ordinal)] = ()
    return found


def preassigned(dataset: Dataset, up_to: int) -> Dataset:
    """`dataset` with each small pooled requirement narrowed to the resources that balance the load.

    A requirement is small when it has at least `count` and at most `up_to` candidates. They are
    taken smallest pool first; each takes the `count` candidates with the fewest periods so far,
    ties by code. The requirement stays (so a result still names its resources), but its filter
    now lists only the chosen ones. A requirement of an event that a pin names resources for is
    left alone.
    """
    candidates = pooled_candidates(dataset)
    durations = {e.code: e.duration for e in dataset.events}
    named = {p.event for p in dataset.pins if p.resources}
    small = [
        q
        for q in dataset.pooled
        if q.event in durations
        and q.event not in named
        and q.count <= len(candidates[(q.event, q.ordinal)]) <= up_to
    ]
    small.sort(key=lambda q: (len(candidates[(q.event, q.ordinal)]), q.event, q.ordinal))
    load: Counter[str] = Counter()
    narrowed: dict[tuple[str, int], PooledRequirement] = {}
    for q in small:
        pool = candidates[(q.event, q.ordinal)]
        picked = sorted(sorted(pool), key=lambda r: load[r])[: q.count]
        for resource in picked:
            load[resource] += durations[q.event]
        narrowed[(q.event, q.ordinal)] = q.model_copy(
            update={"filter": format_selector(Selector((CodeClause(tuple(sorted(picked))),)))}
        )
    if not narrowed:
        return dataset
    return dataset.model_copy(
        update={"pooled": tuple(narrowed.get((q.event, q.ordinal), q) for q in dataset.pooled)}
    )
