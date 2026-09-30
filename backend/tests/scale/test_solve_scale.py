"""NFR-2 and staged solving at institute scale (P10.5). Marked `scale`: run with `pytest -m scale`.

The institute comes from `generate.py` (about 3,000 events, feasible by construction). Every
result is judged by the verifier.
"""

import sys
import time
from pathlib import Path

import pytest

from tts.core.model import Result
from tts.core.run import RunParams
from tts.core.staging import stage
from tts.core.verifier import hard_violations, verify
from tts.solver.decompose import solve_dataset

sys.path.insert(0, str(Path(__file__).parent))
from generate import ScaleParams, generate  # noqa: E402

pytestmark = pytest.mark.scale

NFR2_SECONDS = 15 * 60
PARAMS = RunParams(time_limit_s=NFR2_SECONDS, num_workers=8, seed=0, mode="feasible")


def test_an_institute_of_about_3000_events_is_solved_within_15_minutes_on_8_workers() -> None:
    made = generate()
    assert 2800 <= len(made.dataset.events) <= 3300
    started = time.perf_counter()
    outcome = solve_dataset(made.dataset, PARAMS)
    elapsed = time.perf_counter() - started
    assert outcome.result is not None, outcome.status
    assert hard_violations(verify(made.dataset, outcome.result)) == []
    assert len(outcome.result.assignments) == len(made.dataset.events)
    assert elapsed <= NFR2_SECONDS
    print(f"\nNFR-2: {len(made.dataset.events)} events in {elapsed:.1f} s ({outcome.status})")


def test_solving_level_by_level_from_l4_to_l7_leaves_no_clash_between_stages() -> None:
    params = ScaleParams()
    made = generate(params)
    dataset = made.dataset
    placed: Result | None = None
    started = time.perf_counter()
    for level in params.levels:  # L4 first, L7 last
        for university in params.universities:
            staged = stage(dataset, f'uses:(under:"{university} {level}")', placed)
            outcome = solve_dataset(staged, PARAMS)
            assert outcome.result is not None, (university, level, outcome.status)
            if placed is not None:
                kept = {a.event: a for a in outcome.result.assignments}
                assert all(kept[a.event] == a for a in placed.assignments), "a stage moved"
            placed = outcome.result
    assert placed is not None
    assert len(placed.assignments) == len(dataset.events)
    # The whole institute together: no clash anywhere, so none between stages.
    assert hard_violations(verify(dataset, placed)) == []
    print(
        f"\nStaged L4 to L7: {len(dataset.events)} events in {time.perf_counter() - started:.1f} s"
    )
