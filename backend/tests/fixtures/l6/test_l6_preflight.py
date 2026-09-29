"""P5.5: pre-flight on the real L6 dataset is fast (NFR-7) and finds nothing wrong with it."""

import time

from tts.core.model import Dataset
from tts.preflight.checks import run_preflight
from tts.presets import labeller

NFR_7_SECONDS = 1.0  # spec 01 section 5: pre-flight on L6 takes at most 1 s


def test_preflight_on_l6_takes_at_most_one_second(l6_dataset: Dataset) -> None:
    label = labeller("academic_weekly")
    started = time.perf_counter()
    issues = run_preflight(l6_dataset, label)
    elapsed = time.perf_counter() - started
    assert elapsed <= NFR_7_SECONDS, f"took {elapsed:.3f} s"
    assert issues == []  # the original timetable exists, so nothing can be an error


def test_preflight_is_as_fast_on_a_second_run(l6_dataset: Dataset) -> None:
    """Nothing is cached between calls, so the first measurement is not a fluke."""
    timings = []
    for _ in range(3):
        started = time.perf_counter()
        run_preflight(l6_dataset)
        timings.append(time.perf_counter() - started)
    assert max(timings) <= NFR_7_SECONDS, timings
