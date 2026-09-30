"""The synthetic institute generator (P10.1) builds a feasible dataset."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scale"))

from generate import SMALL, generate  # noqa: E402

from tts.core.verifier import verify  # noqa: E402
from tts.preflight.checks import has_errors, run_preflight  # noqa: E402


def test_the_small_institute_is_sound_and_its_hidden_timetable_is_valid() -> None:
    made = generate(SMALL, seed=1)
    ds = made.dataset
    assert ds.validate_invariants() == []
    assert verify(ds, made.hidden) == []
    assert not has_errors(run_preflight(ds))
    assert len(made.hidden.assignments) == len(ds.events)


def test_the_generator_is_deterministic() -> None:
    assert generate(SMALL, seed=3).dataset == generate(SMALL, seed=3).dataset


def test_every_level_has_its_events() -> None:
    made = generate(SMALL, seed=1)
    assert set(made.events_by_level) == set(SMALL.levels)
    assert sum(len(v) for v in made.events_by_level.values()) == len(made.dataset.events)
