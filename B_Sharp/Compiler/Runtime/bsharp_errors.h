/* (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * The source code of B_Sharp Programming Language is licensed under
 * GPLv3; see LICENSE.md for details.
 *
 * ----------------------------------------------------------------
 * Module: bsharp_errors.h: runtime error values, source positions,
 * catalog-backed failure construction and the pretty error box.
 *
 * The message/name/hint triple for every error code comes from the
 * generated table (bsharp_catalog_gen.c) which mirrors
 * B_Sharp/Errors/error_catalog.py byte-for-byte, so the interpreter
 * and compiled binaries can never disagree about error text.
 */

#ifndef BSHARP_ERRORS_H
#define BSHARP_ERRORS_H

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <stddef.h>
#include <stdbool.h>

typedef struct BSharpValue BSharpValue;

/* A source location. `file_text` is the complete source of the file
 * (compiled programs embed it once as a static string) so the error
 * box can quote the offending line without re-reading anything.
 * `line` and `col` are 0-based, matching the interpreter's Position. */
typedef struct BSharpPosition {
    const char* file_name;
    const char* file_text;
    int line;
    int col;
} BSharpPosition;

typedef struct BSharp_Error {
    const char* error_code;   /* static catalog code, e.g. "RUN011" */
    char* details;            /* message formatted at construction */
    BSharpPosition* pos_start;
    BSharpPosition* pos_end;
} BSharp_Error;

typedef struct ReturnStatement {
    BSharpValue* value;
    BSharp_Error* error;
} ReturnStatement;

/* Catalog message parameters: pre-formatted exactly as Python's
 * str(value) would render them (ints decimal, floats repr-style,
 * strings raw, booleans True/False). */
typedef struct BSharpParam {
    const char* key;
    const char* value;
} BSharpParam;

#define BS_PARAM(key_lit, value_ptr) \
    ((BSharpParam){ .key = (key_lit), .value = (value_ptr) })

/* Successful result carrying `value`. */
ReturnStatement bsharp_success(BSharpValue* value);

/* Failed result for `code`. `code` must be a static string (catalog
 * code or literal). `params`/`param_count` feed {placeholder}
 * substitution in the catalog message; pass NULL, 0 when the message
 * has none. `code`, `params[].key` and `params[].value` pointers must
 * outlive the error (string literals or caller-owned buffers). */
ReturnStatement bsharp_failure(
    const char* code,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end,
    const BSharpParam* params,
    size_t param_count
);

/* Formats a catalog message exactly like Python's Error.__init__:
 * substitutes {key} placeholders ({{ / }} escape literal braces) when
 * every key is supplied, otherwise returns the raw template verbatim.
 * Unknown codes render the default "An error occurred".
 * Caller owns the returned heap string. */
char* bsharp_format_details(
    const char* code,
    const BSharpParam* params,
    size_t param_count
);

/* Renders the full pretty box (same bytes as Python's print(error),
 * ANSI colors included) to stdout, followed by the newline print adds.
 * A NULL position falls back to the one-line name/code/details form. */
void bsharp_print_error(const BSharp_Error* error);

/* Renders the warning box (mirror of format.py::format_warning: yellow
 * header, "A warning has been raised" line, BOLD_YELLOW caret) to
 * stderr. Like Python's print(warn, end="") the box's own trailing
 * newline is the only one - no extra newline is appended.
 * `params` feed {placeholder} substitution (WRN002: base/exponent). */
void bsharp_print_warning(
    const char* code,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end,
    const BSharpParam* params,
    size_t param_count
);

#endif /* BSHARP_ERRORS_H */
