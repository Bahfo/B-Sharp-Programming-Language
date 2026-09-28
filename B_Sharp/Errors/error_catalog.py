# Single source of truth for all B-Sharp error/warning codes lives in
# `error_catalog.json` (a machine-readable copy of the category header
# and every entry). This module only loads it, so the interpreter and
# the C runtime (via tools/gen_error_catalog.py codegen) can never
# disagree: both consume the same JSON file.
#
# Error Code Format: [CATEGORY][NUMBER]
# Categories:
#   LEX - Lexer Errors
#   SYN - Syntax Errors (Parser)
#   RUN - Runtime Errors
#   ASN - Assignment Errors
#   MOD - Modification Errors
#   CMP - Comparison Errors
#   IMP - Import Errors
#   MTH - Math Errors
#   SHD - Shadowing Errors
#   WRN - Warnings

import json
import re
from pathlib import Path

_CATALOG_PATH = Path(__file__).with_name("error_catalog.json")
_CODE_RE = re.compile(r"^[A-Z]{3}\d{3}$")
_FIELDS = ("name", "message", "hint")


def _load_catalog():
    """Parse and validate error_catalog.json into the ERROR_CATALOG dict.

    Fails loudly at import time on any malformed file: a missing/corrupt
    catalog must never silently change error output.
    """
    try:
        raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RuntimeError(
            f"error catalog not found: {_CATALOG_PATH} "
            "(it is required for every error/warning message)"
        ) from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"error catalog is not valid JSON: {exc}") from None

    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("error catalog: missing 'entries' array")

    catalog = {}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise RuntimeError(f"error catalog: entry #{i} is not an object")
        code = entry.get("code")
        if not isinstance(code, str) or not _CODE_RE.match(code):
            raise RuntimeError(
                f"error catalog: entry #{i} has invalid code {code!r}"
            )
        if code in catalog:
            raise RuntimeError(f"error catalog: duplicate code {code!r}")
        info = {}
        for field in _FIELDS:
            value = entry.get(field)
            if not isinstance(value, str):
                raise RuntimeError(
                    f"error catalog: {code}: missing/non-string {field!r}"
                )
            info[field] = value
        extra = set(entry) - {"code", *_FIELDS}
        if extra:
            raise RuntimeError(f"error catalog: {code}: unknown fields {extra}")
        catalog[code] = info
    if not catalog:
        raise RuntimeError("error catalog: no entries")
    return catalog


ERROR_CATALOG = _load_catalog()


def get_error_info(error_code):
    """
    Retrieve error information for a given error code.

    Args:
        error_code: The error code (e.g., "SYN001", "RUN100")

    Returns:
        dict with 'name', 'message', and 'hint' keys, or None if not found
    """
    return ERROR_CATALOG.get(error_code)


def format_error_message(error_code, **context):
    """
    Format an error message with the given context.

    Args:
        error_code: The error code (e.g., "SYN001")
        **context: Variables to substitute in the message template

    Returns:
        Formatted error message string, or the raw template if formatting fails
    """
    error_info = ERROR_CATALOG.get(error_code)
    if error_info is None:
        return f"Unknown error code: {error_code}"

    try:
        return error_info["message"].format(**context)
    except (KeyError, IndexError):
        return error_info["message"]
