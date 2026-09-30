"""Write the OpenAPI schema to a file: `python -m tts.api.dump_openapi <path>`."""

import json
import sys
from pathlib import Path

from tts.api.main import create_app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    app = create_app("sqlite://", migrate=False)
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
