/* (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * The source code of B_Sharp Programming Language is licensed under
 * GPLv3; see LICENSE.md for details.
 *
 * ----------------------------------------------------------------
 * Module: bsharp_number.h: the B# `Number` datatype.
 *
 * Numbers are unbounded exact integers with an int64 fast path and an
 * IEEE double mode, mirroring the interpreter's Python int/float mix:
 *
 *   - INT64  small exact integers (canonical; everything that fits
 *            stays here, so the common case never touches the heap)
 *   - BIG    heap bignums, sign-magnitude little-endian base 2^32
 *            (demotes back to INT64 whenever the value fits)
 *   - FLOAT  IEEE-754 doubles (any mixed int/float op promotes to
 *            this; int->float overflow is reported, never silent)
 *
 * Exact `+ - * / %` on integers, C-truncating `//` and `%` with the
 * dividend's sign, and the interpreter's exact `^` with its 16384-bit
 * guard (see bs_num_pow).
 *
 * Statuses map onto catalog errors at the call site:
 *   BS_NUM_OVERFLOW -> MTH001 "Result too large to represent"
 *   BS_NUM_COMPLEX   -> RUN106 "Complex numbers are not yet supported"
 *   BS_NUM_APPROX    -> WRN002 warning + float result (bs_num_pow only)
 */

#ifndef BSHARP_NUMBER_H
#define BSHARP_NUMBER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct BSharpBignum {
    int sign;             /* -1, 0 or +1 (0 iff len == 0) */
    size_t len;           /* limbs in use (normalized, no leading zeros) */
    uint32_t* limbs;      /* little-endian base 2^32 magnitude */
} BSharpBignum;

typedef enum {
    BS_NUM_INT64,
    BS_NUM_BIG,
    BS_NUM_FLOAT
} BSharpNumberKind;

typedef struct BSharpNumber {
    BSharpNumberKind kind;
    union {
        int64_t i;
        double d;
        BSharpBignum* big;
    } as;
} BSharpNumber;

typedef enum {
    BS_NUM_OK = 0,
    BS_NUM_OVERFLOW,
    BS_NUM_COMPLEX,
    BS_NUM_APPROX
} BSharpNumberStatus;

/* Python's sys.get_int_max_str_digits() default: str(int) refuses
 * integers longer than this many decimal digits. */
#define BS_INT_MAX_STR_DIGITS 4300

/* Above this many estimated result bits, exact integer `^` is refused
 * (mirrors Number.MAX_POWER_RESULT_BITS in the interpreter). */
#define BS_MAX_POWER_RESULT_BITS 16384

/* ---- constructors / inspection ---- */
BSharpNumber bs_num_i64(int64_t value);
BSharpNumber bs_num_f64(double value);
BSharpNumber bs_num_zero(void);
/* Parses a decimal integer literal; returns false on garbage. */
BSharpNumber bs_num_from_dec(const char* text, bool* ok);

bool bs_num_is_int(BSharpNumber n);      /* INT64 or BIG */
bool bs_num_is_int64(BSharpNumber n);    /* fits the fast path */
bool bs_num_is_float(BSharpNumber n);

/* ---- exact helpers ---- */
/* Bit length of |n| (0 for zero) - matches Python's int.bit_length(). */
size_t bs_num_bit_length(BSharpNumber n);
/* int64 fast-path value; ok=false when the value is a BIG. */
int64_t bs_num_to_i64(BSharpNumber n, bool* ok);
/* Rounds the value to double. Returns BS_NUM_OVERFLOW (Python's
 * OverflowError -> MTH001) when the exact value cannot be represented. */
BSharpNumberStatus bs_num_to_f64(BSharpNumber n, double* out);
BSharpNumber bs_num_neg(BSharpNumber n);

/* ---- arithmetic (mixed int/float follows Python promotion) ---- */
BSharpNumberStatus bs_num_add(BSharpNumber a, BSharpNumber b, BSharpNumber* out);
BSharpNumberStatus bs_num_sub(BSharpNumber a, BSharpNumber b, BSharpNumber* out);
BSharpNumberStatus bs_num_mul(BSharpNumber a, BSharpNumber b, BSharpNumber* out);
/* True division: always yields a float. Callers pre-check div-by-zero
 * (RUN100) exactly like the interpreter does. */
BSharpNumberStatus bs_num_true_div(
    BSharpNumber a, BSharpNumber b, BSharpNumber* out);
/* `%` in B# source: C-style truncated integer division (RUN100/101
 * checked by the caller). */
BSharpNumberStatus bs_num_idiv(
    BSharpNumber a, BSharpNumber b, BSharpNumber* out);
/* `~` in B# source: C-style remainder, sign of the dividend
 * (RUN103/104 checked by the caller). */
BSharpNumberStatus bs_num_mod(BSharpNumber a, BSharpNumber b, BSharpNumber* out);
/* `^` with the interpreter's guard: exact while estimated result bits
 * fit BS_MAX_POWER_RESULT_BITS, float approximation (BS_NUM_APPROX +
 * caller-emitted WRN002) past it for negative exponents, MTH001 past it
 * for positive ones. Callers pre-check 0^-n (RUN105). */
BSharpNumberStatus bs_num_pow(BSharpNumber a, BSharpNumber b, BSharpNumber* out);

/* ---- equality / ordering ---- */
bool bs_num_eq(BSharpNumber a, BSharpNumber b);
/* Three-way for exact integers; callers must check bs_num_is_int. */
int bs_num_cmp(BSharpNumber a, BSharpNumber b);
/* Interpreter's _order_key: huge exact ints collapse to +/-inf and
 * NaN stays NaN (all comparisons against NaN are false at the caller). */
bool bs_num_order_key(BSharpNumber n, double* out);

/* ---- formatting ---- */
/* Decimal spelling of an exact integer. Returns NULL when the value
 * exceeds Python's 4300-digit str() limit (callers render
 * "<value too large>" or fall back like Python does). */
char* bs_num_int_strdup(BSharpNumber n);

#endif /* BSHARP_NUMBER_H */
