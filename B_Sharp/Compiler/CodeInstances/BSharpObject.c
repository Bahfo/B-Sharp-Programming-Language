// (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Abstracted B-Sharp object holding all object-types methods.

// The B-Sharp source code itself is protected under the GPLv3
// License. However, the standard library is held under the LGPL
// license. For more info, check LICENSE.md file.

// ----------------------------------------------------------------
// Module: BSharpObject.c: every runtime operation on B# values,
// mirroring B_Sharp/ASTNodes/instances.py class-by-class so that the
// interpreter and compiled binaries behave byte-for-byte the same.
//
// Error positions come from the OPERAND VALUES (self->pos_start /
// self->pos_end) exactly like the interpreter, because the IR always
// positions every successfully produced expression result at its AST
// node. Successful results are returned with NULL positions - the
// generated IR sets them; failed results carry final positions and
// must be propagated untouched. The two exceptions that carry their
// own positions are documented at __negate / __get_element /
// __set_element in BSharpObject.h.
// ----------------------------------------------------------------

#include "BSharpObject.h"

/* ================= type-name tables ================= */

/* type(self).__name__ spellings (RUN003 / RUN112 / RUN114 / RUN119 /
 * RUN010 params use the raw case). */
static const char* value_class_name(BSharpValue* v) {
    switch (v->type) {
        case BSharp_Number:         return "Number";
        case BSharp_Bool:           return "Boolean";
        case BSharp_String:         return "String";
        case BSharp_Empty:          return "Empty";
        case BSharp_NaN:            return "NaN";
        case BSharp_Inf:            return "Inf";
        case BSharp_List:           return "List";
        case BSharp_Tuple:          return "Tuple";
        case BSharp_ErrorInstance:  return "ErrorInstance";
        case BSharp_Function:       return "Function";
        case BSharp_StructDef:      return "StructDefinition";
        case BSharp_StructInstance: return "StructInstance";
        case BSharp_Array:
            switch (v->as.array.element_type) {
                case BSharp_Number: return "NumberArray";
                case BSharp_String: return "StringArray";
                case BSharp_Bool:   return "BooleanArray";
                case BSharp_Empty:  return "EmptyArray";
                default:            return "Array";
            }
    }
    return "Value";
}

/* type(self).__name__.lower() spellings (RUN099 {type_name}). */
static const char* type_lower_name(BSharpValue* v) {
    switch (v->type) {
        case BSharp_Number:         return "number";
        case BSharp_Bool:           return "boolean";
        case BSharp_String:         return "string";
        case BSharp_Empty:          return "empty";
        case BSharp_NaN:            return "nan";
        case BSharp_Inf:            return "inf";
        case BSharp_List:           return "list";
        case BSharp_Tuple:          return "tuple";
        case BSharp_ErrorInstance:  return "errorinstance";
        case BSharp_Function:       return "function";
        case BSharp_StructDef:      return "structdefinition";
        case BSharp_StructInstance: return "structinstance";
        case BSharp_Array:
            switch (v->as.array.element_type) {
                case BSharp_Number: return "numberarray";
                case BSharp_String: return "stringarray";
                case BSharp_Bool:   return "booleanarray";
                case BSharp_Empty:  return "emptyarray";
                default:            return "array";
            }
    }
    return "value";
}

/* ================= number helpers ================= */

static bool num_is_zero(BSharpNumber n) {
    if (n.kind == BS_NUM_INT64) return n.as.i == 0;
    if (n.kind == BS_NUM_BIG)   return n.as.big->len == 0;
    return n.as.d == 0.0;
}

static bool num_is_negative(BSharpNumber n) {
    if (n.kind == BS_NUM_INT64) return n.as.i < 0;
    if (n.kind == BS_NUM_BIG)   return n.as.big->sign < 0;
    return n.as.d < 0.0;
}

/* Negative infinity also reports negative - callers that must refuse
 * infinite exponents (0 ^ -inf) check num_is_infinite separately. */
static bool num_is_infinite(BSharpNumber n) {
    return n.kind == BS_NUM_FLOAT && isinf(n.as.d);
}

/* ================= Python repr() for doubles =================
 * str(float) in Python 3 is repr(): shortest round-tripping digits,
 * fixed notation iff the decimal exponent is in [-4, 15], otherwise
 * scientific with a signed exponent of at least two digits. */
static char* f64_repr(double v) {
    if (isnan(v)) return strdup("nan");
    if (isinf(v)) return strdup(v < 0 ? "-inf" : "inf");

    char buf[64];
    int prec;
    /* shortest precision that round-trips (p significant digits) */
    for (prec = 1; prec <= 17; prec++) {
        snprintf(buf, sizeof(buf), "%.*e", prec - 1, v);
        if (strtod(buf, NULL) == v) break;
    }
    if (prec > 17) {
        snprintf(buf, sizeof(buf), "%.16e", v);
    }

    /* buf looks like [-]d[.ddd]e[+-]XX */
    const char* p = buf;
    bool neg = (*p == '-');
    if (neg) p++;
    const char* digits_start = p;
    while (*digits_start >= '0' && *digits_start <= '9') digits_start++;
    size_t int_digits = (size_t)(digits_start - p);
    const char* epos = strchr(p, 'e');
    int exp10 = epos ? (int)strtol(epos + 1, NULL, 10) : 0;

    char mantissa[32];
    size_t mlen = 0;
    for (const char* q = p; q != epos; q++) {
        if (*q >= '0' && *q <= '9') {
            if (mlen < sizeof(mantissa) - 1) mantissa[mlen++] = *q;
        }
    }
    mantissa[mlen] = '\0';
    (void)int_digits;

    char out[64];
    size_t o = 0;
    if (neg) out[o++] = '-';

    if (exp10 >= -4 && exp10 <= 15) {
        /* fixed notation */
        if (exp10 >= 0) {
            size_t int_len = (size_t)exp10 + 1;
            size_t i = 0;
            for (; i < int_len && i < mlen; i++) out[o++] = mantissa[i];
            for (; i < int_len; i++) out[o++] = '0';
            size_t frac_start = mlen > int_len ? int_len : mlen;
            if (frac_start < mlen) {
                out[o++] = '.';
                for (size_t j = frac_start; j < mlen; j++) out[o++] = mantissa[j];
            } else {
                out[o++] = '.';
                out[o++] = '0';
            }
        } else {
            out[o++] = '0';
            out[o++] = '.';
            for (int z = 0; z < -exp10 - 1; z++) out[o++] = '0';
            for (size_t j = 0; j < mlen; j++) out[o++] = mantissa[j];
        }
    } else {
        /* scientific notation */
        out[o++] = mantissa[0];
        if (mlen > 1) {
            out[o++] = '.';
            for (size_t j = 1; j < mlen; j++) out[o++] = mantissa[j];
        }
        out[o++] = 'e';
        out[o++] = exp10 < 0 ? '-' : '+';
        int a = exp10 < 0 ? -exp10 : exp10;
        char ebuf[16];
        snprintf(ebuf, sizeof(ebuf), "%02d", a);
        for (const char* q = ebuf; *q; q++) out[o++] = *q;
    }
    out[o] = '\0';
    return strdup(out);
}

char* __number_to_str(BSharpNumber n) {
    if (n.kind == BS_NUM_FLOAT) return f64_repr(n.as.d);
    char* s = bs_num_int_strdup(n);
    if (!s) return strdup("<value too large>");
    return s;
}

/* ================= failure helpers ================= */

/* RUN099 at the operand's own position, like Value._op_error. */
static ReturnStatement fail_op(BSharpValue* self, const char* op) {
    BSharpParam params[2] = {
        BS_PARAM("type_name", type_lower_name(self)),
        BS_PARAM("op", op),
    };
    return bsharp_failure(
        "RUN099", self->pos_start, self->pos_end, params, 2);
}

/* MTH001 at the operand's own position (BSharpMathError). */
static ReturnStatement fail_math(BSharpValue* self) {
    return bsharp_failure(
        "MTH001", self->pos_start, self->pos_end, NULL, 0);
}

static ReturnStatement fail_code(
    BSharpValue* self, const char* code) {
    return bsharp_failure(
        code, self->pos_start, self->pos_end, NULL, 0);
}

/* ================= constructors ================= */

BSharpValue* __allocate_base_value(BSharpType type) {
    BSharpValue* val = (BSharpValue*)calloc(1, sizeof(BSharpValue));
    if (!val) exit(1);
    val->type = type;
    val->pos_start = NULL;
    val->pos_end = NULL;
    val->context = NULL;
    return val;
}

BSharpValue* __create_number(BSharpNumber value) {
    BSharpValue* val = __allocate_base_value(BSharp_Number);
    val->as.num = value;
    return val;
}

BSharpValue* __create_number_i64(int64_t value) {
    return __create_number(bs_num_i64(value));
}

BSharpValue* __create_boolean(bool value) {
    BSharpValue* val = __allocate_base_value(BSharp_Bool);
    val->as.boolean = value;
    return val;
}

BSharpValue* __create_string(const char* value) {
    BSharpValue* val = __allocate_base_value(BSharp_String);
    val->as.string = strdup(value ? value : "");
    if (!val->as.string) exit(1);
    return val;
}

BSharpValue* __create_empty(void) {
    return __allocate_base_value(BSharp_Empty);
}

BSharpValue* __create_nan(void) {
    return __allocate_base_value(BSharp_NaN);
}

BSharpValue* __create_inf(int sign) {
    BSharpValue* val = __allocate_base_value(BSharp_Inf);
    val->as.inf_sign = sign >= 0 ? 1 : -1;
    return val;
}

BSharpValue* __create_list(size_t initial_capacity) {
    BSharpValue* val = __allocate_base_value(BSharp_List);
    val->as.list.size = 0;
    val->as.list.capacity = initial_capacity > 0 ? initial_capacity : 4;
    val->as.list.elements = (BSharpValue**)malloc(
        val->as.list.capacity * sizeof(BSharpValue*));
    if (!val->as.list.elements) exit(1);
    val->as.list.is_const = false;
    return val;
}

BSharpValue* __create_array(
    BSharpType element_type,
    int depth,
    const char* type_name,
    size_t initial_capacity
) {
    BSharpValue* val = __allocate_base_value(BSharp_Array);
    val->as.array.list_data.size = 0;
    val->as.array.list_data.capacity =
        initial_capacity > 0 ? initial_capacity : 4;
    val->as.array.list_data.elements = (BSharpValue**)malloc(
        val->as.array.list_data.capacity * sizeof(BSharpValue*));
    if (!val->as.array.list_data.elements) exit(1);
    val->as.array.list_data.is_const = false;
    val->as.array.element_type = element_type;
    val->as.array.depth = depth > 0 ? depth : 1;
    val->as.array.type_name = type_name ? strdup(type_name) : NULL;
    return val;
}

BSharpValue* __create_tuple(BSharpValue** elements, size_t size) {
    BSharpValue* val = __allocate_base_value(BSharp_Tuple);
    val->as.tuple.size = size;
    val->as.tuple.elements =
        (BSharpValue**)malloc(size * sizeof(BSharpValue*));
    if (!val->as.tuple.elements && size > 0) exit(1);
    for (size_t i = 0; i < size; i++) {
        val->as.tuple.elements[i] = elements[i];
    }
    return val;
}

/* ================= copying =================
 * Mirrors Python's Value.copy() family exactly: List/Array containers
 * are duplicated (nested collections recursed, is_const reset to
 * false, pos/context inherited) while every other type - scalars,
 * Tuple, Function, ErrorInstance, Struct* - is SHARED, because the
 * interpreter never copies those either (aliasing is intentional and
 * re-audited in Stage E). Big bignum payloads are shared too. */
BSharpValue* __copy_element(BSharpValue* self) {
    if (!self) return NULL;

    if (self->type == BSharp_List) {
        BSharpValue* copy = __create_list(self->as.list.capacity);
        copy->as.list.size = self->as.list.size;
        copy->as.list.is_const = false;
        for (size_t i = 0; i < self->as.list.size; i++) {
            BSharpValue* el = self->as.list.elements[i];
            copy->as.list.elements[i] =
                (el && (el->type == BSharp_List || el->type == BSharp_Array))
                    ? __copy_element(el) : el;
        }
        copy->pos_start = self->pos_start;
        copy->pos_end = self->pos_end;
        copy->context = self->context;
        return copy;
    }

    if (self->type == BSharp_Array) {
        BSharpValue* copy = __create_array(
            self->as.array.element_type,
            self->as.array.depth,
            self->as.array.type_name,
            self->as.array.list_data.capacity);
        copy->as.array.list_data.size = self->as.array.list_data.size;
        copy->as.array.list_data.is_const = false;
        for (size_t i = 0; i < self->as.array.list_data.size; i++) {
            BSharpValue* el = self->as.array.list_data.elements[i];
            copy->as.array.list_data.elements[i] =
                (el && (el->type == BSharp_List || el->type == BSharp_Array))
                    ? __copy_element(el) : el;
        }
        copy->pos_start = self->pos_start;
        copy->pos_end = self->pos_end;
        copy->context = self->context;
        return copy;
    }

    return self;
}

/* ================= list/array shared views ================= */

typedef struct {
    BSharpValue** elements;
    size_t size;
    bool* is_const;
} list_view;

/* Both List and Array expose their storage the same way; Tuple does
 * NOT count as list-like anywhere (Python treats it separately). */
static bool list_view_of(BSharpValue* v, list_view* out) {
    if (v->type == BSharp_List) {
        out->elements = v->as.list.elements;
        out->size = v->as.list.size;
        out->is_const = &v->as.list.is_const;
        return true;
    }
    if (v->type == BSharp_Array) {
        out->elements = v->as.array.list_data.elements;
        out->size = v->as.array.list_data.size;
        out->is_const = &v->as.array.list_data.is_const;
        return true;
    }
    return false;
}

static bool is_list_like(BSharpValue* v) {
    return v->type == BSharp_List || v->type == BSharp_Array;
}

/* Grows `view`'s container by one slot. Callers own the container
 * pointer; both List and Array keep a stable elements array. */
static void list_append_slot(
    BSharpValue* container, BSharpValue* element) {
    list_view v = {NULL, 0, NULL};
    if (!list_view_of(container, &v)) exit(1);
    size_t* cap = container->type == BSharp_List
        ? &container->as.list.capacity
        : &container->as.array.list_data.capacity;
    if (v.size >= *cap) {
        *cap = *cap * 2 + 4;
        v.elements = (BSharpValue**)realloc(v.elements,
            *cap * sizeof(BSharpValue*));
        if (!v.elements) exit(1);
        if (container->type == BSharp_List) {
            container->as.list.elements = v.elements;
        } else {
            container->as.array.list_data.elements = v.elements;
        }
    }
    v.elements[v.size] = element;
    if (container->type == BSharp_List) {
        container->as.list.size = v.size + 1;
    } else {
        container->as.array.list_data.size = v.size + 1;
    }
}

/* ================= UTF-8 string indexing =================
 * Python indexes str objects by code point, so String reads walk
 * UTF-8 sequences. (Byte order equals code point order, so strcmp
 * stays valid for equality and ordering.) */

static size_t utf8_count(const char* s) {
    size_t n = 0;
    for (const char* p = s; *p; p++) {
        if (((unsigned char)*p & 0xC0) != 0x80) n++;
    }
    return n;
}

static const char* utf8_nth(const char* s, int64_t i) {
    if (i <= 0) return s;
    for (const char* p = s; *p; p++) {
        if (((unsigned char)*p & 0xC0) != 0x80) {
            if (i == 0) return p;
            i--;
        }
    }
    return NULL;
}

static size_t utf8_seq_len(const char* p) {
    unsigned char c = (unsigned char)*p;
    if (c < 0x80) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3;
    if ((c & 0xF8) == 0xF0) return 4;
    return 1;
}

/* ================= arithmetic ================= */

static ReturnStatement mul_core(BSharpValue* self, BSharpValue* other);
static ReturnStatement div_core(BSharpValue* self, BSharpValue* other);

ReturnStatement __addition(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Number) {
        if (other->type != BSharp_Number) return fail_op(self, "addition");
        BSharpNumber out;
        if (bs_num_add(self->as.num, other->as.num, &out) != BS_NUM_OK) {
            return fail_math(self);
        }
        return bsharp_success(__create_number(out));
    }
    if (self->type == BSharp_String) {
        const char* rhs;
        char* owned = NULL;
        if (other->type == BSharp_String) {
            rhs = other->as.string;
        } else if (other->type == BSharp_Number) {
            owned = __number_to_str(other->as.num);
            rhs = owned;
        } else if (other->type == BSharp_Bool) {
            rhs = other->as.boolean ? "true" : "false";
        } else {
            return fail_op(self, "addition");
        }
        size_t la = strlen(self->as.string);
        size_t lb = strlen(rhs);
        char* buf = (char*)malloc(la + lb + 1);
        if (!buf) { free(owned); exit(1); }
        memcpy(buf, self->as.string, la);
        memcpy(buf + la, rhs, lb);
        buf[la + lb] = '\0';
        free(owned);
        BSharpValue* val = __allocate_base_value(BSharp_String);
        val->as.string = buf;
        return bsharp_success(val);
    }
    return fail_op(self, "addition");
}

ReturnStatement __subtraction(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Number) {
        if (other->type != BSharp_Number) return fail_op(self, "subtraction");
        BSharpNumber out;
        if (bs_num_sub(self->as.num, other->as.num, &out) != BS_NUM_OK) {
            return fail_math(self);
        }
        return bsharp_success(__create_number(out));
    }
    return fail_op(self, "subtraction");
}

/* Builds a fresh container of self's kind holding `n` elements
 * (Array keeps its annotation fields, context is inherited). */
static BSharpValue* wrap_container(
    BSharpValue* self, BSharpValue** elements, size_t n) {
    if (self->type == BSharp_Array) {
        size_t cap = self->as.array.list_data.capacity;
        BSharpValue* res = __create_array(
            self->as.array.element_type,
            self->as.array.depth,
            self->as.array.type_name,
            n > cap ? n : cap);
        for (size_t i = 0; i < n; i++) {
            res->as.array.list_data.elements[i] = elements[i];
        }
        res->as.array.list_data.size = n;
        res->context = self->context;
        return res;
    }
    size_t cap = self->as.list.capacity;
    BSharpValue* res = __create_list(n > cap ? n : cap);
    for (size_t i = 0; i < n; i++) {
        res->as.list.elements[i] = elements[i];
    }
    res->as.list.size = n;
    res->context = self->context;
    return res;
}

/* Python's List._element_wise: an element that refuses the operation
 * is kept unchanged so the container size is always preserved. */
static BSharpValue** mul_elements_keep(
    BSharpValue** src, size_t n,
    BSharpValue* other, size_t* out_n) {
    BSharpValue** els = (BSharpValue**)malloc(n * sizeof(BSharpValue*));
    if (!els && n > 0) exit(1);
    for (size_t i = 0; i < n; i++) {
        ReturnStatement r = mul_core(src[i], other);
        els[i] = r.error ? src[i] : r.value;
    }
    *out_n = n;
    return els;
}

/* String * Number: RUN108 unless the factor is an exact integer,
 * RUN107 for negatives, MTH001 when the repeat cannot materialise
 * (Python's OverflowError on `s * huge`). */
static ReturnStatement string_mul(
    BSharpValue* self, BSharpValue* other) {
    if (other->type != BSharp_Number || !bs_num_is_int(other->as.num)) {
        return bsharp_failure(
            "RUN108", self->pos_start, self->pos_end, NULL, 0);
    }
    if (num_is_negative(other->as.num)) {
        return bsharp_failure(
            "RUN107", self->pos_start, self->pos_end, NULL, 0);
    }
    if (other->as.num.kind == BS_NUM_BIG) {
        /* any BIG exceeds PY_SSIZE_T_MAX: Python raises OverflowError */
        return fail_math(self);
    }
    int64_t k = other->as.num.as.i;   /* >= 0 */
    size_t len = strlen(self->as.string);
    if (k != 0 && len > (size_t)(SIZE_MAX / (size_t)k)) {
        return fail_math(self);
    }
    size_t total = len * (size_t)k;
    char* buf = (char*)malloc(total + 1);
    if (!buf) exit(1);
    for (size_t i = 0; i < (size_t)k; i++) {
        memcpy(buf + i * len, self->as.string, len);
    }
    buf[total] = '\0';
    BSharpValue* val = __allocate_base_value(BSharp_String);
    val->as.string = buf;
    return bsharp_success(val);
}

/* List/Array * Number / List - the body of both List.multiplication
 * and Array.multiplication (arrays re-wrap the result with their own
 * annotation via wrap_container). */
static ReturnStatement mul_container(
    BSharpValue* self, BSharpValue* other) {
    list_view v = {NULL, 0, NULL};
    list_view_of(self, &v);

    if (other->type == BSharp_Number) {
        size_t n = 0;
        BSharpValue** els =
            mul_elements_keep(v.elements, v.size, other, &n);
        BSharpValue* res = wrap_container(self, els, n);
        free(els);
        return bsharp_success(res);
    }

    if (is_list_like(other)) {
        list_view ov = {NULL, 0, NULL};
        list_view_of(other, &ov);
        if (v.size != ov.size) {
            return fail_code(self, "RUN111");
        }
        BSharpValue** els =
            (BSharpValue**)malloc(v.size * sizeof(BSharpValue*));
        if (!els && v.size > 0) exit(1);
        for (size_t i = 0; i < v.size; i++) {
            ReturnStatement r = mul_core(v.elements[i], ov.elements[i]);
            els[i] = r.error ? v.elements[i] : r.value;
        }
        BSharpValue* res = wrap_container(self, els, v.size);
        free(els);
        return bsharp_success(res);
    }

    BSharpParam p = BS_PARAM("type_name", value_class_name(other));
    if (self->type == BSharp_Array) {
        return bsharp_failure(
            "RUN119", self->pos_start, self->pos_end, &p, 1);
    }
    return bsharp_failure(
        "RUN112", self->pos_start, self->pos_end, &p, 1);
}

/* The `a.multiplication(b)` method dispatch (no reversed retry - the
 * interpreter only retries at the binary-node level). */
static ReturnStatement mul_core(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Number) {
        if (other->type == BSharp_Number) {
            BSharpNumber out;
            if (bs_num_mul(self->as.num, other->as.num, &out) != BS_NUM_OK) {
                return fail_math(self);
            }
            return bsharp_success(__create_number(out));
        }
        if (is_list_like(other)) {
            return mul_container(other, self);
        }
        return fail_op(self, "multiplication");
    }
    if (self->type == BSharp_String) {
        return string_mul(self, other);
    }
    if (is_list_like(self)) {
        return mul_container(self, other);
    }
    return fail_op(self, "multiplication");
}

/* TOKEN_MUL with the interpreter's reversed retry: any error from
 * `left * right` is retried as `right * left` when the right operand
 * defines _reversed_multiplication (String, List, Array), and the
 * retry's outcome REPLACES the first. */
ReturnStatement __multiplication(
    BSharpValue* self, BSharpValue* other) {
    ReturnStatement res = mul_core(self, other);
    if (res.error &&
        (other->type == BSharp_String || is_list_like(other))) {
        res = mul_core(other, self);
    }
    return res;
}

/* Element-wise `/` with Python's Fix 5: RUN100 is a hard error and
 * propagates (at the element's own position), everything else that
 * refuses is silently kept so the size is preserved. */
static ReturnStatement div_elements(
    BSharpValue* self, BSharpValue** src, size_t n,
    BSharpValue* other) {
    BSharpValue** els = (BSharpValue**)malloc(n * sizeof(BSharpValue*));
    if (!els && n > 0) exit(1);
    for (size_t i = 0; i < n; i++) {
        ReturnStatement r = div_core(src[i], other);
        if (r.error) {
            if (strcmp(r.error->error_code, "RUN100") == 0) {
                free(els);
                return r;
            }
            els[i] = src[i];
        } else {
            els[i] = r.value;
        }
    }
    BSharpValue* res = wrap_container(self, els, n);
    free(els);
    return bsharp_success(res);
}

/* List.division / Array.division bodies. */
static ReturnStatement div_container(
    BSharpValue* self, BSharpValue* other) {
    if (other->type == BSharp_Number) {
        if (num_is_zero(other->as.num)) {
            return fail_code(self, "RUN100");
        }
        list_view v = {NULL, 0, NULL};
        list_view_of(self, &v);
        return div_elements(self, v.elements, v.size, other);
    }
    if (self->type == BSharp_Array) {
        return fail_code(self, "RUN120");
    }
    if (is_list_like(other)) {
        return fail_code(self, "RUN113");
    }
    BSharpParam p = BS_PARAM("type_name", value_class_name(other));
    return bsharp_failure(
        "RUN114", self->pos_start, self->pos_end, &p, 1);
}

static ReturnStatement div_core(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Number) {
        if (other->type != BSharp_Number) return fail_op(self, "division");
        if (num_is_zero(other->as.num)) return fail_code(self, "RUN100");
        BSharpNumber out;
        if (bs_num_true_div(self->as.num, other->as.num, &out) != BS_NUM_OK) {
            return fail_math(self);
        }
        return bsharp_success(__create_number(out));
    }
    if (is_list_like(self)) {
        return div_container(self, other);
    }
    return fail_op(self, "division");
}

ReturnStatement __division(BSharpValue* self, BSharpValue* other) {
    return div_core(self, other);
}

/* '%' - C-style truncated integer division. */
ReturnStatement __int_division(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Number && other->type == BSharp_Number) {
        if (!bs_num_is_int(self->as.num) || !bs_num_is_int(other->as.num)) {
            return fail_code(self, "RUN101");
        }
        if (num_is_zero(other->as.num)) return fail_code(self, "RUN100");
        BSharpNumber out;
        if (bs_num_idiv(self->as.num, other->as.num, &out) != BS_NUM_OK) {
            return fail_math(self);
        }
        return bsharp_success(__create_number(out));
    }
    return fail_op(self, "division");
}

/* '~' - C-style remainder, sign of the dividend. */
ReturnStatement __modulo_division(BSharpValue* self, BSharpValue* other) {
    if (self->type != BSharp_Number) return fail_op(self, "modulo");
    if (other->type != BSharp_Number) return fail_code(self, "RUN102");
    if (!bs_num_is_int(self->as.num) || !bs_num_is_int(other->as.num)) {
        return fail_code(self, "RUN103");
    }
    if (num_is_zero(other->as.num)) return fail_code(self, "RUN104");
    BSharpNumber out;
    if (bs_num_mod(self->as.num, other->as.num, &out) != BS_NUM_OK) {
        return fail_math(self);
    }
    return bsharp_success(__create_number(out));
}

/* '^' - RUN105 for 0^-n is checked up front (the interpreter reaches
 * it through ZeroDivisionError), but infinite exponents are excluded:
 * Python evaluates 0 ** -inf to inf, which then overflows into
 * MTH001 inside bs_num_pow. BS_NUM_APPROX emits WRN002 exactly like
 * PrecisionLossWarning before returning the float approximation. */
ReturnStatement __power(BSharpValue* self, BSharpValue* other) {
    if (self->type != BSharp_Number) return fail_op(self, "power");
    if (other->type != BSharp_Number) return fail_op(self, "power");

    BSharpNumber a = self->as.num;
    BSharpNumber b = other->as.num;

    if (num_is_zero(a) && num_is_negative(b) && !num_is_infinite(b)) {
        return fail_code(self, "RUN105");
    }

    BSharpNumber out;
    BSharpNumberStatus st = bs_num_pow(a, b, &out);
    if (st == BS_NUM_OVERFLOW) return fail_math(self);
    if (st == BS_NUM_COMPLEX) return fail_code(self, "RUN106");
    if (st == BS_NUM_APPROX) {
        /* Python wraps the whole warning in try/except: a value whose
         * str() exceeds the digit limit silently skips the print. */
        if (self->pos_start && self->pos_end) {
            char* base_s = bs_num_int_strdup(a);
            char* exp_s = bs_num_int_strdup(b);
            if (base_s && exp_s) {
                BSharpParam wp[2] = {
                    BS_PARAM("base", base_s),
                    BS_PARAM("exponent", exp_s),
                };
                bsharp_print_warning(
                    "WRN002", self->pos_start, self->pos_end, wp, 2);
            }
            free(base_s);
            free(exp_s);
        }
    }
    return bsharp_success(__create_number(out));
}

/* ================= equality ================= */

ReturnStatement __is_equal(BSharpValue* self, BSharpValue* other) {
    bool eq = false;

    switch (self->type) {
        case BSharp_Number:
            if (other->type == BSharp_Number) {
                eq = bs_num_eq(self->as.num, other->as.num);
            } else if (other->type == BSharp_Bool) {
                eq = bs_num_eq(self->as.num,
                    bs_num_i64(other->as.boolean ? 1 : 0));
            }
            break;

        case BSharp_Bool:
            if (other->type == BSharp_Number) {
                eq = bs_num_eq(
                    bs_num_i64(self->as.boolean ? 1 : 0), other->as.num);
            } else if (other->type == BSharp_Bool) {
                eq = self->as.boolean == other->as.boolean;
            }
            break;

        case BSharp_String:
            eq = other->type == BSharp_String &&
                strcmp(self->as.string, other->as.string) == 0;
            break;

        case BSharp_Empty:
            eq = other->type == BSharp_Empty;
            break;

        case BSharp_NaN:
            eq = false;   /* IEEE: NaN != everything, including itself */
            break;

        case BSharp_Inf:
            eq = other->type == BSharp_Inf &&
                other->as.inf_sign == self->as.inf_sign;
            break;

        case BSharp_List:
        case BSharp_Array: {
            list_view a = {NULL, 0, NULL}, b = {NULL, 0, NULL};
            if (is_list_like(other) &&
                list_view_of(self, &a) && list_view_of(other, &b) &&
                a.size == b.size) {
                eq = true;
                for (size_t i = 0; i < a.size; i++) {
                    ReturnStatement r =
                        __is_equal(a.elements[i], b.elements[i]);
                    if (r.error || !r.value->as.boolean) {
                        eq = false;
                        break;
                    }
                }
            }
            break;
        }

        case BSharp_Tuple:
            if (other->type == BSharp_Tuple &&
                self->as.tuple.size == other->as.tuple.size) {
                eq = true;
                for (size_t i = 0; i < self->as.tuple.size; i++) {
                    ReturnStatement r = __is_equal(
                        self->as.tuple.elements[i],
                        other->as.tuple.elements[i]);
                    if (r.error || !r.value->as.boolean) {
                        eq = false;
                        break;
                    }
                }
            }
            break;

        default:
            /* Function (identity), ErrorInstance, StructDef and
             * StructInstance always compare false, even to self. */
            eq = false;
            break;
    }

    return bsharp_success(__create_boolean(eq));
}

ReturnStatement __not_equal(BSharpValue* self, BSharpValue* other) {
    ReturnStatement eq = __is_equal(self, other);
    if (eq.error) return eq;
    eq.value->as.boolean = !eq.value->as.boolean;
    return eq;
}

/* ================= ordering ================= */

typedef enum { OP_LT, OP_GT, OP_LE, OP_GE } order_op;

/* Interpreter's _order_key: only the numeric domain maps to a double;
 * NaN/strings/collections return false (comparison is false). */
static bool order_key(BSharpValue* v, double* out) {
    switch (v->type) {
        case BSharp_Number: return bs_num_order_key(v->as.num, out);
        case BSharp_Bool:   *out = v->as.boolean ? 1.0 : 0.0; return true;
        case BSharp_Inf:
            *out = v->as.inf_sign >= 0 ? INFINITY : -INFINITY;
            return true;
        default:            return false;
    }
}

static ReturnStatement order_cmp(
    BSharpValue* self, BSharpValue* other, order_op op) {
    bool r = false;

    if (self->type == BSharp_String && other->type == BSharp_String) {
        int c = strcmp(self->as.string, other->as.string);
        r = (op == OP_LT) ? (c < 0)
          : (op == OP_GT) ? (c > 0)
          : (op == OP_LE) ? (c <= 0) : (c >= 0);
    } else if (self->type == BSharp_Number ||
               self->type == BSharp_Bool ||
               self->type == BSharp_Inf) {
        double a, b;
        if (order_key(self, &a) && order_key(other, &b)) {
            /* IEEE: any comparison involving NaN yields false */
            r = (op == OP_LT) ? (a < b)
              : (op == OP_GT) ? (a > b)
              : (op == OP_LE) ? (a <= b) : (a >= b);
        }
    }

    return bsharp_success(__create_boolean(r));
}

ReturnStatement __less_than(BSharpValue* self, BSharpValue* other) {
    return order_cmp(self, other, OP_LT);
}

ReturnStatement __greater_than(BSharpValue* self, BSharpValue* other) {
    return order_cmp(self, other, OP_GT);
}

ReturnStatement __less_than_equal(BSharpValue* self, BSharpValue* other) {
    return order_cmp(self, other, OP_LE);
}

ReturnStatement __greater_than_equal(BSharpValue* self, BSharpValue* other) {
    return order_cmp(self, other, OP_GE);
}

/* ================= logic ================= */

ReturnStatement __and_op(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Bool) {
        if (other->type == BSharp_Bool) {
            return bsharp_success(__create_boolean(
                self->as.boolean && other->as.boolean));
        }
        return bsharp_failure(
            "CMP002", self->pos_start, self->pos_end, NULL, 0);
    }
    return fail_op(self, "and");
}

ReturnStatement __or_op(BSharpValue* self, BSharpValue* other) {
    if (self->type == BSharp_Bool) {
        if (other->type == BSharp_Bool) {
            return bsharp_success(__create_boolean(
                self->as.boolean || other->as.boolean));
        }
        return bsharp_failure(
            "CMP003", self->pos_start, self->pos_end, NULL, 0);
    }
    return fail_op(self, "or");
}

ReturnStatement __not_op(BSharpValue* self) {
    if (self->type == BSharp_Bool) {
        return bsharp_success(__create_boolean(!self->as.boolean));
    }
    return fail_op(self, "not");
}

bool __is_truthy(BSharpValue* self) {
    switch (self->type) {
        case BSharp_Number:    return !num_is_zero(self->as.num);
        case BSharp_Bool:      return self->as.boolean;
        case BSharp_String:    return self->as.string[0] != '\0';
        case BSharp_List:      return self->as.list.size > 0;
        case BSharp_Array:     return self->as.array.list_data.size > 0;
        case BSharp_Tuple:     return self->as.tuple.size > 0;
        case BSharp_Inf:       return true;
        case BSharp_Function:  return true;
        case BSharp_StructInstance: return true;
        /* Empty, NaN, ErrorInstance and StructDefinition are falsy */
        default:               return false;
    }
}

/* ================= unary ================= */

ReturnStatement __negate(
    BSharpValue* operand,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end
) {
    if (operand->type == BSharp_Inf) {
        BSharpValue* res = __create_inf(-operand->as.inf_sign);
        return bsharp_success(res);
    }
    if (operand->type == BSharp_Number ||
        is_list_like(operand)) {
        BSharpValue* minus_one = __create_number_i64(-1);
        return mul_core(operand, minus_one);
    }
    BSharpParam p = BS_PARAM("type_name", value_class_name(operand));
    return bsharp_failure(
        "RUN003", pos_start, pos_end, &p, 1);
}

ReturnStatement __require_int(
    BSharpValue* value,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end,
    const char* label,
    int64_t* out
) {
    if (value->type != BSharp_Number || value->as.num.kind == BS_NUM_FLOAT) {
        BSharpParam p = BS_PARAM("label", label);
        return bsharp_failure(
            "RUN021", pos_start, pos_end, &p, 1);
    }
    if (value->as.num.kind == BS_NUM_INT64) {
        *out = value->as.num.as.i;
    } else {
        /* BIG: always out of range for any real container; clamp so
         * the bounds check reports RUN011/RUN110 like Python does. */
        *out = value->as.num.as.big->sign < 0 ? INT64_MIN : INT64_MAX;
    }
    return bsharp_success(NULL);
}

/* ================= index reads ================= */

/* RUN110 {index, length}: the index parameter is rendered from the
 * ORIGINAL number (Python puts the raw int into the message). When
 * str(int) would exceed the 4300-digit limit Python's Error.__init__
 * falls back to the raw template - mirrored by params = NULL. */
static ReturnStatement fail_index_oob(
    BSharpValue* self, BSharpNumber index, size_t len) {
    char* idx_s = bs_num_int_strdup(index);
    if (!idx_s) {
        return bsharp_failure(
            "RUN110", self->pos_start, self->pos_end, NULL, 0);
    }
    char len_buf[32];
    snprintf(len_buf, sizeof(len_buf), "%llu",
             (unsigned long long)len);
    BSharpParam params[2] = {
        BS_PARAM("index", idx_s),
        BS_PARAM("length", len_buf),
    };
    ReturnStatement r = bsharp_failure(
        "RUN110", self->pos_start, self->pos_end, params, 2);
    free(idx_s);
    return r;
}

ReturnStatement __get_element(
    BSharpValue* container,
    BSharpValue* index_val,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end
) {
    if (container->type == BSharp_Tuple) {
        int64_t i;
        ReturnStatement r = __require_int(
            index_val, pos_start, pos_end, "Index", &i);
        if (r.error) return r;
        int64_t n = (int64_t)container->as.tuple.size;
        if (i < 0) i += n;
        if (i < 0 || i >= n) {
            return bsharp_failure("RUN011", pos_start, pos_end, NULL, 0);
        }
        BSharpValue* el = container->as.tuple.elements[i];
        /* Interpreter mutates the STORED element's position in place:
         * element.set_context(...).set_pos(node.pos_start, node.pos_end) */
        el->pos_start = pos_start;
        el->pos_end = pos_end;
        return bsharp_success(el);
    }

    if (is_list_like(container)) {
        int64_t i;
        ReturnStatement r = __require_int(
            index_val, pos_start, pos_end, "Index", &i);
        if (r.error) return r;
        list_view v = {NULL, 0, NULL};
        list_view_of(container, &v);
        int64_t n = v.size > (size_t)INT64_MAX
            ? INT64_MAX : (int64_t)v.size;
        if (i < 0) i += n;
        if (i < 0 || i >= n) {
            return bsharp_failure("RUN011", pos_start, pos_end, NULL, 0);
        }
        BSharpValue* el = v.elements[i];
        el->pos_start = pos_start;
        el->pos_end = pos_end;
        return bsharp_success(el);
    }

    if (container->type == BSharp_String) {
        int64_t i;
        ReturnStatement r = __require_int(
            index_val, pos_start, pos_end, "Index", &i);
        if (r.error) return r;
        int64_t n = (int64_t)utf8_count(container->as.string);
        if (i < 0) i += n;
        if (i < 0 || i >= n) {
            return bsharp_failure("RUN011", pos_start, pos_end, NULL, 0);
        }
        const char* p = utf8_nth(container->as.string, i);
        char buf[5];
        size_t len = utf8_seq_len(p);
        memcpy(buf, p, len);
        buf[len] = '\0';
        return bsharp_success(__create_string(buf));
    }

    return bsharp_failure("RUN012", pos_start, pos_end, NULL, 0);
}

/* ================= array validation ================= */

static const char* element_class_name(BSharpType t) {
    switch (t) {
        case BSharp_Number: return "Number";
        case BSharp_String: return "String";
        case BSharp_Bool:   return "Boolean";
        case BSharp_Empty:  return "Empty";
        case BSharp_Inf:    return "Inf";
        case BSharp_NaN:    return "NaN";
        default:            return "Value";
    }
}

/* Array._type_spelling: the annotation spelling when known,
 * otherwise `Element` + `[]` per depth level. */
static char* array_type_spelling(BSharpValue* arr) {
    if (arr->as.array.type_name) return strdup(arr->as.array.type_name);
    const char* base = element_class_name(arr->as.array.element_type);
    size_t depth = (size_t)(arr->as.array.depth > 0 ? arr->as.array.depth : 1);
    size_t need = strlen(base) + depth * 2 + 1;
    char* s = (char*)malloc(need);
    if (!s) exit(1);
    strcpy(s, base);
    for (size_t i = 0; i < depth; i++) strcat(s, "[]");
    return s;
}

/* Array._validate_element: strict depth-aware check (RUN115-RUN118
 * reported at the ARRAY's position, like self.pos_* in Python). */
static ReturnStatement array_validate(
    BSharpValue* arr, BSharpValue* el, int level) {
    int depth = arr->as.array.depth;
    char* expect = array_type_spelling(arr);
    ReturnStatement res;

    if (el->type == BSharp_Empty) {
        if (arr->as.array.element_type == BSharp_Empty) {
            free(expect);
            return bsharp_success(NULL);
        }
        BSharpParam p = BS_PARAM("expected_type", expect);
        res = bsharp_failure(
            level == 1 ? "RUN115" : "RUN116",
            arr->pos_start, arr->pos_end, &p, 1);
        free(expect);
        return res;
    }

    if (level >= depth) {
        if (el->type == arr->as.array.element_type) {
            free(expect);
            return bsharp_success(NULL);
        }
        BSharpParam params[2] = {
            BS_PARAM("expected_type", expect),
            BS_PARAM("actual_type", value_class_name(el)),
        };
        res = bsharp_failure(
            level == 1 ? "RUN118" : "RUN117",
            arr->pos_start, arr->pos_end, params, 2);
        free(expect);
        return res;
    }

    if (!is_list_like(el)) {
        BSharpParam params[2] = {
            BS_PARAM("expected_type", expect),
            BS_PARAM("actual_type", value_class_name(el)),
        };
        res = bsharp_failure(
            level == 1 ? "RUN118" : "RUN117",
            arr->pos_start, arr->pos_end, params, 2);
        free(expect);
        return res;
    }

    list_view v = {NULL, 0, NULL};
    list_view_of(el, &v);
    for (size_t i = 0; i < v.size; i++) {
        ReturnStatement r = array_validate(arr, v.elements[i], level + 1);
        if (r.error) {
            free(expect);
            return r;
        }
    }
    free(expect);
    return bsharp_success(NULL);
}

/* Independent typed row of depth-1 built from `elements` (pointers are
 * taken over, matching Python's `list(src.list_of_elements)`). Row
 * type_name stays NULL so _type_spelling recomputes `Element[]`. */
static BSharpValue* array_make_row(
    BSharpValue* arr, BSharpValue** elements, size_t n) {
    BSharpValue* row = __create_array(
        arr->as.array.element_type,
        arr->as.array.depth - 1,
        NULL,
        n);
    for (size_t i = 0; i < n; i++) {
        row->as.array.list_data.elements[i] = elements[i];
    }
    row->as.array.list_data.size = n;
    row->pos_start = arr->pos_start;
    row->pos_end = arr->pos_end;
    row->context = arr->context;
    return row;
}

/* Array._coerce_row + _prepare_stored: normalise a validated row
 * before storage so nested rows always carry the array's own type. */
static BSharpValue* array_prepare_stored(
    BSharpValue* arr, BSharpValue* el) {
    if (arr->as.array.depth >= 2 && is_list_like(el)) {
        if (el->type == BSharp_Array &&
            el->as.array.element_type == arr->as.array.element_type &&
            el->as.array.depth == arr->as.array.depth - 1) {
            return __copy_element(el);
        }
        if (el->type == BSharp_List) {
            BSharpValue* src = __copy_element(el);
            return array_make_row(
                arr, src->as.list.elements, src->as.list.size);
        }
        /* Wrong-shape Array: Python takes its elements directly
         * (shallow), so aliasing matches the interpreter. */
        if (el->type == BSharp_Array) {
            return array_make_row(
                arr,
                el->as.array.list_data.elements,
                el->as.array.list_data.size);
        }
    }
    return el;
}

/* Array.assign_at padding values (depth-1 type defaults). */
static BSharpValue* array_default(BSharpValue* arr) {
    BSharpValue* d;
    switch (arr->as.array.element_type) {
        case BSharp_Number: d = __create_number_i64(0); break;
        case BSharp_String: d = __create_string(""); break;
        case BSharp_Bool:   d = __create_boolean(false); break;
        default:            d = __create_empty(); break;
    }
    d->pos_start = arr->pos_start;
    d->pos_end = arr->pos_end;
    d->context = arr->context;
    return d;
}

/* ================= index writes ================= */

/* List.assign_at: MOD001 first, then the element copy, then the
 * negative wrap / dynamic growth (RUN110 at the LIST's position). */
static ReturnStatement list_assign_at(
    BSharpValue* container,
    BSharpNumber index,
    int64_t i,
    BSharpValue* el
) {
    list_view v = {NULL, 0, NULL};
    list_view_of(container, &v);
    if (*v.is_const) return fail_code(container, "MOD001");
    if (is_list_like(el)) el = __copy_element(el);

    int64_t n = v.size > (size_t)INT64_MAX ? INT64_MAX : (int64_t)v.size;
    if (i < 0) i += n;
    if (i < 0) return fail_index_oob(container, index, v.size);

    if (i < n) {
        v.elements[i] = el;
        return bsharp_success(NULL);
    }
    while ((int64_t)v.size < i) {
        BSharpValue* pad = __create_empty();
        pad->pos_start = container->pos_start;
        pad->pos_end = container->pos_end;
        pad->context = container->context;
        list_append_slot(container, pad);
        list_view_of(container, &v);
    }
    list_append_slot(container, el);
    return bsharp_success(NULL);
}

/* Array.assign_at: validate FIRST (RUN115-118), normalise the row,
 * then MOD001, then the wrap/growth with type-default padding. */
static ReturnStatement array_assign_at(
    BSharpValue* container,
    BSharpNumber index,
    int64_t i,
    BSharpValue* el
) {
    ReturnStatement v = array_validate(container, el, 1);
    if (v.error) return v;
    if (is_list_like(el)) el = array_prepare_stored(container, el);

    list_view view = {NULL, 0, NULL};
    list_view_of(container, &view);
    if (*view.is_const) return fail_code(container, "MOD001");

    int64_t n = view.size > (size_t)INT64_MAX
        ? INT64_MAX : (int64_t)view.size;
    if (i < 0) i += n;
    if (i < 0) return fail_index_oob(container, index, view.size);

    if (i < n) {
        view.elements[i] = el;
        return bsharp_success(NULL);
    }
    while ((int64_t)view.size < i) {
        if (container->as.array.depth >= 2) {
            list_append_slot(container,
                array_make_row(container, NULL, 0));
        } else {
            list_append_slot(container, array_default(container));
        }
        list_view_of(container, &view);
    }
    list_append_slot(container, el);
    return bsharp_success(NULL);
}

ReturnStatement __set_element(
    BSharpValue* container,
    BSharpValue* index_val,
    BSharpValue* new_val,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end
) {
    if (container->type == BSharp_Tuple) {
        return bsharp_failure("RUN139", pos_start, pos_end, NULL, 0);
    }

    if (is_list_like(container)) {
        int64_t i;
        ReturnStatement r = __require_int(
            index_val, pos_start, pos_end, "Index", &i);
        if (r.error) return r;

        if (container->type == BSharp_Array) {
            r = array_assign_at(
                container, index_val->as.num, i, new_val);
        } else {
            r = list_assign_at(
                container, index_val->as.num, i, new_val);
        }
        if (r.error) return r;

        /* Python: value.set_context(context).set_pos(node...) on the
         * original RHS object (not the stored copy). */
        new_val->pos_start = pos_start;
        new_val->pos_end = pos_end;
        return bsharp_success(new_val);
    }

    if (container->type == BSharp_String) {
        return bsharp_failure("RUN013", pos_start, pos_end, NULL, 0);
    }
    return bsharp_failure("RUN014", pos_start, pos_end, NULL, 0);
}

/* ================= struct definitions =================
 * The C-side struct model (field list + bound methods) is the IR-era
 * replacement for Python's environment-based StructInstance. Codes
 * that have a real interpreter counterpart use it (RUN097 / RUN098 /
 * RUN010 / RUN014 / MOD003); the two C-only guards keep their legacy
 * codes and are re-audited in Stage E together with the lowering. */

BSharpValue* create_struct_definition(
    const char* name,
    const char** field_names,
    size_t field_count,
    BSharpMethod* methods,
    size_t method_count
) {
    BSharpValue* val = __allocate_base_value(BSharp_StructDef);

    BSharpStructDef* def =
        (BSharpStructDef*)malloc(sizeof(BSharpStructDef));
    if (!def) exit(1);

    def->name = strdup(name ? name : "");
    def->field_count = field_count;
    def->field_names = NULL;
    if (field_count > 0) {
        def->field_names = (char**)malloc(field_count * sizeof(char*));
        if (!def->field_names) exit(1);
        for (size_t i = 0; i < field_count; i++) {
            def->field_names[i] = strdup(field_names[i]);
        }
    }

    def->method_count = method_count;
    def->methods = NULL;
    if (method_count > 0) {
        def->methods =
            (BSharpMethod*)malloc(method_count * sizeof(BSharpMethod));
        if (!def->methods) exit(1);
        for (size_t i = 0; i < method_count; i++) {
            def->methods[i].name = strdup(methods[i].name);
            def->methods[i].function_ptr = methods[i].function_ptr;
            def->methods[i].param_count = methods[i].param_count;
            def->methods[i].param_names = NULL;
            if (methods[i].param_count > 0) {
                def->methods[i].param_names = (char**)malloc(
                    methods[i].param_count * sizeof(char*));
                if (!def->methods[i].param_names) exit(1);
                for (size_t j = 0; j < methods[i].param_count; j++) {
                    def->methods[i].param_names[j] =
                        strdup(methods[i].param_names[j]);
                }
            }
        }
    }

    val->as.struct_data = def;
    return val;
}

ReturnStatement bsharp_instantiate_struct(
    BSharpValue* struct_def_val,
    BSharpValue** initial_values,
    size_t val_count
) {
    if (!struct_def_val || struct_def_val->type != BSharp_StructDef) {
        BSharpParam p = BS_PARAM("type_name",
            struct_def_val ? value_class_name(struct_def_val) : "NoneType");
        return bsharp_failure(
            "RUN098",
            struct_def_val ? struct_def_val->pos_start : NULL,
            struct_def_val ? struct_def_val->pos_end : NULL,
            &p, 1);
    }

    BSharpStructDef* def =
        (BSharpStructDef*)struct_def_val->as.struct_data;

    /* TODO(Stage E): Python never pre-checks struct arity (instantiate
     * runs member nodes), so this C-only guard has no interpreter code
     * to mirror yet - pick or add a catalog entry then. */
    if (val_count != def->field_count) {
        return bsharp_failure(
            "RUN103",
            struct_def_val->pos_start,
            struct_def_val->pos_end,
            NULL, 0);
    }

    BSharpStructInstance* inst =
        (BSharpStructInstance*)malloc(sizeof(BSharpStructInstance));
    if (!inst) exit(1);

    inst->def = def;
    inst->field_count = def->field_count;
    inst->field_names = NULL;
    inst->field_values = NULL;
    if (def->field_count > 0) {
        inst->field_names =
            (char**)malloc(def->field_count * sizeof(char*));
        inst->field_values =
            (BSharpValue**)malloc(def->field_count * sizeof(BSharpValue*));
        if (!inst->field_names || !inst->field_values) exit(1);
    }

    for (size_t i = 0; i < def->field_count; i++) {
        inst->field_names[i] = strdup(def->field_names[i]);
        inst->field_values[i] = __copy_element(initial_values[i]);
    }

    BSharpValue* res_val = __allocate_base_value(BSharp_StructInstance);
    res_val->pos_start = struct_def_val->pos_start;
    res_val->pos_end = struct_def_val->pos_end;
    res_val->context = struct_def_val->context;
    res_val->as.struct_data = inst;

    return bsharp_success(res_val);
}

ReturnStatement bsharp_get_property(
    BSharpValue* instance,
    const char* property_name
) {
    if (!instance || instance->type != BSharp_StructInstance) {
        /* Interpreter path for non-structs: RUN010 {property, type} */
        BSharpParam params[2] = {
            BS_PARAM("property", property_name),
            BS_PARAM("type_name",
                instance ? value_class_name(instance) : "NoneType"),
        };
        return bsharp_failure(
            "RUN010",
            instance ? instance->pos_start : NULL,
            instance ? instance->pos_end : NULL,
            params, 2);
    }

    BSharpStructInstance* inst =
        (BSharpStructInstance*)instance->as.struct_data;

    for (size_t i = 0; i < inst->field_count; i++) {
        if (strcmp(inst->field_names[i], property_name) == 0) {
            return bsharp_success(inst->field_values[i]);
        }
    }

    for (size_t i = 0; i < inst->def->method_count; i++) {
        if (strcmp(inst->def->methods[i].name, property_name) == 0) {
            BSharpBoundMethod* bound =
                (BSharpBoundMethod*)malloc(sizeof(BSharpBoundMethod));
            if (!bound) exit(1);

            bound->instance = instance;
            bound->function_ptr = inst->def->methods[i].function_ptr;
            bound->param_count = inst->def->methods[i].param_count;

            BSharpValue* method_val =
                __allocate_base_value(BSharp_Function);
            method_val->pos_start = instance->pos_start;
            method_val->pos_end = instance->pos_end;
            method_val->context = instance->context;
            method_val->as.function_ptr = bound;

            return bsharp_success(method_val);
        }
    }

    BSharpParam params[2] = {
        BS_PARAM("property", property_name),
        BS_PARAM("struct_name", inst->def->name),
    };
    return bsharp_failure(
        "RUN097",
        instance->pos_start,
        instance->pos_end,
        params, 2);
}

ReturnStatement bsharp_set_property(
    BSharpValue* instance,
    const char* property_name,
    BSharpValue* new_value
) {
    if (instance && instance->type == BSharp_StructDef) {
        BSharpStructDef* def = (BSharpStructDef*)instance->as.struct_data;
        BSharpParam p = BS_PARAM("name", def ? def->name : "struct");
        return bsharp_failure(
            "MOD003", instance->pos_start, instance->pos_end, &p, 1);
    }

    if (!instance || instance->type != BSharp_StructInstance) {
        /* Interpreter: any other assignment target is RUN014 */
        return bsharp_failure(
            "RUN014",
            instance ? instance->pos_start : NULL,
            instance ? instance->pos_end : NULL,
            NULL, 0);
    }

    BSharpStructInstance* inst =
        (BSharpStructInstance*)instance->as.struct_data;

    for (size_t i = 0; i < inst->field_count; i++) {
        if (strcmp(inst->field_names[i], property_name) == 0) {
            /* environment.assign stores the object as-is (no copy) */
            inst->field_values[i] = new_value;
            return bsharp_success(new_value);
        }
    }

    BSharpParam params[2] = {
        BS_PARAM("property", property_name),
        BS_PARAM("struct_name", inst->def->name),
    };
    return bsharp_failure(
        "RUN097",
        instance->pos_start,
        instance->pos_end,
        params, 2);
}

BSharpValue* bsharp_error_to_value(BSharp_Error* error) {
    if (!error) return __create_empty();

    BSharpValue* val = __allocate_base_value(BSharp_ErrorInstance);
    val->pos_start = error->pos_start;
    val->pos_end = error->pos_end;
    val->as.error_inst = error;
    return val;
}

