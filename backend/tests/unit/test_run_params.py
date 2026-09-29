import pytest
from pydantic import ValidationError

from tts.core.run import RunParams


def test_defaults_are_those_of_the_spec() -> None:
    p = RunParams()
    assert (p.time_limit_s, p.num_workers, p.seed, p.mode, p.lock_published) == (
        120.0,
        None,
        0,
        "optimise",
        True,
    )


def test_params_are_frozen_and_validated() -> None:
    with pytest.raises(ValidationError):
        RunParams().seed = 1  # type: ignore[misc]
    for bad in ({"time_limit_s": 0}, {"num_workers": 0}, {"mode": "fast"}, {"colour": "red"}):
        with pytest.raises(ValidationError):
            RunParams(**bad)


def test_params_round_trip_through_json() -> None:
    p = RunParams(time_limit_s=30, num_workers=1, seed=7, mode="feasible", lock_published=False)
    assert RunParams.model_validate_json(p.model_dump_json()) == p
