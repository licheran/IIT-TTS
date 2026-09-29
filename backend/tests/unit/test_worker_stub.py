from tts.worker.main import run


def test_worker_loop_stops_when_asked() -> None:
    calls = iter([False, False, True])
    run(lambda: next(calls), interval_s=0)
    assert next(calls, None) is None
