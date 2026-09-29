"""Worker entry point: `python -m tts.worker.main`. Runs queued runs until stopped."""

import logging

from tts.store.db import database_url, make_engine, make_session_factory, upgrade
from tts.worker.runner import Worker


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    url = database_url()
    upgrade(url)
    Worker(make_session_factory(make_engine(url))).serve(lambda: False)


if __name__ == "__main__":
    main()
