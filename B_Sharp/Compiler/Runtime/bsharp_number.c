/* (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * The source code of B_Sharp Programming Language is licensed under
 * GPLv3; see LICENSE.md for details.
 *
 * ----------------------------------------------------------------
 * Module: bsharp_number.c: bignum + int64 fast path + float Number.
 */

#include "bsharp_number.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

/* ==================================================================
 * Bignum primitives (sign-magnitude, base 2^32, little-endian)
 * ================================================================== */

static BSharpBignum* bn_raw(size_t len) {
    BSharpBignum* bn = (BSharpBignum*)malloc(sizeof(BSharpBignum));
    if (!bn) exit(1);
    bn->sign = 0;
    bn->len = len;
    bn->limbs = len ? (uint32_t*)calloc(len, sizeof(uint32_t)) : NULL;
    if (len && !bn->limbs) exit(1);
    return bn;
}

static void bn_free(BSharpBignum* bn) {
    if (!bn) return;
    free(bn->limbs);
    free(bn);
}

static void bn_normalize(BSharpBignum* bn) {
    while (bn->len > 0 && bn->limbs[bn->len - 1] == 0) bn->len--;
    if (bn->len == 0) bn->sign = 0;
}

static BSharpBignum* bn_zero(void) {
    return bn_raw(0);
}

static BSharpBignum* bn_from_u64(uint64_t v, int sign) {
    BSharpBignum* bn = bn_raw(2);
    bn->limbs[0] = (uint32_t)(v & 0xFFFFFFFFu);
    bn->limbs[1] = (uint32_t)(v >> 32);
    bn->sign = (v == 0) ? 0 : sign;
    bn_normalize(bn);
    return bn;
}

static BSharpBignum* bn_copy(const BSharpBignum* src) {
    BSharpBignum* bn = bn_raw(src->len);
    if (src->len) memcpy(bn->limbs, src->limbs, src->len * sizeof(uint32_t));
    bn->sign = src->sign;
    return bn;
}

static int bn_cmp_mag(const BSharpBignum* a, const BSharpBignum* b) {
    if (a->len != b->len) return a->len < b->len ? -1 : 1;
    for (size_t i = a->len; i-- > 0; ) {
        if (a->limbs[i] != b->limbs[i])
            return a->limbs[i] < b->limbs[i] ? -1 : 1;
    }
    return 0;
}

static BSharpBignum* bn_add_mag(const BSharpBignum* a, const BSharpBignum* b) {
    size_t n = a->len > b->len ? a->len : b->len;
    BSharpBignum* r = bn_raw(n + 1);
    uint64_t carry = 0;
    for (size_t i = 0; i < n; i++) {
        uint64_t av = i < a->len ? a->limbs[i] : 0;
        uint64_t bv = i < b->len ? b->limbs[i] : 0;
        uint64_t sum = av + bv + carry;
        r->limbs[i] = (uint32_t)(sum & 0xFFFFFFFFu);
        carry = sum >> 32;
    }
    r->limbs[n] = (uint32_t)carry;
    r->sign = 1;
    bn_normalize(r);
    return r;
}

/* requires |a| >= |b| */
static BSharpBignum* bn_sub_mag(const BSharpBignum* a, const BSharpBignum* b) {
    BSharpBignum* r = bn_raw(a->len);
    int64_t borrow = 0;
    for (size_t i = 0; i < a->len; i++) {
        int64_t bv = i < b->len ? b->limbs[i] : 0;
        int64_t diff = (int64_t)a->limbs[i] - bv - borrow;
        if (diff < 0) {
            diff += (int64_t)1 << 32;
            borrow = 1;
        } else {
            borrow = 0;
        }
        r->limbs[i] = (uint32_t)diff;
    }
    r->sign = 1;
    bn_normalize(r);
    return r;
}

static BSharpBignum* bn_mul_mag(const BSharpBignum* a, const BSharpBignum* b) {
    if (a->len == 0 || b->len == 0) return bn_zero();
    BSharpBignum* r = bn_raw(a->len + b->len);
    for (size_t i = 0; i < a->len; i++) {
        uint64_t carry = 0;
        uint64_t ai = a->limbs[i];
        for (size_t j = 0; j < b->len; j++) {
            uint64_t cur =
                r->limbs[i + j] + ai * (uint64_t)b->limbs[j] + carry;
            r->limbs[i + j] = (uint32_t)(cur & 0xFFFFFFFFu);
            carry = cur >> 32;
        }
        size_t k = i + b->len;
        while (carry) {
            uint64_t cur = r->limbs[k] + carry;
            r->limbs[k] = (uint32_t)(cur & 0xFFFFFFFFu);
            carry = cur >> 32;
            k++;
        }
    }
    r->sign = 1;
    bn_normalize(r);
    return r;
}

/* In-place division of the whole magnitude by a small divisor.
 * Returns the remainder. */
static uint64_t bn_divmod_small_mut(BSharpBignum* bn, uint64_t divisor) {
    uint64_t rem = 0;
    for (size_t i = bn->len; i-- > 0; ) {
        uint64_t cur = (rem << 32) | bn->limbs[i];
        bn->limbs[i] = (uint32_t)(cur / divisor);
        rem = cur % divisor;
    }
    bn_normalize(bn);
    return rem;
}

static int bn_clz32(uint32_t v) {
    int n = 0;
    if (v == 0) return 32;
    while ((v & 0x80000000u) == 0) { n++; v <<= 1; }
    return n;
}

/* Knuth Algorithm D, base 2^32. Inputs must be positive magnitudes.
 * Computes |a| = q*|b| + r. Returns heap-allocated q; *out_rem receives
 * the heap-allocated magnitude of the remainder. NULL if |b| == 0. */
static BSharpBignum* bn_divmod_mag(const BSharpBignum* a, const BSharpBignum* b,
                                   BSharpBignum** out_rem) {
    if (b->len == 0) {
        *out_rem = NULL;
        return NULL;
    }
    if (bn_cmp_mag(a, b) < 0) {
        *out_rem = bn_copy(a);
        return bn_zero();
    }
    if (b->len == 1) {
        uint64_t rem = 0;
        BSharpBignum* q = bn_copy(a);
        q->sign = 1;
        rem = bn_divmod_small_mut(q, b->limbs[0]);
        if (a->sign < 0) q->sign = q->len ? -1 : 0;
        *out_rem = bn_from_u64(rem, 1);
        return q;
    }

    int shift = bn_clz32(b->limbs[b->len - 1]);

    /* Normalize: u = a << shift with one extra high limb (slack for the
     * add-back carry), v = b << shift. */
    size_t un = a->len + 1;
    BSharpBignum* u = bn_raw(un + 1);
    uint64_t carry = 0;
    for (size_t i = 0; i < a->len; i++) {
        uint64_t cur = ((uint64_t)a->limbs[i] << shift) | carry;
        u->limbs[i] = (uint32_t)(cur & 0xFFFFFFFFu);
        carry = cur >> 32;
    }
    u->limbs[a->len] = (uint32_t)carry;
    u->len = a->len;
    bn_normalize(u);
    u->len = un; /* exactly a->len+1 limbs: trailing zero or carry digit */

    size_t vn = b->len;
    BSharpBignum* v = bn_raw(vn);
    carry = 0;
    for (size_t i = 0; i < vn; i++) {
        uint64_t cur = ((uint64_t)b->limbs[i] << shift) | carry;
        v->limbs[i] = (uint32_t)(cur & 0xFFFFFFFFu);
        carry = cur >> 32;
    }
    v->sign = 1;

    size_t m = un - vn; /* quotient limb count minus one */
    BSharpBignum* q = bn_raw(m + 1);
    q->sign = 1;

    for (size_t jj = m + 1; jj-- > 0; ) {
        uint64_t top =
            ((uint64_t)u->limbs[jj + vn] << 32) | u->limbs[jj + vn - 1];
        uint64_t qhat = top / v->limbs[vn - 1];
        uint64_t rhat = top % v->limbs[vn - 1];

        if (qhat > 0xFFFFFFFFull) {
            qhat = 0xFFFFFFFFull;
            rhat = top - qhat * v->limbs[vn - 1];
        }
        while (qhat * v->limbs[vn - 2] >
               ((rhat << 32) | u->limbs[jj + vn - 2])) {
            qhat--;
            rhat += v->limbs[vn - 1];
            if (rhat > 0xFFFFFFFFull) break;
        }

        /* Multiply and subtract qhat * v from u[jj .. jj+vn]. */
        int64_t borrow = 0;
        uint64_t carry2 = 0;
        for (size_t i = 0; i < vn; i++) {
            uint64_t p = qhat * (uint64_t)v->limbs[i] + carry2;
            carry2 = p >> 32;
            int64_t sub = (int64_t)u->limbs[jj + i] - (int64_t)(uint32_t)p
                          - borrow;
            if (sub < 0) {
                sub += (int64_t)1 << 32;
                borrow = 1;
            } else {
                borrow = 0;
            }
            u->limbs[jj + i] = (uint32_t)sub;
        }
        int64_t high = (int64_t)u->limbs[jj + vn] - (int64_t)carry2 - borrow;
        if (high < 0) {
            /* qhat was one too large: add v back. */
            uint64_t c = 0;
            for (size_t i = 0; i < vn; i++) {
                uint64_t sum = (uint64_t)u->limbs[jj + i] + v->limbs[i] + c;
                u->limbs[jj + i] = (uint32_t)(sum & 0xFFFFFFFFu);
                c = sum >> 32;
            }
            u->limbs[jj + vn] = (uint32_t)((uint64_t)high + c);
            qhat--;
        } else {
            u->limbs[jj + vn] = (uint32_t)high;
        }
        q->limbs[jj] = (uint32_t)qhat;
    }

    /* Remainder = low vn+1 limbs of u, right-shifted by `shift`. */
    BSharpBignum* rem = bn_raw(vn);
    for (size_t j = vn; j-- > 0; ) {
        uint32_t lo = u->limbs[j];
        uint32_t hi = u->limbs[j + 1];
        rem->limbs[j] = shift
            ? (uint32_t)((lo >> shift) | (hi << (32 - shift)))
            : lo;
    }
    rem->sign = 1;
    bn_normalize(rem);

    bn_normalize(q);
    *out_rem = rem;
    bn_free(u);
    bn_free(v);
    return q;
}

/* Binary exponentiation of magnitudes. */
static BSharpBignum* bn_pow_mag(const BSharpBignum* base, uint64_t exp) {
    BSharpBignum* result = bn_from_u64(1, 1);
    BSharpBignum* b = bn_copy(base);
    while (exp > 0) {
        if (exp & 1) {
            BSharpBignum* t = bn_mul_mag(result, b);
            bn_free(result);
            result = t;
        }
        exp >>= 1;
        if (exp) {
            BSharpBignum* t = bn_mul_mag(b, b);
            bn_free(b);
            b = t;
        }
    }
    bn_free(b);
    return result;
}

static bool bn_bit_at(const BSharpBignum* bn, size_t pos) {
    size_t w = pos / 32;
    if (w >= bn->len) return false;
    return ((bn->limbs[w] >> (pos % 32)) & 1u) != 0;
}

static bool bn_any_bit_below(const BSharpBignum* bn, size_t pos) {
    size_t full = pos / 32;
    unsigned b = (unsigned)(pos % 32);
    for (size_t i = 0; i < full && i < bn->len; i++)
        if (bn->limbs[i]) return true;
    if (b > 0 && full < bn->len) {
        uint32_t mask = (b == 32) ? 0xFFFFFFFFu : ((1u << b) - 1);
        if (bn->limbs[full] & mask) return true;
    }
    return false;
}

/* Correctly-rounded |bn| -> double (round half-to-even), matching
 * CPython's long->float conversion. Returns false on overflow
 * (Python's OverflowError -> MTH001). */
static bool bn_to_double(const BSharpBignum* bn, double* out) {
    if (bn->len == 0) {
        *out = 0.0;
        return true;
    }
    size_t top_bits = 0;
    uint32_t top = bn->limbs[bn->len - 1];
    while (top) { top_bits++; top >>= 1; }
    size_t bits = (bn->len - 1) * 32 + top_bits;
    if (bits > 1024) return false; /* >= 2^1024: never representable */

    if (bits <= 64) {
        uint64_t v;
        if (bn->len == 1) {
            v = bn->limbs[0];
        } else {
            v = (uint64_t)bn->limbs[0] | ((uint64_t)bn->limbs[1] << 32);
        }
        *out = (double)v; /* C guarantees correct rounding here */
        return !isinf(*out);
    }

    /* q = floor(value / 2^shift): exactly the top 53 bits. */
    size_t shift = bits - 53;
    uint64_t q = 0;
    {
        size_t w = shift / 32;
        int b0 = (int)(shift % 32);
        int collected = 0;
        size_t i = w;
        int bitoff = b0;
        while (collected < 53 && i < bn->len) {
            uint64_t chunk = bitoff ? (bn->limbs[i] >> bitoff)
                                    : bn->limbs[i];
            int avail = 32 - bitoff;
            int take = 53 - collected;
            if (take > avail) take = avail;
            q |= (chunk & (((uint64_t)1 << take) - 1)) << collected;
            collected += take;
            i++;
            bitoff = 0;
        }
    }
    /* Round using the first dropped bit (shift-1) and a sticky scan. */
    bool half = bn_bit_at(bn, shift - 1);
    bool lower = shift > 1 && bn_any_bit_below(bn, shift - 1);
    if (half && (lower || (q & 1))) q++;

    double d = ldexp((double)q, (int)shift);
    if (isinf(d)) return false;
    *out = d;
    return true;
}

/* Exact conversion of a finite integral double to a magnitude.
 * Caller guarantees |d| >= 2^63 (so d's exponent easily covers the
 * 53-bit mantissa times a non-negative power of two). */
static BSharpBignum* bn_from_double_mag(double d) {
    int e;
    double frac = frexp(d, &e);                  /* d = frac * 2^e */
    uint64_t sig = (uint64_t)ldexp(frac, 53);    /* exact mantissa */
    int exp = e - 53;                            /* value = sig * 2^exp */

    BSharpBignum* t = bn_from_u64(sig, 1);
    if (exp <= 0) return t;

    /* shift left by `exp` bits: first within limbs, then reindex. */
    unsigned bits = (unsigned)(exp % 32);
    size_t words = (size_t)(exp / 32);

    BSharpBignum* s = bn_raw(t->len + 1);
    uint64_t carry = 0;
    for (size_t i = 0; i < t->len; i++) {
        uint64_t cur = ((uint64_t)t->limbs[i] << bits) | carry;
        s->limbs[i] = (uint32_t)(cur & 0xFFFFFFFFu);
        carry = cur >> 32;
    }
    if (carry) s->limbs[t->len] = (uint32_t)carry;
    s->sign = 1;
    bn_normalize(s);
    bn_free(t);

    BSharpBignum* r = bn_raw(s->len + words);
    for (size_t i = 0; i < s->len; i++) r->limbs[i + words] = s->limbs[i];
    r->sign = 1;
    bn_normalize(r);
    bn_free(s);
    return r;
}

/* ==================================================================
 * Number constructors / canonicalisation
 * ================================================================== */

BSharpNumber bs_num_i64(int64_t value) {
    BSharpNumber n;
    n.kind = BS_NUM_INT64;
    n.as.i = value;
    return n;
}

BSharpNumber bs_num_f64(double value) {
    BSharpNumber n;
    n.kind = BS_NUM_FLOAT;
    n.as.d = value;
    return n;
}

BSharpNumber bs_num_zero(void) {
    return bs_num_i64(0);
}

/* Wraps a magnitude (ownership transferred) into a canonical Number. */
static BSharpNumber bn_to_num(BSharpBignum* bn) {
    bn_normalize(bn);
    if (bn->len == 0) {
        bn_free(bn);
        return bs_num_zero();
    }
    if (bn->len <= 2) {
        uint64_t v = bn->limbs[0];
        if (bn->len == 2) v |= (uint64_t)bn->limbs[1] << 32;
        if (bn->sign >= 0) {
            if (v <= (uint64_t)INT64_MAX) {
                bn_free(bn);
                return bs_num_i64((int64_t)v);
            }
        } else {
            if (v <= (uint64_t)INT64_MAX + 1ull) {
                int64_t r = (v == (uint64_t)INT64_MAX + 1ull)
                    ? INT64_MIN : -(int64_t)v;
                bn_free(bn);
                return bs_num_i64(r);
            }
        }
    }
    BSharpNumber n;
    n.kind = BS_NUM_BIG;
    n.as.big = bn;
    return n;
}

BSharpNumber bs_num_from_dec(const char* text, bool* ok) {
    if (ok) *ok = false;
    if (!text || !*text) return bs_num_zero();

    int sign = 1;
    const char* p = text;
    if (*p == '+' || *p == '-') {
        if (*p == '-') sign = -1;
        p++;
    }
    if (!*p) return bs_num_zero();

    /* int64 fast path: at most 18 significant digits. */
    uint64_t acc = 0;
    size_t digits = 0;
    bool fast = true;
    for (const char* q = p; *q; q++) {
        if (*q < '0' || *q > '9') return bs_num_zero();
        digits++;
        if (digits > 18) { fast = false; break; }
        acc = acc * 10 + (uint64_t)(*q - '0');
    }
    if (fast && digits > 0) {
        if (sign > 0 && acc <= (uint64_t)INT64_MAX) {
            if (ok) *ok = true;
            return bs_num_i64((int64_t)acc);
        }
        if (sign < 0 && acc <= (uint64_t)INT64_MAX + 1ull) {
            if (ok) *ok = true;
            if (acc == (uint64_t)INT64_MAX + 1ull)
                return bs_num_i64(INT64_MIN);
            return bs_num_i64(-(int64_t)acc);
        }
        fast = false;
    }

    /* Slow path: accumulate digit by digit into a bignum. */
    BSharpBignum* a = bn_zero();
    for (const char* q = p; *q; q++) {
        if (*q < '0' || *q > '9') {
            bn_free(a);
            return bs_num_zero();
        }
        /* a = a * 10 */
        if (a->len) {
            BSharpBignum* scaled = bn_raw(a->len + 1);
            uint64_t c = 0;
            for (size_t i = 0; i < a->len; i++) {
                uint64_t cur = (uint64_t)a->limbs[i] * 10 + c;
                scaled->limbs[i] = (uint32_t)(cur & 0xFFFFFFFFu);
                c = cur >> 32;
            }
            if (c) scaled->limbs[a->len] = (uint32_t)c;
            scaled->sign = 1;
            bn_normalize(scaled);
            bn_free(a);
            a = scaled;
        }
        /* a += digit */
        uint64_t d = (uint64_t)(*q - '0');
        if (d) {
            uint64_t c = d;
            size_t i = 0;
            while (c && i < a->len) {
                uint64_t sum = (uint64_t)a->limbs[i] + c;
                a->limbs[i] = (uint32_t)(sum & 0xFFFFFFFFu);
                c = sum >> 32;
                i++;
            }
            if (c) {
                BSharpBignum* grown = bn_raw(a->len + 1);
                memcpy(grown->limbs, a->limbs, a->len * sizeof(uint32_t));
                grown->limbs[a->len] = (uint32_t)c;
                grown->sign = 1;
                bn_normalize(grown);
                bn_free(a);
                a = grown;
            }
        }
    }
    a->sign = a->len ? sign : 0;
    if (ok) *ok = true;
    return bn_to_num(a);
}

bool bs_num_is_int(BSharpNumber n) {
    return n.kind != BS_NUM_FLOAT;
}

bool bs_num_is_int64(BSharpNumber n) {
    return n.kind == BS_NUM_INT64;
}

bool bs_num_is_float(BSharpNumber n) {
    return n.kind == BS_NUM_FLOAT;
}

size_t bs_num_bit_length(BSharpNumber n) {
    if (n.kind == BS_NUM_INT64) {
        uint64_t v = n.as.i < 0 ? (uint64_t)(-(n.as.i + 1)) + 1ull
                                : (uint64_t)n.as.i;
        size_t bits = 0;
        while (v) { bits++; v >>= 1; }
        return bits;
    }
    if (n.kind == BS_NUM_BIG) {
        BSharpBignum* bn = n.as.big;
        if (bn->len == 0) return 0;
        uint32_t top = bn->limbs[bn->len - 1];
        size_t bits = 0;
        while (top) { bits++; top >>= 1; }
        return (bn->len - 1) * 32 + bits;
    }
    return 0;
}

int64_t bs_num_to_i64(BSharpNumber n, bool* ok) {
    if (n.kind == BS_NUM_INT64) {
        if (ok) *ok = true;
        return n.as.i;
    }
    if (ok) *ok = false;
    return 0;
}

BSharpNumberStatus bs_num_to_f64(BSharpNumber n, double* out) {
    if (n.kind == BS_NUM_FLOAT) {
        *out = n.as.d;
        return BS_NUM_OK;
    }
    if (n.kind == BS_NUM_INT64) {
        *out = (double)n.as.i; /* correctly rounded; always finite */
        return BS_NUM_OK;
    }
    bool neg = n.as.big->sign < 0;
    double d;
    if (!bn_to_double(n.as.big, &d)) return BS_NUM_OVERFLOW;
    *out = neg ? -d : d;
    return BS_NUM_OK;
}

BSharpNumber bs_num_neg(BSharpNumber n) {
    if (n.kind == BS_NUM_FLOAT) return bs_num_f64(-n.as.d);
    if (n.kind == BS_NUM_INT64) {
        if (n.as.i == INT64_MIN) {
            /* -INT64_MIN = 2^63: positive, outside int64 range. */
            BSharpBignum* bn = bn_from_u64((uint64_t)INT64_MAX + 1ull, 1);
            return bn_to_num(bn);
        }
        return bs_num_i64(-n.as.i);
    }
    /* BIG: never mutate the shared bignum - return a fresh copy. */
    BSharpBignum* c = bn_copy(n.as.big);
    c->sign = -c->sign;
    bn_normalize(c);
    BSharpNumber r;
    r.kind = BS_NUM_BIG;
    r.as.big = c;
    return r;
}

/* ==================================================================
 * Arithmetic
 * ================================================================== */

/* Sign of an exact integer value: -1, 0 or +1. */
static int num_sign(BSharpNumber n) {
    if (n.kind == BS_NUM_INT64)
        return n.as.i < 0 ? -1 : (n.as.i > 0 ? 1 : 0);
    if (n.kind == BS_NUM_BIG) return n.as.big->sign;
    return n.as.d < 0 ? -1 : (n.as.d > 0 ? 1 : 0); /* never used for floats */
}

/* Heap-allocated positive magnitude of an exact integer. */
static BSharpBignum* num_abs_mag(BSharpNumber n) {
    if (n.kind == BS_NUM_BIG) {
        BSharpBignum* c = bn_copy(n.as.big);
        c->sign = 1;
        bn_normalize(c);
        return c;
    }
    uint64_t m = n.as.i < 0 ? (uint64_t)(-(n.as.i + 1)) + 1ull
                            : (uint64_t)n.as.i;
    return bn_from_u64(m, 1);
}

static BSharpNumberStatus int_add(BSharpNumber a, BSharpNumber b,
                                  BSharpNumber* out) {
    if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64) {
        int64_t r;
        if (!__builtin_add_overflow(a.as.i, b.as.i, &r)) {
            *out = bs_num_i64(r);
            return BS_NUM_OK;
        }
    }
    int sa = num_sign(a);
    int sb = num_sign(b);
    BSharpBignum* ba = num_abs_mag(a);
    BSharpBignum* bb = num_abs_mag(b);
    BSharpBignum* r;
    if (sa == 0) {
        r = bb;
        bb = NULL;
        r->sign = r->len ? sb : 0;
    } else if (sb == 0) {
        r = ba;
        ba = NULL;
        r->sign = r->len ? sa : 0;
    } else if (sa == sb) {
        r = bn_add_mag(ba, bb);
        r->sign = sa;
        bn_free(ba);
        bn_free(bb);
        ba = bb = NULL;
    } else {
        int cmp = bn_cmp_mag(ba, bb);
        if (cmp == 0) {
            r = bn_zero();
        } else if (cmp > 0) {
            r = bn_sub_mag(ba, bb);
            r->sign = sa;
        } else {
            r = bn_sub_mag(bb, ba);
            r->sign = sb;
        }
        bn_free(ba);
        bn_free(bb);
        ba = bb = NULL;
    }
    if (ba) bn_free(ba);
    if (bb) bn_free(bb);
    *out = bn_to_num(r);
    return BS_NUM_OK;
}

static BSharpNumberStatus int_sub(BSharpNumber a, BSharpNumber b,
                                  BSharpNumber* out) {
    if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64) {
        int64_t r;
        if (!__builtin_sub_overflow(a.as.i, b.as.i, &r)) {
            *out = bs_num_i64(r);
            return BS_NUM_OK;
        }
    }
    BSharpNumber nb = bs_num_neg(b);
    BSharpNumberStatus st = int_add(a, nb, out);
    if (nb.kind == BS_NUM_BIG) bn_free(nb.as.big);
    return st;
}

static BSharpNumberStatus int_mul(BSharpNumber a, BSharpNumber b,
                                  BSharpNumber* out) {
    if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64) {
        int64_t r;
        if (!__builtin_mul_overflow(a.as.i, b.as.i, &r)) {
            *out = bs_num_i64(r);
            return BS_NUM_OK;
        }
    }
    int sign = num_sign(a) * num_sign(b);
    BSharpBignum* ba = num_abs_mag(a);
    BSharpBignum* bb = num_abs_mag(b);
    BSharpBignum* r = bn_mul_mag(ba, bb);
    r->sign = r->len ? sign : 0;
    bn_free(ba);
    bn_free(bb);
    *out = bn_to_num(r);
    return BS_NUM_OK;
}

BSharpNumberStatus bs_num_add(BSharpNumber a, BSharpNumber b, BSharpNumber* out) {
    if (a.kind == BS_NUM_FLOAT || b.kind == BS_NUM_FLOAT) {
        double da, db;
        if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        if (bs_num_to_f64(b, &db) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        *out = bs_num_f64(da + db);
        return BS_NUM_OK;
    }
    return int_add(a, b, out);
}

BSharpNumberStatus bs_num_sub(BSharpNumber a, BSharpNumber b, BSharpNumber* out) {
    if (a.kind == BS_NUM_FLOAT || b.kind == BS_NUM_FLOAT) {
        double da, db;
        if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        if (bs_num_to_f64(b, &db) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        *out = bs_num_f64(da - db);
        return BS_NUM_OK;
    }
    return int_sub(a, b, out);
}

BSharpNumberStatus bs_num_mul(BSharpNumber a, BSharpNumber b, BSharpNumber* out) {
    if (a.kind == BS_NUM_FLOAT || b.kind == BS_NUM_FLOAT) {
        double da, db;
        if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        if (bs_num_to_f64(b, &db) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        *out = bs_num_f64(da * db);
        return BS_NUM_OK;
    }
    return int_mul(a, b, out);
}

/* Total bit length of a magnitude (0 for zero). */
static size_t bn_bits(const BSharpBignum* bn) {
    if (bn->len == 0) return 0;
    uint32_t top = bn->limbs[bn->len - 1];
    int t = 0;
    while (top) { t++; top >>= 1; }
    return (bn->len - 1) * 32 + (size_t)t;
}

/* Exact magnitude left shift by s bits. */
static BSharpBignum* bn_shl(const BSharpBignum* a, size_t s) {
    if (a->len == 0 || s == 0) return bn_copy(a);
    size_t limb_sh = s / 32;
    int bit_sh = (int)(s % 32);
    BSharpBignum* r = bn_raw(a->len + limb_sh + (bit_sh ? 1 : 0));
    if (bit_sh == 0) {
        memcpy(r->limbs + limb_sh, a->limbs, a->len * sizeof(uint32_t));
    } else {
        uint32_t carry = 0;
        for (size_t i = 0; i < a->len; i++) {
            uint64_t v = ((uint64_t)a->limbs[i]) << bit_sh;
            r->limbs[i + limb_sh] = (uint32_t)v | carry;
            carry = (uint32_t)(v >> 32);
        }
        r->limbs[a->len + limb_sh] = carry;
    }
    r->sign = a->sign;
    bn_normalize(r);
    return r;
}

/* Top 54 bits of |bn| (bn must be nonzero, so bit 53 of *h is set).
 * *sticky collects every bit strictly below the window plus extra. */
static void bn_top54(const BSharpBignum* bn, uint64_t* h, bool* sticky,
                     bool extra) {
    size_t bits = bn_bits(bn);
    size_t shift = bits - 54;
    uint64_t window = 0;
    size_t i = shift / 32;
    int bitoff = (int)(shift % 32);
    int got = 0;
    while (got < 54 && i < bn->len) {
        uint64_t chunk = bitoff ? ((uint64_t)bn->limbs[i] >> bitoff)
                                : (uint64_t)bn->limbs[i];
        int avail = 32 - bitoff;
        int take = 54 - got;
        if (take > avail) take = avail;
        window |= (chunk & (((uint64_t)1 << take) - 1)) << got;
        got += take;
        i++;
        bitoff = 0;
    }
    *h = window;
    *sticky = extra || (shift > 0 && bn_any_bit_below(bn, shift));
}

/* Correctly-rounded `/` over two exact integers: Python's int/int
 * true division (round-half-even, overflow -> OverflowError, gradual
 * underflow to 0.0/-0.0). Callers pre-check b != 0 (RUN100). */
static BSharpNumberStatus int_true_div(BSharpNumber a, BSharpNumber b,
                                       BSharpNumber* out) {
    int sign = (num_sign(a) < 0) != (num_sign(b) < 0) ? -1 : 1;
    if (num_sign(b) == 0) return BS_NUM_OVERFLOW; /* unreachable: RUN100 */
    if (num_sign(a) == 0) {
        *out = bs_num_f64(sign < 0 ? -0.0 : 0.0);
        return BS_NUM_OK;
    }

    BSharpBignum* ma = num_abs_mag(a);
    BSharpBignum* mb = num_abs_mag(b);
    size_t la = bn_bits(ma);
    size_t lb = bn_bits(mb);

    /* Scale so that floor(N/D) carries at least 54 bits, keeping the
     * division exact; the exponent bookkeeping puts the binary point
     * back where it belongs. */
    BSharpBignum* n;
    BSharpBignum* d;
    long e;
    if (la <= lb + 54) {
        size_t s = 54 + lb - la;
        n = bn_shl(ma, s);
        d = mb;
        e = -(long)s;
        bn_free(ma);
    } else {
        size_t t = la - lb - 54;
        n = ma;
        d = bn_shl(mb, t);
        e = (long)t;
        bn_free(mb);
    }

    BSharpBignum* r = NULL;
    BSharpBignum* q = bn_divmod_mag(n, d, &r);
    bn_free(n);
    bn_free(d);
    if (!q) { /* d == 0 impossible here */
        bn_free(r);
        return BS_NUM_OVERFLOW;
    }

    uint64_t h;
    bool sticky;
    bn_top54(q, &h, &sticky, r != NULL && r->len != 0);
    uint64_t m = h >> 1;
    bool round_bit = (h & 1) != 0;
    long exp = (long)bn_bits(q) - 53 + e;
    bn_free(q);
    bn_free(r);

    if (round_bit && (sticky || (m & 1))) m++;
    if (m == ((uint64_t)1 << 53)) {
        m >>= 1;
        exp++;
    }

    double dval = ldexp((double)m, (int)exp);
    if (isinf(dval)) return BS_NUM_OVERFLOW;
    if (sign < 0) dval = -dval;
    *out = bs_num_f64(dval);
    return BS_NUM_OK;
}

BSharpNumberStatus bs_num_true_div(BSharpNumber a, BSharpNumber b,
                                   BSharpNumber* out) {
    if (!bs_num_is_float(a) && !bs_num_is_float(b))
        return int_true_div(a, b, out);
    double da, db;
    if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
    if (bs_num_to_f64(b, &db) != BS_NUM_OK) return BS_NUM_OVERFLOW;
    *out = bs_num_f64(da / db);
    return BS_NUM_OK;
}

/* Truncated division of two exact integers: both magnitudes computed
 * here; callers pre-check b != 0 (RUN100). */
static void int_divmod(BSharpNumber a, BSharpNumber b,
                       BSharpBignum** out_q, BSharpBignum** out_r) {
    BSharpBignum* ma = num_abs_mag(a);
    BSharpBignum* mb = num_abs_mag(b);
    *out_q = bn_divmod_mag(ma, mb, out_r);
    bn_free(ma);
    bn_free(mb);
}

BSharpNumberStatus bs_num_idiv(BSharpNumber a, BSharpNumber b,
                               BSharpNumber* out) {
    if (b.kind == BS_NUM_INT64 && b.as.i == 0) return BS_NUM_OVERFLOW;
    if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64) {
        if (a.as.i == INT64_MIN && b.as.i == -1) {
            *out = bn_to_num(bn_from_u64((uint64_t)INT64_MAX + 1ull, 1));
            return BS_NUM_OK;
        }
        *out = bs_num_i64(a.as.i / b.as.i); /* C truncation semantics */
        return BS_NUM_OK;
    }
    BSharpBignum* q;
    BSharpBignum* r;
    int_divmod(a, b, &q, &r);
    bn_free(r);
    int sign = (num_sign(a) != num_sign(b)) ? -1 : 1;
    q->sign = q->len ? sign : 0;
    *out = bn_to_num(q);
    return BS_NUM_OK;
}

BSharpNumberStatus bs_num_mod(BSharpNumber a, BSharpNumber b,
                              BSharpNumber* out) {
    if (b.kind == BS_NUM_INT64 && b.as.i == 0) return BS_NUM_OVERFLOW;
    if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64) {
        if (b.as.i == -1) { /* also protects INT64_MIN % -1 (UB in C) */
            *out = bs_num_i64(0);
            return BS_NUM_OK;
        }
        *out = bs_num_i64(a.as.i % b.as.i); /* sign of the dividend */
        return BS_NUM_OK;
    }
    BSharpBignum* q;
    BSharpBignum* r;
    int_divmod(a, b, &q, &r);
    bn_free(q);
    r->sign = r->len ? num_sign(a) : 0;
    *out = bn_to_num(r);
    return BS_NUM_OK;
}

BSharpNumberStatus bs_num_pow(BSharpNumber a, BSharpNumber b,
                              BSharpNumber* out) {
    if (a.kind == BS_NUM_FLOAT || b.kind == BS_NUM_FLOAT) {
        double da, db;
        if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        if (bs_num_to_f64(b, &db) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        /* NaN beats every other rule (incl. negative base): pow(-2, nan)
         * is nan, not the complex-number refusal. */
        if (isnan(da) || isnan(db)) {
            *out = bs_num_f64((double)NAN);
            return BS_NUM_OK;
        }
        if (da < 0.0 && db != trunc(db)) return BS_NUM_COMPLEX;
        double r = pow(da, db);
        if (isnan(r)) { /* defensive: should be unreachable */
            *out = bs_num_f64(r);
            return BS_NUM_OK;
        }
        if (isinf(r)) return BS_NUM_OVERFLOW;
        *out = bs_num_f64(r);
        return BS_NUM_OK;
    }

    /* ---- both exact integers ---- */

    /* exponent 0: anything ^ 0 = 1 (including 0 ^ 0). */
    if (b.kind == BS_NUM_INT64 && b.as.i == 0) {
        *out = bs_num_i64(1);
        return BS_NUM_OK;
    }

    /* Base in {0, 1, -1}: exact, tiny, and exempt from the guard.
     * (0 ^ negative was rejected by the caller as RUN105.) */
    if (a.kind == BS_NUM_INT64) {
        int64_t av = a.as.i;
        if (av == 0) {
            *out = bs_num_i64(0);
            return BS_NUM_OK;
        }
        bool exp_neg;
        if (b.kind == BS_NUM_INT64) {
            exp_neg = b.as.i < 0;
        } else {
            exp_neg = b.as.big->sign < 0;
        }
        if (av == 1) {
            *out = exp_neg ? bs_num_f64(1.0) : bs_num_i64(1);
            return BS_NUM_OK;
        }
        if (av == -1) {
            /* (-1)^n = 1 if even else -1; parity comes from |n|. */
            bool even;
            if (b.kind == BS_NUM_INT64) {
                int64_t bi = b.as.i;
                even = (bi % 2 == 0);
            } else {
                even = (b.as.big->limbs[0] & 1u) == 0;
            }
            int64_t r = even ? 1 : -1;
            *out = exp_neg ? bs_num_f64((double)r) : bs_num_i64(r);
            return BS_NUM_OK;
        }
    }

    /* Guard: estimated result bits = bit_length(|base|) * |exponent|. */
    size_t base_bits = bs_num_bit_length(a);
    bool exp_neg;
    uint64_t abs_exp;
    if (b.kind == BS_NUM_INT64) {
        exp_neg = b.as.i < 0;
        abs_exp = b.as.i < 0 ? (uint64_t)(-(b.as.i + 1)) + 1ull
                             : (uint64_t)b.as.i;
    } else {
        exp_neg = b.as.big->sign < 0;
        abs_exp = UINT64_MAX;
        if (b.as.big->len <= 2) {
            uint64_t v = b.as.big->limbs[0];
            if (b.as.big->len == 2)
                v |= (uint64_t)b.as.big->limbs[1] << 32;
            abs_exp = v;
        }
    }
    uint64_t estimate;
    if (base_bits == 0) {
        estimate = 0;
    } else if (abs_exp > UINT64_MAX / base_bits) {
        estimate = UINT64_MAX;
    } else {
        estimate = (uint64_t)base_bits * abs_exp;
    }

    if (abs_exp > 1 && estimate > BS_MAX_POWER_RESULT_BITS) {
        /* Guarded path: the interpreter evaluates float(base) **
         * float(exponent) and maps non-finite results to MTH001;
         * finite results (only reachable for negative exponents)
         * come back as a float approximation + WRN002 warning. */
        double da, db;
        if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        if (bs_num_to_f64(b, &db) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        double r = pow(da, db);
        if (!isfinite(r)) return BS_NUM_OVERFLOW;
        *out = bs_num_f64(r);
        return BS_NUM_APPROX;
    }

    if (!exp_neg) {
        /* Exact: |a| ^ abs_exp with the sign of an odd result. */
        BSharpBignum* ma = num_abs_mag(a);
        BSharpBignum* r = bn_pow_mag(ma, abs_exp);
        bn_free(ma);
        if (num_sign(a) < 0 && (abs_exp & 1))
            r->sign = r->len ? -1 : 0;
        else if (r->len)
            r->sign = 1;
        *out = bn_to_num(r);
        return BS_NUM_OK;
    }

    /* Negative exponent (unguarded): compute the exact m = a^|b|, then
     * the interpreter's 1.0 / float(m) (probe-verified: double rounding
     * through float(m), NOT Python's single-rounded int/int divide). */
    if (abs_exp == 1) {
        double da;
        if (bs_num_to_f64(a, &da) != BS_NUM_OK) return BS_NUM_OVERFLOW;
        *out = bs_num_f64(1.0 / da);
        return BS_NUM_OK;
    }
    {
        BSharpBignum* ma = num_abs_mag(a);
        BSharpBignum* m = bn_pow_mag(ma, abs_exp);
        bn_free(ma);
        bool negr = num_sign(a) < 0 && (abs_exp & 1);
        m->sign = m->len ? (negr ? -1 : 1) : 0;
        double d;
        if (!bn_to_double(m, &d)) {
            bn_free(m);
            return BS_NUM_OVERFLOW;
        }
        bn_free(m);
        double val = negr ? -d : d;
        *out = bs_num_f64(1.0 / val);
        return BS_NUM_OK;
    }
}

/* ==================================================================
 * Equality / ordering
 * ================================================================== */

bool bs_num_eq(BSharpNumber a, BSharpNumber b) {
    if (a.kind != BS_NUM_FLOAT && b.kind != BS_NUM_FLOAT) {
        if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64)
            return a.as.i == b.as.i;
        if (a.kind == BS_NUM_BIG && b.kind == BS_NUM_BIG)
            return a.as.big->sign == b.as.big->sign &&
                   bn_cmp_mag(a.as.big, b.as.big) == 0;
        /* mixed: a BIG is never in int64 range (canonical form) */
        return false;
    }
    if (a.kind == BS_NUM_FLOAT && b.kind == BS_NUM_FLOAT)
        return a.as.d == b.as.d;

    /* exactly one float */
    BSharpNumber f = a.kind == BS_NUM_FLOAT ? a : b;
    BSharpNumber i = a.kind == BS_NUM_FLOAT ? b : a;
    double d = f.as.d;
    if (isnan(d) || isinf(d)) return false;
    if (d != trunc(d)) return false;

    if (d >= -9223372036854775808.0 && d < 9223372036854775808.0) {
        int64_t di = (int64_t)d;
        if (i.kind == BS_NUM_BIG) return false;
        return di == i.as.i;
    }
    /* |d| >= 2^63: build its exact integer value and compare exactly. */
    BSharpBignum* mag = bn_from_double_mag(fabs(d));
    mag->sign = d < 0 ? -1 : 1;
    BSharpNumber exact = bn_to_num(mag);
    bool eq = bs_num_eq(exact, i); /* both exact integers */
    if (exact.kind == BS_NUM_BIG) bn_free(exact.as.big);
    return eq;
}

/* Magnitude compare of two exact integers (heap-free). */
static int cmp_abs(BSharpNumber a, BSharpNumber b) {
    if (a.kind == BS_NUM_INT64 && b.kind == BS_NUM_INT64) {
        uint64_t ma = a.as.i < 0 ? (uint64_t)(-(a.as.i + 1)) + 1ull
                                 : (uint64_t)a.as.i;
        uint64_t mb = b.as.i < 0 ? (uint64_t)(-(b.as.i + 1)) + 1ull
                                 : (uint64_t)b.as.i;
        return ma < mb ? -1 : (ma > mb ? 1 : 0);
    }
    if (a.kind == BS_NUM_BIG && b.kind == BS_NUM_BIG)
        return bn_cmp_mag(a.as.big, b.as.big);
    /* mixed: |BIG| >= 2^63 > any int64 magnitude except INT64_MIN's
     * 2^63, and INT64_MIN is canonicalised to INT64 - so BIG wins. */
    return a.kind == BS_NUM_BIG ? 1 : -1;
}

int bs_num_cmp(BSharpNumber a, BSharpNumber b) {
    int sa = num_sign(a);
    int sb = num_sign(b);
    if (sa != sb) return sa < sb ? -1 : 1;
    if (sa == 0) return 0;
    int c = cmp_abs(a, b);
    return sa > 0 ? c : -c;
}

bool bs_num_order_key(BSharpNumber n, double* out) {
    if (n.kind == BS_NUM_FLOAT) {
        *out = n.as.d; /* NaN passes through: every C comparison against
                        * it is false, matching the interpreter. */
        return true;
    }
    double d;
    if (bs_num_to_f64(n, &d) != BS_NUM_OK) {
        bool neg = num_sign(n) < 0;
        *out = neg ? -INFINITY : INFINITY;
        return true;
    }
    *out = d;
    return true;
}

/* ==================================================================
 * Integer formatting
 * ================================================================== */

char* bs_num_int_strdup(BSharpNumber n) {
    if (n.kind == BS_NUM_FLOAT) return NULL; /* not an int */

    bool negative = num_sign(n) < 0;
    BSharpBignum* work = num_abs_mag(n);

    /* digits arrive least-significant first */
    size_t cap = 64;
    size_t len = 0;
    char* buf = (char*)malloc(cap);
    if (!buf) exit(1);

    if (work->len == 0) buf[len++] = '0';
    while (work->len > 0) {
        uint64_t rem = bn_divmod_small_mut(work, 10);
        if (len + 2 > cap) {
            cap *= 2;
            buf = (char*)realloc(buf, cap);
            if (!buf) exit(1);
        }
        buf[len++] = (char)('0' + rem);
        if (len > BS_INT_MAX_STR_DIGITS) {
            free(buf);
            bn_free(work);
            return NULL;
        }
    }
    bn_free(work);

    if (negative) {
        if (len + 2 > cap) {
            cap += 1;
            buf = (char*)realloc(buf, cap);
            if (!buf) exit(1);
        }
        buf[len++] = '-';
    }

    for (size_t i = 0, j = len; i + 1 < j; i++, j--) {
        char t = buf[i];
        buf[i] = buf[j - 1];
        buf[j - 1] = t;
    }
    buf[len] = '\0';
    return buf;
}
