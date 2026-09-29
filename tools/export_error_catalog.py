#!/usr/bin/env python3
"""Export the B# error catalog to JSON for non-Python consumers.

The interpreter loads B_Sharp/Errors/error_catalog.py; every other
backend (the D runtime, the compiler, codegen tables) consumes
B_Sharp/Errors/error_catalog.json. This script keeps the two in sync:

    python3 tools/export_error_catalog.py           # rewrite the JSON
    python3 tools/export_error_catalog.py --check   # verify in sync

The test suite (Tests/test_error_catalog_sync.py) enforces --check.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from B_Sharp.Errors.error_catalog import ERROR_CATALOG  # noqa: E402

CATALOG_JSON = ROOT / "B_Sharp" / "Errors" / "error_catalog.json"


def render():
    entries = [
        {
            "code": code,
            "name": entry["name"],
            "message": entry["message"],
            "hint": entry["hint"],
        }
        for code, entry in ERROR_CATALOG.items()
    ]
    return json.dumps({"entries": entries}, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    content = render()
    if "--check" in argv:
        if not CATALOG_JSON.exists():
            print(f"missing {CATALOG_JSON}", file=sys.stderr)
            return 1
        if CATALOG_JSON.read_text(encoding="utf-8") != content:
            print(
                "error_catalog.json is out of date; run "
                "python3 tools/export_error_catalog.py",
                file=sys.stderr,
            )
            return 1
        print(f"error_catalog.json is in sync ({len(ERROR_CATALOG)} entries)")
        return 0

    CATALOG_JSON.write_text(content, encoding="utf-8")
    print(f"wrote {len(ERROR_CATALOG)} entries to {CATALOG_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
