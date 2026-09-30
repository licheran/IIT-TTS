"""A workbook for the table-editor performance check (P7.10): L6 plus many extra teachers.

Usage: python tests/scale/editor_workbook.py <out.xlsx> [extra teachers, default 5000]
"""

import sys
from pathlib import Path

from tts.core.model import Resource
from tts.io.fet_html import parse_fet_groups_html, to_dataset
from tts.io.tables import WorkbookData
from tts.io.workbook import export_xlsx
from tts.presets.academic_weekly import types

FET = Path(__file__).parent.parent / "fixtures" / "l6" / "fet-groups-export.html"


def build(extra: int) -> WorkbookData:
    dataset, _ = to_dataset(parse_fet_groups_html(FET))
    teachers = tuple(
        Resource(code=f"EXTRA{n:05d}", type=types.TEACHER, name=f"Extra teacher {n}")
        for n in range(extra)
    )
    return WorkbookData(dataset.model_copy(update={"resources": (*dataset.resources, *teachers)}))


def main() -> None:
    out = Path(sys.argv[1])
    extra = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    export_xlsx(build(extra), out)
    print(f"wrote {out} with {extra} extra teachers")


if __name__ == "__main__":
    main()
