"""Worker entry point: `python -m tts.worker.main`. Runs queued runs until stopped."""

import logging
import time

from tts.store.db import database_url, make_engine, make_session_factory, upgrade
from tts.worker.runner import Worker

log = logging.getLogger("tts.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    url = database_url()
    for attempt in range(1, 6):  # the api migrates at the same time; retry if it wins the race
        try:
            upgrade(url)
            break
        except Exception:
            log.exception("migration attempt %d failed", attempt)
            if attempt == 5:
                raise
            time.sleep(2)
    Worker(make_session_factory(make_engine(url))).serve(lambda: False)


if __name__ == "__main__":
    main()
