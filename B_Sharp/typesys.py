# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# The code is guarded and licensed under the GPLv3 License.
# ----------------------------------------------------------------
# Module: typesys.py: Single source of truth for B_Sharp data types.
#
# Every type rule lives here exactly once and is shared by both
# execution routes:
#   * the tree-walking interpreter (simulated LLVM semantics over
#     Python payloads), and
#   * the LLVM compiler backend (real i8/i16/i32/i64/float/double/ptr
#     types plus the %BSValue tagged-union ABI).
#
# Fixed-width integers wrap with two's-complement semantics (exactly
# like LLVM's default `add`/`sub`/`mul`). Float32 results are rounded
# through IEEE-754 binary32 after every operation.

import math
import struct

# Type kinds
INT = "int"
FLOAT = "float"
BOOL = "bool"
CHAR = "char"
STRING = "string"
EMPTY = "empty"
NAN = "nan"
INF = "inf"
LIST = "list"
ARRAY = "array"
TUPLE = "tuple"
FUNCTION = "function"
STRUCT = "struct"
ERROR = "error"


class BSharpType:
    """
    Descriptor for one B# data type (name, width, LLVM type,
    ABI tag).
    """

    __slots__ = (
        "name",
        "kind",
        "bits",
        "signed",
        "llvm",
        "rank",
        "tag",
    )

    def __init__(
        self,
        name,
        kind,
        bits=0,
        signed=True,
        llvm="ptr",
        rank=0,
        tag=0,
    ):
        self.name = name
        self.kind = kind
        self.bits = bits
        self.signed = signed
        self.llvm = llvm
        self.rank = rank
        self.tag = tag

    def __repr__(self):
        return f"BSharpType({self.name})"


TYPES = {
    "Short": BSharpType("Short", INT, bits=8, signed=True, llvm="i8", rank=1, tag=1),
    "Single": BSharpType(
        "Single", INT, bits=16, signed=True, llvm="i16", rank=2, tag=2
    ),
    "Integer": BSharpType(
        "Integer", INT, bits=32, signed=True, llvm="i32", rank=3, tag=3
    ),
    "Long": BSharpType("Long", INT, bits=64, signed=True, llvm="i64", rank=4, tag=4),
    "Float": BSharpType("Float", FLOAT, bits=32, llvm="float", rank=5, tag=5),
    "Double": BSharpType("Double", FLOAT, bits=64, llvm="double", rank=6, tag=6),
    "Bool": BSharpType("Bool", BOOL, bits=1, signed=False, llvm="i1", rank=0, tag=7),
    "Char": BSharpType("Char", CHAR, bits=8, signed=False, llvm="i8", rank=0, tag=8),
    "String": BSharpType("String", STRING, llvm="ptr", rank=0, tag=9),
    "Empty": BSharpType("Empty", EMPTY, llvm="i8", rank=0, tag=10),
    "NaN": BSharpType("NaN", NAN, llvm="double", rank=0, tag=11),
    "Inf": BSharpType("Inf", INF, llvm="double", rank=0, tag=12),
    "List": BSharpType("List", LIST, llvm="ptr", rank=0, tag=13),
    "Array": BSharpType("Array", ARRAY, llvm="ptr", rank=0, tag=14),
    "Tuple": BSharpType("Tuple", TUPLE, llvm="ptr", rank=0, tag=15),
    "Function": BSharpType("Function", FUNCTION, llvm="ptr", rank=0, tag=16),
    "Struct": BSharpType("Struct", STRUCT, llvm="ptr", rank=0, tag=17),
    "Error": BSharpType("Error", ERROR, llvm="ptr", rank=0, tag=18),
}

INT_TYPE_NAMES = ("Short", "Single", "Integer", "Long")
FLOAT_TYPE_NAMES = ("Float", "Double")
NUMERIC_TYPE_NAMES = INT_TYPE_NAMES + FLOAT_TYPE_NAMES

INT_RANGES = {
    name: (-(1 << (TYPES[name].bits - 1)), (1 << (TYPES[name].bits - 1)) - 1)
    for name in INT_TYPE_NAMES
}

DEFAULT_INT_TYPE = "Long"
DEFAULT_FLOAT_TYPE = "Double"

# Numeric literal suffixes (case-insensitive): 5i, 5s, 5b, 5L, 1.5f, 5.0D.
SUFFIX_TO_TYPE = {
    "l": "Long",
    "i": "Integer",
    "s": "Single",
    "b": "Short",
    "f": "Float",
    "d": "Double",
}

# Targets allowed for the `cast(value, Type)` conversion form.
CASTABLE_TYPES = NUMERIC_TYPE_NAMES + ("Char", "String", "Bool")


def wrap_signed(value, bits):
    """Two's-complement wrap of an integer to `bits` width (LLVM default)."""
    value = int(value)
    mod = 1 << bits
    value %= mod
    if value >= 1 << (bits - 1):
        value -= mod
    return value


def to_f32(value):
    """Round a Python float to IEEE-754 binary32 (LLVM `float` semantics)."""
    try:
        return struct.unpack("<f", struct.pack("<f", float(value)))[0]
    except OverflowError:
        return math.inf if value >= 0 else -math.inf


def f32_repr(value):
    """Shortest string that round-trips through binary32.

    Mirrors what a C runtime printing an LLVM `float` must produce so the
    interpreter and compiled binaries render identically.
    """
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "-inf" if value < 0 else "inf"
    for precision in range(1, 10):
        text = format(value, f".{precision}g")
        try:
            if to_f32(float(text)) == value:
                return text
        except (OverflowError, ValueError):
            continue
    return format(value, ".9g")


def fits_int(type_name, value):
    """True when a Python int fits the range of a fixed-width int type."""
    low, high = INT_RANGES[type_name]
    return low <= int(value) <= high


def normalize_payload(type_name, raw):
    """Fold a raw Python payload into the canonical value for a type."""
    kind = TYPES[type_name].kind
    if kind == INT:
        return wrap_signed(raw, TYPES[type_name].bits)
    if kind == FLOAT:
        value = float(raw)
        if type_name == "Float":
            return to_f32(value)
        return value
    if kind == BOOL:
        return bool(raw)
    if kind == CHAR:
        text = str(raw)
        return text[0] if text else "\0"
    return raw


def promote(name_a, name_b):
    """Result type of a binary numeric operation (dynamic promotion).

    int + int   -> wider width (Short < Single < Integer < Long)
    float + float -> wider (Float < Double)
    int + float -> the float type, except Long + Float -> Double
                   (an f32 mantissa cannot hold 64-bit integers)
    """
    if name_a == name_b:
        return name_a
    kind_a = TYPES[name_a].kind
    kind_b = TYPES[name_b].kind
    if kind_a == INT and kind_b == INT:
        return name_a if TYPES[name_a].bits >= TYPES[name_b].bits else name_b
    if kind_a == FLOAT and kind_b == FLOAT:
        return "Double"
    if kind_a == INT and kind_b == FLOAT:
        int_name, float_name = name_a, name_b
    elif kind_a == FLOAT and kind_b == INT:
        int_name, float_name = name_b, name_a
    else:
        return None
    if float_name == "Double":
        return "Double"
    # float side is Float: only a 64-bit integer outgrows it.
    return "Double" if int_name == "Long" else "Float"


def convert_numeric(payload, from_kind, target_name):
    """LLVM-equivalent numeric conversion (used by `cast` and builtins).

    int -> int wraps (trunc); float -> float rounds; int -> float converts
    (sitofp rounding); float -> int truncates toward zero then wraps
    (NaN -> 0, infinities clamp to the type range edge before wrapping).
    """
    target = TYPES[target_name]
    if target.kind == INT:
        bits = target.bits
        if from_kind == FLOAT:
            value = float(payload)
            if math.isnan(value):
                return 0
            if math.isinf(value):
                low, high = INT_RANGES[target_name]
                return high if value > 0 else low
            return wrap_signed(math.trunc(value), bits)
        return wrap_signed(int(payload), bits)
    if target.kind == FLOAT:
        try:
            value = float(payload)
        except OverflowError:
            value = math.inf if payload >= 0 else -math.inf
        if target_name == "Float":
            return to_f32(value)
        return value
    raise ValueError(f"not a numeric target: {target_name}")


def context_literal(py_value, is_float, target_name):
    """Type a numeric literal against a declared type (annotation narrowing).

    Kind-strict: an int literal narrows only into an int type, a float
    literal only into a float type. Cross-kind literals are rejected even
    when the value would convert exactly — use `cast` or a correctly
    suffixed literal instead.

    Returns (payload, None) on success or (None, reason) where reason is
    "kind" (int/float kind mismatch) or "range" (out of range).
    Rules:
      int literal -> int type:      allowed iff it fits, else "range"
      int literal -> float type:    rejected ("kind")
      float literal -> float type:  always allowed (fptrunc rounding)
      float literal -> int type:    rejected ("kind")
    """
    target = TYPES[target_name]
    if target.kind == INT:
        if is_float:
            return None, "kind"
        value = int(py_value)
        if fits_int(target_name, value):
            return value, None
        return None, "range"
    if target.kind == FLOAT:
        if not is_float:
            return None, "kind"
        try:
            value = float(py_value)
        except OverflowError:
            value = math.inf if py_value >= 0 else -math.inf
        if target_name == "Float":
            value = to_f32(value)
        return value, None
    return None, "range"
