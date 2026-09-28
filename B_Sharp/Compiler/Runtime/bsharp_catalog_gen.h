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
