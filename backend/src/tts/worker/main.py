"""Worker entry point. A stub loop until the run queue exists (Phase 6)."""

import logging
import time
from collections.abc import Callable

log = logging.getLogger("tts.worker")


def run(should_stop: Callable[[], bool], interval_s: float = 5.0) -> None:
    """Idle until `should_stop()` returns true, checking once per `interval_s`."""
    log.info("worker started (stub: no queue yet)")
    while not should_stop():
        time.sleep(interval_s)
    log.info("worker stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run(lambda: False)


if __name__ == "__main__":
    main()
