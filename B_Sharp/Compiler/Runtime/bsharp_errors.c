/* (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * The source code of B_Sharp Programming Language is licensed under
 * GPLv3; see LICENSE.md for details.
 *
 * ----------------------------------------------------------------
 * Module: bsharp_errors.c: catalog-backed failure construction and
 * the byte-exact pretty error box (mirror of B_Sharp/Errors/format.py).
 */

#include "bsharp_errors.h"
#include "bsharp_catalog_gen.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ANSI colors - same values as B_Sharp/tokens.py. The interpreter
 * always colors its boxes (even when piped), so we too. */
#define BS_RESET        "\033[0m"
#define BS_BOLD_RED     "\033[1;31m"
#define BS_BOLD_YELLOW  "\033[1;33m"
#define BS_BLUE         "\033[34m"

static char* bs_strdup(const char* s) {
    if (!s) s = "";
    size_t n = strlen(s) + 1;
    char* out = (char*)malloc(n);
    if (!out) exit(1);
    memcpy(out, s, n);
    return out;
}

static bool bs_is_ident_char(char c) {
    return (c >= 'a' && c <= 'z')
        || (c >= 'A' && c <= 'Z')
        || (c >= '0' && c <= '9')
        || c == '_';
}

static const BSharpParam* bs_find_param(
    const char* key,
    size_t key_len,
    const BSharpParam* params,
    size_t param_count
) {
    for (size_t i = 0; i < param_count; i++) {
        if (params[i].key == NULL || params[i].value == NULL) continue;
        if (strlen(params[i].key) == key_len
                && memcmp(params[i].key, key, key_len) == 0) {
            return &params[i];
        }
    }
    return NULL;
}

ReturnStatement bsharp_success(BSharpValue* value) {
    ReturnStatement result;
    result.value = value;
    result.error = NULL;
    return result;
}

char* bsharp_format_details(
    const char* code,
    const BSharpParam* params,
    size_t param_count
) {
    const BSharpErrorInfo* info = bsharp_lookup_error(code);
    const char* tmpl = (info && info->message) ? info->message
                                               : "An error occurred";
    if (!params) param_count = 0;

    /* Pass 1: validate the template shape (mirroring str.format's
     * exceptions, which Error.__init__ swallows into a raw fallback)
     * and make sure every referenced key is supplied. */
    for (const char* p = tmpl; *p; ) {
        if (p[0] == '{' && p[1] == '{') {
            p += 2;
            continue;
        }
        if (p[0] == '}' && p[1] == '}') {
            p += 2;
            continue;
        }
        if (*p == '{') {
            const char* start = p + 1;
            const char* end = start;
            while (*end && *end != '}' && bs_is_ident_char(*end)) end++;
            if (*end != '}' || end == start || (start[0] >= '0' && start[0] <= '9')) {
                /* malformed / empty / numeric placeholder -> fallback */
                return bs_strdup(tmpl);
            }
            if (!bs_find_param(start, (size_t)(end - start), params, param_count)) {
                /* KeyError -> Python falls back to the raw template */
                return bs_strdup(tmpl);
            }
            p = end + 1;
            continue;
        }
        if (*p == '}') {
            /* Single '}' raises ValueError -> raw fallback */
            return bs_strdup(tmpl);
        }
        p++;
    }

    /* Pass 2: size and emit. */
    size_t out_len = 0;
    for (const char* p = tmpl; *p; ) {
        if (p[0] == '{' && p[1] == '{') { out_len += 1; p += 2; continue; }
        if (p[0] == '}' && p[1] == '}') { out_len += 1; p += 2; continue; }
        if (*p == '{') {
            const char* start = p + 1;
            const char* end = start;
            while (*end && *end != '}' && bs_is_ident_char(*end)) end++;
            const BSharpParam* param =
                bs_find_param(start, (size_t)(end - start), params, param_count);
            out_len += strlen(param->value);
            p = end + 1;
            continue;
        }
        out_len++;
        p++;
    }

    char* out = (char*)malloc(out_len + 1);
    if (!out) exit(1);
    char* w = out;
    for (const char* p = tmpl; *p; ) {
        if (p[0] == '{' && p[1] == '{') { *w++ = '{'; p += 2; continue; }
        if (p[0] == '}' && p[1] == '}') { *w++ = '}'; p += 2; continue; }
        if (*p == '{') {
            const char* start = p + 1;
            const char* end = start;
            while (*end && *end != '}' && bs_is_ident_char(*end)) end++;
            const BSharpParam* param =
                bs_find_param(start, (size_t)(end - start), params, param_count);
            size_t vlen = strlen(param->value);
            memcpy(w, param->value, vlen);
            w += vlen;
            p = end + 1;
            continue;
        }
        *w++ = *p++;
    }
    *w = '\0';
    return out;
}

ReturnStatement bsharp_failure(
    const char* code,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end,
    const BSharpParam* params,
    size_t param_count
) {
    BSharp_Error* err = (BSharp_Error*)malloc(sizeof(BSharp_Error));
    if (!err) exit(1);

    err->error_code = code ? code : "RUN001";
    err->details = bsharp_format_details(err->error_code, params, param_count);
    err->pos_start = pos_start;
    err->pos_end = pos_end;

    ReturnStatement result;
    result.value = NULL;
    result.error = err;
    return result;
}

/* Returns the 0-based `line` of `text` as a (ptr, len) pair; missing
 * lines render empty, exactly like Python's guarded split()[index]. */
static void bs_line_at(
    const char* text,
    int line,
    const char** out_ptr,
    size_t* out_len
) {
    if (!text || line < 0) {
        *out_ptr = "";
        *out_len = 0;
        return;
    }
    const char* p = text;
    int current = 0;
    while (current < line) {
        const char* nl = strchr(p, '\n');
        if (!nl) {
            *out_ptr = "";
            *out_len = 0;
            return;
        }
        p = nl + 1;
        current++;
    }
    const char* end = strchr(p, '\n');
    if (!end) end = p + strlen(p);
    *out_ptr = p;
    *out_len = (size_t)(end - p);
}

/* Shared box renderer mirroring B_Sharp/Errors/format.py::format()
 * (errors) and format_warning() (warnings), byte for byte.
 * `is_warning` selects the yellow header variant; `trailing_newline`
 * models Python's print(error) (adds "\n") vs print(warn, end=""). */
static void bs_print_box(
    FILE* stream,
    const char* name,
    const char* code,
    const char* details,
    const char* hint,
    BSharpPosition* pos,
    bool is_warning,
    bool trailing_newline
) {
    if (!pos) {
        fprintf(stream, "%s (%s):\n%s\n", name, code, details);
        return;
    }

    const char* source_line;
    size_t source_len;
    bs_line_at(pos->file_text, pos->line, &source_line, &source_len);

    const char* head_color = is_warning ? BS_BOLD_YELLOW : BS_BOLD_RED;
    const char* head_word = is_warning ? "Warning" : "Error";

    fprintf(stream, "%s%s: %s (%s)" BS_RESET "\n",
            head_color, head_word, name, code);
    fprintf(
        stream,
        "\u256d\u2500 %s: in Line %d: Col %d\n",
        pos->file_name ? pos->file_name : "?",
        pos->line + 1,
        pos->col + 1
    );
    if (is_warning) {
        fprintf(stream, "\u2502  A warning has been raised: \n");
    } else {
        fprintf(
            stream,
            "\u2502  An error has occurred. The following message explains it: \n"
        );
    }
    fprintf(stream, "\u2502\n");
    fprintf(stream, "\u251c\u2500> %.*s\n", (int)source_len, source_line);
    fprintf(stream, "\u2502   %s",
            is_warning ? BS_BOLD_YELLOW : BS_BOLD_RED);
    for (int i = 0; i < pos->col; i++) fputc(' ', stream);
    fputc('^', stream);
    fprintf(stream, BS_RESET "\n");

    /* details lines, each prefixed like '│   ' */
    const char* p = details;
    for (;;) {
        const char* nl = strchr(p, '\n');
        if (!nl) {
            fprintf(stream, "\u2502   %s\n", p);
            break;
        }
        fprintf(stream, "\u2502   %.*s\n", (int)(nl - p), p);
        p = nl + 1;
    }

    fprintf(stream, "\u2502\n");
    fprintf(stream, "\u2570\u2500> " BS_BLUE "HINT" BS_RESET ": %s\n", hint);
    if (trailing_newline) {
        /* Python's print(error) appends one more newline after str(error). */
        fputc('\n', stream);
    }
}

void bsharp_print_error(const BSharp_Error* error) {
    if (!error) return;

    const BSharpErrorInfo* info = bsharp_lookup_error(error->error_code);
    const char* name = (info && info->name) ? info->name : "Unknown Error";
    const char* hint = (info && info->hint)
        ? info->hint
        : "check the code at the indicated position";
    const char* details = error->details ? error->details : "";
    const char* code = error->error_code ? error->error_code : "?";

    bs_print_box(stdout, name, code, details, hint, error->pos_start,
                 false, true);
}

void bsharp_print_warning(
    const char* code,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end,
    const BSharpParam* params,
    size_t param_count
) {
    (void)pos_end;
    const BSharpErrorInfo* info = bsharp_lookup_error(code);
    const char* name = (info && info->name) ? info->name : "Unknown Warning";
    const char* hint = (info && info->hint)
        ? info->hint
        : "check the code at the indicated position";
    char* details = bsharp_format_details(code, params, param_count);

    bs_print_box(stderr, name, code ? code : "?", details, hint, pos_start,
                 true, false);
    free(details);
}
