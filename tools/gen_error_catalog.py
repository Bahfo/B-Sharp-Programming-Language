#!/usr/bin/env python3
"""Generates the C error-catalog table from B_Sharp/Errors/error_catalog.json.

The JSON file is the single source of truth: the interpreter loads it
directly (B_Sharp/Errors/error_catalog.py) and this tool compiles it into
the C runtime table, so any change there must be regenerated into the
runtime (Tests/test_error_catalog_sync.py enforces byte-equality so drift
is impossible).

    python3 tools/gen_error_catalog.py           # (re)write the generated files
    python3 tools/gen_error_catalog.py --check   # verify no drift (exit 1 on drift)
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The loader reads B_Sharp/Errors/error_catalog.json (the source of truth)
# and validates it; importing it here keeps one validation path for both
# the interpreter and the generated C table.
from B_Sharp.Errors.error_catalog import ERROR_CATALOG  # noqa: E402

OUT_DIR = ROOT / "B_Sharp" / "Compiler" / "Runtime"
HEADER_PATH = OUT_DIR / "bsharp_catalog_gen.h"
SOURCE_PATH = OUT_DIR / "bsharp_catalog_gen.c"

CODE_RE = re.compile(r"^[A-Z]{3}\d{3}$")
# Python str.format is only ever used with plain {identifier} placeholders
# and {{ / }} literal-brace escapes in this catalog; format specs, numeric
# indices or conversions would silently diverge from the C formatter, so
# reject them at generation time.
PLACEHOLDER_RE = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


def validate():
    problems = []
    for code, info in sorted(ERROR_CATALOG.items()):
        if not CODE_RE.match(code):
            problems.append(f"{code!r}: code does not match AAA999")
            continue
        for field in ("name", "message", "hint"):
            if not isinstance(info.get(field), str):
                problems.append(f"{code!r}: missing/non-string {field!r}")
        message = info.get("message", "")
        stripped = PLACEHOLDER_RE.sub("", message)
        stripped = stripped.replace("{{", "").replace("}}", "")
        if "{" in stripped or "}" in stripped:
            problems.append(
                f"{code!r}: message contains a non-simple placeholder: {message!r}"
            )
    if problems:
        raise SystemExit("catalog validation failed:\n  " + "\n  ".join(problems))


def c_string(value):
    out = ['"']
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def render_header():
    return """\
/* GENERATED FILE - DO NOT EDIT.
 * Produced by tools/gen_error_catalog.py from B_Sharp/Errors/error_catalog.json.
 * Run `python3 tools/gen_error_catalog.py` after editing the catalog, or
 * Tests/test_error_catalog_sync.py will fail.
 */
#ifndef BSHARP_CATALOG_GEN_H
#define BSHARP_CATALOG_GEN_H

#include <stddef.h>

typedef struct {
    const char* code;
    const char* name;
    const char* message;
    const char* hint;
} BSharpErrorInfo;

extern const BSharpErrorInfo bsharp_error_catalog[];
extern const size_t bsharp_error_catalog_count;

/* Binary-searches the catalog; returns NULL for unknown codes. */
const BSharpErrorInfo* bsharp_lookup_error(const char* code);

#endif /* BSHARP_CATALOG_GEN_H */
"""


def render_source():
    entries = sorted(ERROR_CATALOG.items())
    lines = [
        "/* GENERATED FILE - DO NOT EDIT.",
        " * Produced by tools/gen_error_catalog.py from B_Sharp/Errors/error_catalog.json.",
        " */",
        "",
        '#include "bsharp_catalog_gen.h"',
        "",
        "#include <string.h>",
        "",
        "const BSharpErrorInfo bsharp_error_catalog[] = {",
    ]
    for code, info in entries:
        lines.append("    {")
        lines.append(f"        {c_string(code)},")
        lines.append(f"        {c_string(info['name'])},")
        lines.append(f"        {c_string(info['message'])},")
        lines.append(f"        {c_string(info['hint'])},")
        lines.append("    },")
    lines.append("};")
    lines.append("")
    lines.append(
        "const size_t bsharp_error_catalog_count = "
        "sizeof(bsharp_error_catalog) / sizeof(bsharp_error_catalog[0]);"
    )
    lines.append("")
    lines.append(
        "const BSharpErrorInfo* bsharp_lookup_error(const char* code) {"
    )
    lines.append("    if (!code) return NULL;")
    lines.append("    size_t lo = 0;")
    lines.append("    size_t hi = bsharp_error_catalog_count;")
    lines.append("    while (lo < hi) {")
    lines.append("        size_t mid = lo + (hi - lo) / 2;")
    lines.append("        int cmp = strcmp(code, bsharp_error_catalog[mid].code);")
    lines.append("        if (cmp == 0) return &bsharp_error_catalog[mid];")
    lines.append("        if (cmp > 0) lo = mid + 1;")
    lines.append("        else hi = mid;")
    lines.append("    }")
    lines.append("    return NULL;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify generated files match the catalog (exit 1 on drift)",
    )
    args = parser.parse_args(argv)

    validate()
    header = render_header()
    source = render_source()

    if args.check:
        drift = []
        for path, expected in ((HEADER_PATH, header), (SOURCE_PATH, source)):
            if not path.exists():
                drift.append(f"missing: {path}")
            elif path.read_text(encoding="utf-8") != expected:
                drift.append(f"stale: {path}")
        if drift:
            print(
                "ERROR CATALOG DRIFT - run `python3 tools/gen_error_catalog.py`",
                file=sys.stderr,
            )
            for item in drift:
                print(f"  {item}", file=sys.stderr)
            return 1
        print("generated catalog matches error_catalog.json")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HEADER_PATH.write_text(header, encoding="utf-8")
    SOURCE_PATH.write_text(source, encoding="utf-8")
    print(f"wrote {HEADER_PATH.relative_to(ROOT)}")
    print(f"wrote {SOURCE_PATH.relative_to(ROOT)}")
    print(f"{len(ERROR_CATALOG)} error codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
