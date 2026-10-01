# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# The code is guarded and licensed under the GPLv3 License.
# ----------------------------------------------------------------
# Module: instances.py: All B_Sharp datatypes and environment
# needed-to-define keyword instances (functions, variables, etc.).

from __future__ import annotations
from B_Sharp.Errors.errors import *
from B_Sharp.tokens import TYPE_KEYWORDS

import math
import re
import sys
from fractions import Fraction

from B_Sharp import typesys as _typesys

MAX_AUTO_GROW_INDEX = 1_000_000

_ARRAY_TYPE_RE = re.compile(
    r"^(?P<base>[A-Za-z_][A-Za-z0-9_]*)(?:\[\])+$",
)


class Value:
    """
    Base class for all B_Sharp runtime values.

    Provides shared infrastructure (set_pos, set_context) and safe default
    implementations for every operation. Subclasses only override the
    operations they actually support - undefined operations automatically
    yield a clean RunTimeError instead of crashing the interpreter.
    """

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def _to_number(self, other):
        # Legacy helper kept for the Boolean <-> numeric equality paths:
        # Booleans coerce to a Long holding 1/0, everything else passes
        # through untouched.
        if isinstance(other, Boolean):
            return Long(1 if other.value else 0)
        return other

    def _op_error(self, op):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "RUN099",
            {"type_name": type_spelling(self).lower(), "op": op},
        )

    def addition(self, other):
        return self._op_error("addition")

    def subtraction(self, other):
        return self._op_error("subtraction")

    def multiplication(self, other):
        return self._op_error("multiplication")

    def division(self, other):
        return self._op_error("division")

    def integer_division(self, other):
        return self._op_error("division")

    def power(self, other):
        return self._op_error("power")

    def is_equal(self, other):
        return Boolean(False), None

    def not_equal(self, other):
        return Boolean(True), None

    def less_than(self, other):
        return Boolean(False), None

    def greater_than(self, other):
        return Boolean(False), None

    def less_than_equal(self, other):
        return Boolean(False), None

    def greater_than_equal(self, other):
        return Boolean(False), None

    def and_(self, other):
        return self._op_error("and")

    def or_(self, other):
        return self._op_error("or")

    def not_(self):
        return self._op_error("not")

    def modulo_division(self, other):
        return self._op_error("modulo")

    def true_(self):
        return False


def _compare_numeric(left, right):
    """Three-way comparison over the numeric domain.

    Returns -1/0/1, or None when the operands are unordered (NaN on
    either side, per IEEE). Mixed int/float pairs compare exactly via
    Fraction so a 64-bit Long never loses precision against a Double.
    Booleans coerce to 1/0; signed infinities order beyond every finite
    value with sign awareness.
    """

    def _key(value):
        if isinstance(value, NaN):
            return None
        if isinstance(value, Inf):
            return ("inf", value.sign)
        if isinstance(value, Boolean):
            return ("int", 1 if value.value else 0)
        if isinstance(value, NumericValue):
            if isinstance(value.value, float) and math.isnan(value.value):
                return None
            if isinstance(value.value, float) and math.isinf(value.value):
                return ("inf", 1 if value.value > 0 else -1)
            if isinstance(value.value, float):
                return ("frac", Fraction(value.value))
            return ("int", int(value.value))
        return ("unknown", None)

    a = _key(left)
    b = _key(right)
    if a is None or b is None:
        return None
    if a[0] == "unknown" or b[0] == "unknown":
        return None
    if a[0] == "inf" or b[0] == "inf":
        a_rank = 1 if a[0] == "inf" else 0
        b_rank = 1 if b[0] == "inf" else 0
        if a_rank != b_rank:
            # A finite value always orders below +inf and above -inf.
            if a_rank:
                return 1 if a[1] > 0 else -1
            return -1 if b[1] > 0 else 1
        if a[1] == b[1]:
            return 0
        return -1 if a[1] < b[1] else 1
    a_val = a[1] if a[0] == "int" else a[1]
    b_val = b[1] if b[0] == "int" else b[1]
    if a_val < b_val:
        return -1
    if a_val > b_val:
        return 1
    return 0


def _numeric_order(self, other, operator):
    """Shared implementation for <, >, <=, >= over numeric operands.

    Callers pass lambdas like `lambda a, b: a < b`; they are applied to
    the three-way result (-1/0/1) against 0, so every ordering operator
    behaves correctly.
    """
    order = _compare_numeric(self, other)
    if order is None:
        return Boolean(False), None
    return Boolean(operator(order, 0)), None


class NumericValue(Value):
    """
    Base class for all LLVM-driven numeric values.

    The six concrete types mirror LLVM scalar types exactly:
    `Short` (i8), `Single` (i16), `Integer` (i32), `Long` (i64),
    `Float` (float), `Double` (double).

    Introduction:\n
    Fixed-width numeric datatypes. Integer arithmetic wraps with
    two's-complement semantics (exactly like LLVM's default `add`/`sub`/
    `mul`); Float results are rounded to IEEE-754 binary32 after every
    operation. Mixed-type expressions promote dynamically: the wider
    integer wins, any float beats any integer, and `Long + Float`
    promotes to `Double`.

    Usage:\n
    ```
    var x = 5          // Long (64-bit integer, the default)
    var y = 323.1231   // Double (64-bit float, the default)
    var z : Integer = 5
    var w = 1.5f       // Float literal via the `f` suffix

    const pi : Double = 3.14
    ```

    Assigning a value whose type differs from the declared type is an
    error unless the right-hand side is a numeric literal that converts
    cleanly; use `cast(value, Type)` for explicit conversion.
    """

    TYPE_NAME = None

    def __init__(self, type_name, value):
        spec = _typesys.TYPES[type_name]
        if spec.kind == _typesys.INT:
            payload = _typesys.wrap_signed(int(value), spec.bits)
        elif spec.kind == _typesys.FLOAT:
            payload = float(value)
            if type_name == "Float":
                payload = _typesys.to_f32(payload)
        else:
            payload = value
        self.type_name = type_name
        self.value = payload
        self.set_pos()
        self.set_context()

    @property
    def _kind(self):
        return _typesys.TYPES[self.type_name].kind

    @property
    def _is_int_kind(self):
        return self._kind == _typesys.INT

    def _payload_is_inf(self):
        return isinstance(self.value, float) and math.isinf(self.value)

    def _finish(self, target, raw, inputs_have_inf=False):
        """
        Boxes a raw Python result into the promoted result type.

        Integers wrap; floats round to binary32 for Float; a newly
        infinite float result is a math error (MTH001) unless an input
        was already infinite.
        """
        if _typesys.TYPES[target].kind == _typesys.INT:
            result = _typesys.wrap_signed(raw, _typesys.TYPES[target].bits)
            return NUMERIC_CLASSES[target](result), None
        try:
            result = float(raw)
        except OverflowError:
            return None, BSharpMathError(self.pos_start, self.pos_end)
        if target == "Float":
            result = _typesys.to_f32(result)
        if math.isinf(result) and not inputs_have_inf:
            return None, BSharpMathError(self.pos_start, self.pos_end)
        return NUMERIC_CLASSES[target](result), None

    def _promote(self, other):
        return _typesys.promote(self.type_name, other.type_name)

    def addition(self, other):
        if not isinstance(other, NumericValue):
            return self._op_error("addition")
        target = self._promote(other)
        if _typesys.TYPES[target].kind == _typesys.INT:
            return self._finish(target, int(self.value) + int(other.value))
        try:
            raw = float(self.value) + float(other.value)
        except OverflowError:
            return None, BSharpMathError(self.pos_start, self.pos_end)
        return self._finish(
            target,
            raw,
            inputs_have_inf=self._payload_is_inf() or other._payload_is_inf(),
        )

    def subtraction(self, other):
        if not isinstance(other, NumericValue):
            return self._op_error("subtraction")
        target = self._promote(other)
        if _typesys.TYPES[target].kind == _typesys.INT:
            return self._finish(target, int(self.value) - int(other.value))
        try:
            raw = float(self.value) - float(other.value)
        except OverflowError:
            return None, BSharpMathError(self.pos_start, self.pos_end)
        return self._finish(
            target,
            raw,
            inputs_have_inf=self._payload_is_inf() or other._payload_is_inf(),
        )

    def multiplication(self, other):
        if isinstance(other, NumericValue):
            target = self._promote(other)
            if _typesys.TYPES[target].kind == _typesys.INT:
                return self._finish(target, int(self.value) * int(other.value))
            try:
                raw = float(self.value) * float(other.value)
            except OverflowError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
            return self._finish(
                target,
                raw,
                inputs_have_inf=self._payload_is_inf() or other._payload_is_inf(),
            )
        if isinstance(other, (List, Array)):
            # Scalar-vector multiplication works in both directions.
            return other._reversed_multiplication(self)
        return self._op_error("multiplication")

    def division(self, other):
        """
        / - true division. int / int promotes to Double.
        """
        if not isinstance(other, NumericValue):
            return self._op_error("division")
        if other.value == 0:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN100",
            )
        target = self._promote(other)
        if _typesys.TYPES[target].kind == _typesys.INT:
            target = "Double"
        try:
            raw = float(self.value) / float(other.value)
        except OverflowError:
            return None, BSharpMathError(self.pos_start, self.pos_end)
        return self._finish(
            target,
            raw,
            inputs_have_inf=self._payload_is_inf() or other._payload_is_inf(),
        )

    def integer_division(self, other):
        """
        '%' - C-style integer division (truncates toward zero, wraps).
        """
        if not isinstance(other, NumericValue):
            return self._op_error("division")
        if not self._is_int_kind or not other._is_int_kind:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN101",
            )
        if other.value == 0:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN100",
            )
        target = self._promote(other)
        a, b = int(self.value), int(other.value)
        quotient = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            quotient = -quotient
        # MIN / -1 wraps back to MIN, like LLVM/tested x86 behavior.
        return self._finish(target, quotient)

    def modulo_division(self, other):
        """
        '~' C-style modulo (result takes the sign of the dividend).
        """
        if not isinstance(other, NumericValue):
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN102",
            )
        if not self._is_int_kind or not other._is_int_kind:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN103",
            )
        if other.value == 0:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN104",
            )
        target = self._promote(other)
        a, b = int(self.value), int(other.value)
        remainder = abs(a) % abs(b)
        if a < 0:
            remainder = -remainder
        return self._finish(target, remainder)

    def power(self, power_factor):
        if not isinstance(power_factor, NumericValue):
            return self._op_error("power")
        target = self._promote(power_factor)
        if _typesys.TYPES[target].kind == _typesys.INT:
            base, exponent = int(self.value), int(power_factor.value)
            bits = _typesys.TYPES[target].bits
            if exponent < 0:
                # Negative integer exponents produce a Double, matching
                # true-division semantics (2 ^ -1 == 0.5).
                try:
                    raw = float(base) ** exponent
                except ZeroDivisionError:
                    return None, RunTimeError(
                        self.pos_start,
                        self.pos_end,
                        "RUN105",
                    )
                except (ValueError, OverflowError):
                    return None, BSharpMathError(
                        self.pos_start,
                        self.pos_end,
                    )
                return self._finish("Double", raw)
            # Exact modular power: O(log exp), then wrap to the width.
            return self._finish(target, pow(base, exponent, 1 << bits))
        try:
            raw = float(self.value) ** float(power_factor.value)
        except ZeroDivisionError:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN105",
            )
        except (ValueError, OverflowError):
            return None, BSharpMathError(
                self.pos_start,
                self.pos_end,
            )
        except Exception:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN106",
            )
        if isinstance(raw, complex):
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN106",
            )
        return self._finish(
            target,
            raw,
            inputs_have_inf=self._payload_is_inf() or power_factor._payload_is_inf(),
        )

    def is_equal(self, other):
        if isinstance(other, (NumericValue, Boolean)):
            other = self._to_number(other)
            if not isinstance(other, NumericValue):
                return Boolean(False), None
            target = self._promote(other)
            if _typesys.TYPES[target].kind == _typesys.INT:
                return Boolean(int(self.value) == int(other.value)), None
            return Boolean(float(self.value) == float(other.value)), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, (NumericValue, Boolean)):
            other = self._to_number(other)
            if not isinstance(other, NumericValue):
                return Boolean(True), None
            target = self._promote(other)
            if _typesys.TYPES[target].kind == _typesys.INT:
                return Boolean(int(self.value) != int(other.value)), None
            return Boolean(float(self.value) != float(other.value)), None
        return Boolean(True), None

    def less_than(self, other):
        return _numeric_order(self, other, lambda a, b: a < b)

    def greater_than(self, other):
        return _numeric_order(self, other, lambda a, b: a > b)

    def less_than_equal(self, other):
        return _numeric_order(self, other, lambda a, b: a <= b)

    def greater_than_equal(self, other):
        return _numeric_order(self, other, lambda a, b: a >= b)

    def true_(self):
        return self.value != 0

    def __repr__(self):
        if self.type_name == "Float":
            return _typesys.f32_repr(self.value)
        return str(self.value)


class Short(NumericValue):
    """
    8-bit signed integer (LLVM i8).
    """

    def __init__(self, value):
        super().__init__("Short", value)


class Single(NumericValue):
    """
    16-bit signed integer (LLVM i16).
    """

    def __init__(self, value):
        super().__init__("Single", value)


class Integer(NumericValue):
    """
    32-bit signed integer (LLVM i32).
    """

    def __init__(self, value):
        super().__init__("Integer", value)


class Long(NumericValue):
    """
    64-bit signed integer (LLVM i64). Default type of integer
    literals.
    """

    def __init__(self, value):
        super().__init__("Long", value)


class Float(NumericValue):
    """
    32-bit floating point (LLVM float). Rounded to binary32
    per op.
    """

    def __init__(self, value):
        super().__init__("Float", value)


class Double(NumericValue):
    """
    64-bit floating point (LLVM double). Default type of float literals.
    """

    def __init__(self, value):
        super().__init__("Double", value)


class Boolean(Value):
    """
    A datatype representing a boolean value (true | false).

    Introduction:\n
    Booleans are atomic datatypes. They consist of two keywords: `true` and
    `false`. B-Sharp implements both keywords in its syntax.

    Usage:\n
    Booleans are associated with comparisons. If one comparison rule is added,
    a boolean type is always detected. For example:
    ```
    if (x == 4) { // A logical operator returning either true or false.
        // Expression
    }
    ```
    Booleans can be also used in variables assignments. For example:
    ```
    var boolean_example : Bool = true
    var boolean_2 = false
    const BooleanValue = true
    ```
    """

    def __init__(self, value: bool):
        self.value = value
        self.set_pos()
        self.set_context()

    def is_equal(self, other):
        if isinstance(other, (NumericValue, Boolean)):
            other_num = self._to_number(other)
            my_num = Long(1 if self.value else 0)
            return my_num.is_equal(other_num)
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, (NumericValue, Boolean)):
            other_num = self._to_number(other)
            my_num = Long(1 if self.value else 0)
            return my_num.not_equal(other_num)
        return Boolean(True), None

    def less_than(self, other):
        return _numeric_order(self, other, lambda a, b: a < b)

    def greater_than(self, other):
        return _numeric_order(self, other, lambda a, b: a > b)

    def less_than_equal(self, other):
        return _numeric_order(self, other, lambda a, b: a <= b)

    def greater_than_equal(self, other):
        return _numeric_order(self, other, lambda a, b: a >= b)

    def and_(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value and other.value), None
        return None, ComparisonError(
            self.pos_start,
            self.pos_end,
            "CMP002",
        )

    def or_(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value or other.value), None
        return None, ComparisonError(
            self.pos_start,
            self.pos_end,
            "CMP003",
        )

    def not_(self):
        return Boolean(not self.value), None

    def true_(self):
        return self.value

    def __repr__(self):
        return "true" if self.value == True else "false"


class String(Value):
    """
    A datatype representing a string of characters (String).

    Introduction:\n
    Strings are atomic datatypes holding double-quoted text. Single
    quotation marks always produce a `Char`, never a `String`.

    Usage:\n
    To declare a variable of type `String`. Do the following:
    ```
    var x = "Hello"             // Double quotation strings
    var y : String = "Hi"       // ... and type declaration
    var c : Char = 'c'          // Single quotation characters
    ```

    Strings are also associated with `.type,` `.size,` and `.length` properties.
    The `.length` and `.size` properties are identical. Indexing a string
    yields a `Char`.
    """

    def __init__(self, value: str):
        self.value = str(value)
        self.set_pos()
        self.set_context()

    def addition(self, other):
        if isinstance(other, String):
            try:
                return String(self.value + other.value), None
            except MemoryError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
        elif isinstance(other, Char):
            try:
                return String(self.value + other.value), None
            except MemoryError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
        elif isinstance(other, (NumericValue, Boolean)):
            try:
                return String(self.value + str(other)), None
            except MemoryError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
        return self._op_error("addition")

    def multiplication(self, other):
        if (
            isinstance(other, NumericValue)
            and _typesys.TYPES[other.type_name].kind == _typesys.INT
        ):
            if other.value < 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "RUN107",
                )
            try:
                return String(self.value * int(other.value)), None
            except (OverflowError, MemoryError):
                # Repeat count/result too large to represent (MTH001).
                return None, BSharpMathError(self.pos_start, self.pos_end)
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "RUN108",
        )

    def _reversed_multiplication(self, other):
        return self.multiplication(other)

    def is_equal(self, other):
        if isinstance(other, String):
            return Boolean(self.value == other.value), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, String):
            return Boolean(self.value != other.value), None
        return Boolean(True), None

    def less_than(self, other):
        if isinstance(other, String):
            return Boolean(self.value < other.value), None
        return Boolean(False), None

    def greater_than(self, other):
        if isinstance(other, String):
            return Boolean(self.value > other.value), None
        return Boolean(False), None

    def less_than_equal(self, other):
        if isinstance(other, String):
            return Boolean(self.value <= other.value), None
        return Boolean(False), None

    def greater_than_equal(self, other):
        if isinstance(other, String):
            return Boolean(self.value >= other.value), None
        return Boolean(False), None

    def true_(self):
        return len(self.value) > 0

    def __repr__(self):
        return f'"{self.value}"'


class Char(Value):
    """
    A datatype representing a single character (LLVM i8).

    Introduction:\n
    Chars are atomic datatypes produced by single-quoted literals: `'a'`
    holds exactly one character. A Char supports equality and ordering
    against other Chars, and concatenates with Strings and Chars into a
    `String`. Numeric arithmetic on a Char is an error - convert with
    `cast(c, Short)` first.

    Usage:\n
    ```
    var c = 'a'
    var s : String = "x" + c     // "xa"
    var t : String = c + 'b'     // "ab"
    ```
    """

    def __init__(self, value: str):
        text = str(value)
        self.value = text[0] if text else "\0"
        self.set_pos()
        self.set_context()

    def addition(self, other):
        if isinstance(other, Char):
            try:
                return String(self.value + other.value), None
            except MemoryError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
        if isinstance(other, String):
            try:
                return String(self.value + other.value), None
            except MemoryError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
        return self._op_error("addition")

    def _reversed_addition(self, other):
        if isinstance(other, String):
            try:
                return String(other.value + self.value), None
            except MemoryError:
                return None, BSharpMathError(self.pos_start, self.pos_end)
        return self._op_error("addition")

    def is_equal(self, other):
        if isinstance(other, Char):
            return Boolean(self.value == other.value), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, Char):
            return Boolean(self.value != other.value), None
        return Boolean(True), None

    def less_than(self, other):
        if isinstance(other, Char):
            return Boolean(self.value < other.value), None
        return Boolean(False), None

    def greater_than(self, other):
        if isinstance(other, Char):
            return Boolean(self.value > other.value), None
        return Boolean(False), None

    def less_than_equal(self, other):
        if isinstance(other, Char):
            return Boolean(self.value <= other.value), None
        return Boolean(False), None

    def greater_than_equal(self, other):
        if isinstance(other, Char):
            return Boolean(self.value >= other.value), None
        return Boolean(False), None

    def true_(self):
        return True

    def __repr__(self):
        return f"'{self.value}'"


class Empty(Value):
    """
    A datatype represnting a Null (None) Value.

    Introduction:\n
    An automic data type in B_Sharp that represents a null value. It holds
    for empty value on runtime unless later explicitly traded with a value.

    Usage:\n
    `Empty` comes with the keyword (none). Thus the most abvious usage is with
    a declaration of a variable that has `none` value:
    ```
    var x = none
    ```
    Be careful here if you want to assign a value of type empty but you give it
    an instance of another type format. That would through a `AssignmenError`
    during runtime. For example, the following code would through a
    `AssignmenError`:
    `var x : Empty = 5`

    That is because clearly (5) is not empty.

    Emptyness is either one of two things:
    1. No type is given, examples:
     - `var x`
     - `var x : Empty`
     - `const x`
     - `const x : Empty   // Be careful because (x) cannot be changed after this`
    2. Assigning to (`none`):
     - `var x = none`
     - `var x : Empty = none`
     - `const x = none`
     - `const x : Empty = none`

    However, be careful: `Empty` is a datatype whose instance is the value none.
    """

    def __init__(self):
        self.value = None
        self.set_pos()
        self.set_context()

    def is_equal(self, other):
        if isinstance(other, Empty):
            return Boolean(True), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, Empty):
            return Boolean(False), None
        return Boolean(True), None

    def true_(self):
        return False

    def __repr__(self):
        return "none"


class NaN(Value):
    """
    Not A Number (NaN).

    The `nan` keyword is a special keywords with its datatype when applications
    require a usage of a value that is not a number. Especially mathematics.
    """

    def __init__(self):
        self.set_pos()
        self.set_context()

    def is_equal(self, other):
        return Boolean(False), None

    def not_equal(self, other):
        return Boolean(True), None

    def true_(self):
        return False

    def __repr__(self):
        return "nan"


class Inf(Value):
    """
    Signed infinity.

    The `inf` keyword produces +inf; unary '-' on an infinity flips the
    sign, so -inf exists as a first-class value. Ordering follows IEEE
    rules via _order_key; equality is sign-aware.
    """

    def __init__(self, sign=1):
        self.sign = 1 if sign >= 0 else -1
        self.set_pos()
        self.set_context()

    def negated(self):
        result = Inf(-self.sign)
        result.set_pos(self.pos_start, self.pos_end)
        result.set_context(self.context)
        return result

    def is_equal(self, other):
        return Boolean(isinstance(other, Inf) and other.sign == self.sign), None

    def not_equal(self, other):
        equal, _ = self.is_equal(other)
        return Boolean(not equal.value), None

    def less_than(self, other):
        return _numeric_order(self, other, lambda a, b: a < b)

    def greater_than(self, other):
        return _numeric_order(self, other, lambda a, b: a > b)

    def less_than_equal(self, other):
        return _numeric_order(self, other, lambda a, b: a <= b)

    def greater_than_equal(self, other):
        return _numeric_order(self, other, lambda a, b: a >= b)

    def true_(self):
        return True

    def __repr__(self):
        return "-inf" if self.sign < 0 else "inf"


class List(Value):
    """
    A complex datatype representing a collection of data.

    Mutation methods (push, append, swap, delete) operate on the SAME list.
    drop(start, end) also mutates the same list but returns the extracted
    slice as a new List the caller may keep or ignore.

    Indices are Python-style: negative values wrap from the end.
    """

    def __init__(self, list_of_elements: list):
        self.set_pos()
        self.set_context()
        self.list_of_elements = list_of_elements
        self.is_const = False

    def _check_mutable(self):
        if getattr(self, "is_const", False):
            return ModificationError(
                self.pos_start,
                self.pos_end,
                "MOD001",
            )
        return None

    def _resolve_insert_index(self, index):
        """Normalizes an insertion index. Valid range covers -len..len."""
        n = len(self.list_of_elements)
        i = index
        if i < 0:
            i += n
        if i < 0 or i > n:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN109",
                {"index": index, "length": n},
            )
        return i, None

    def _resolve_access_index(self, index):
        """Normalizes an element-access index. Valid range covers -len..len-1."""
        n = len(self.list_of_elements)
        i = index
        if i < 0:
            i += n
        if i < 0 or i >= n:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN110",
                {"index": index, "length": n},
            )
        return i, None

    def push(self, element, index=None):
        """Insert at index (or append when index is omitted). In place."""
        err = self._check_mutable()
        if err:
            return None, err
        if isinstance(element, (List, Array)):
            element = element.copy()
        if index is None:
            self.list_of_elements.append(element)
            return None, None
        i, err = self._resolve_insert_index(index)
        if err:
            return None, err
        self.list_of_elements.insert(i, element)
        return None, None

    def append(self, element):
        """Append to the end. In place."""
        err = self._check_mutable()
        if err:
            return None, err
        if isinstance(element, (List, Array)):
            element = element.copy()
        self.list_of_elements.append(element)
        return None, None

    def swap(self, element, index):
        """Replace the element at index. In place."""
        err = self._check_mutable()
        if err:
            return None, err
        if isinstance(element, (List, Array)):
            element = element.copy()
        i, err = self._resolve_access_index(index)
        if err:
            return None, err
        self.list_of_elements[i] = element
        return None, None

    def delete(self, index):
        """
        Remove a single element by index. In place.
        """
        err = self._check_mutable()
        if err:
            return None, err
        i, err = self._resolve_access_index(index)
        if err:
            return None, err
        del self.list_of_elements[i]
        return None, None

    def drop(self, start, end):
        """
        Remove slice [start:end] in place; return it as a new List.
        Clamps like slice `l[s..e]`.
        """
        err = self._check_mutable()
        if err:
            return None, err
        n = len(self.list_of_elements)
        s, e = start, end
        if s < 0:
            s += n
        if e < 0:
            e += n
        s = max(0, min(s, n))
        e = max(0, min(e, n))
        if s > e:
            s = e
        removed = self.list_of_elements[s:e]
        # Deep copy nested collections for isolation
        deep_removed = []
        for el in removed:
            if isinstance(el, (List, Array)):
                deep_removed.append(el.copy())
            else:
                deep_removed.append(el)
        del self.list_of_elements[s:e]
        return List(deep_removed), None

    def assign_at(self, index, element):
        """
        Dynamic index assignment: replaces if in bounds, extends
        if at/past end.
        """
        err = self._check_mutable()
        if err:
            return None, err
        if isinstance(element, (List, Array)):
            element = element.copy()
        n = len(self.list_of_elements)
        i = index
        if i < 0:
            i += n
        if i < 0:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN110",
                {"index": index, "length": n},
            )
        if i < n:
            self.list_of_elements[i] = element
            return None, None
        if i > MAX_AUTO_GROW_INDEX:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN110",
                {"index": index, "length": n},
            )

        # dynamic growth: extend with none (Empty) up to i, then append
        while len(self.list_of_elements) < i:
            self.list_of_elements.append(
                Empty().set_pos(self.pos_start, self.pos_end).set_context(self.context)
            )
        self.list_of_elements.append(element)
        # if we extended, we now have i+1 elements; but if i == n we just appended,
        # if i > n we padded
        # For i == n case, the while loop didn't run and append gives correct
        # For i > n, we padded to i then appended -> length i+1 correct
        # However the above does: while len < i: append Empty,
        # then append element -> for i = n+5, we pad 5 empties then element
        return None, None

    @staticmethod
    def _element_wise(elements, other, operation):
        """Applies `operation` element-wise against `other`.

        An element that refuses the operation is kept unchanged, so the
        result always preserves the container size.
        """
        new_elements = []
        for element in elements:
            res, error = operation(element, other)
            new_elements.append(element if error else res)
        return new_elements

    def multiplication(self, other):
        if isinstance(other, NumericValue):
            new_elements = self._element_wise(
                self.list_of_elements, other, lambda el, o: el.multiplication(o)
            )
            return (
                List(new_elements)
                .set_context(self.context)
                .set_pos(self.pos_start, self.pos_end),
                None,
            )

        if isinstance(other, List):
            if len(self.list_of_elements) != len(other.list_of_elements):
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "RUN111",
                )

            new_elements = []
            for a, b in zip(self.list_of_elements, other.list_of_elements):
                res, error = a.multiplication(b)
                new_elements.append(a if error else res)

            return (
                List(new_elements)
                .set_context(self.context)
                .set_pos(self.pos_start, self.pos_end),
                None,
            )

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "RUN112",
            {"type_name": type_spelling(other)},
        )

    def division(self, other):
        if isinstance(other, NumericValue):
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "RUN100",
                )
            new_elements = []
            for element in self.list_of_elements:
                res, error = element.division(other)
                if error:
                    if error.details and "division by zero" in error.details.lower():
                        return None, error
                    new_elements.append(element)
                else:
                    new_elements.append(res)
            return (
                List(new_elements)
                .set_context(self.context)
                .set_pos(self.pos_start, self.pos_end),
                None,
            )

        if isinstance(other, List):
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN113",
            )

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "RUN114",
            {"type_name": type_spelling(other)},
        )

    def _reversed_multiplication(self, other):
        return self.multiplication(other)

    def is_equal(self, other):
        if isinstance(other, List):
            if len(self.list_of_elements) != len(other.list_of_elements):
                return Boolean(False), None
            for a, b in zip(self.list_of_elements, other.list_of_elements):
                res, error = a.is_equal(b)
                if error:
                    return Boolean(False), None
                if not res.value:
                    return Boolean(False), None
            return Boolean(True), None
        return Boolean(False), None

    def not_equal(self, other):
        res, error = self.is_equal(other)
        if error:
            return res, error
        return Boolean(not res.value), None

    def copy(self):
        new_elements = []
        for el in self.list_of_elements:
            if isinstance(el, (List, Array)):
                new_elements.append(el.copy())
            else:
                new_elements.append(el)
        copy = List(new_elements)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return f"{self.list_of_elements}"


class Array(List):
    """
    Typed array: element type enforced on every mutation.

    `depth` records how many `[]` levels the annotation declared:
    depth 1 = flat (elements are scalars), depth >= 2 = nested, where
    elements are typed arrays of depth-1. Shape is enforced strictly.
    """

    def __init__(self, element_type_class, list_of_elements=None, depth=1):
        self.element_type = element_type_class
        self.depth = depth if depth else 1

        self.type_name = None
        self.set_pos()
        self.set_context()
        self.list_of_elements = list_of_elements if list_of_elements is not None else []
        self.is_const = False

    def push(self, element, index=None):
        err = self._validate_element(element)
        if err:
            return None, err
        element = self._prepare_stored(element)
        return List.push(self, element, index)

    def append(self, element):
        err = self._validate_element(element)
        if err:
            return None, err
        element = self._prepare_stored(element)
        return List.append(self, element)

    def swap(self, element, index):
        err = self._validate_element(element)
        if err:
            return None, err
        element = self._prepare_stored(element)
        return List.swap(self, element, index)

    def _type_spelling(self):
        """
        Canonical B# spelling of this array's type, e.g. `Long[][]`.

        Built from the declared element type plus the recorded nesting depth,
        so a nested array keeps every `[]` (dimension) level instead of collapsing
        to the flat spelling, and element types are always spelled the way the
        language spells them (`Bool[]`, never `Boolean[]`).
        """
        base = class_spelling(self.element_type)
        return f"{base}{'[]' * max(1, self.depth)}"

    def _make_row(self, elements):
        """
        Builds an independent typed row of depth-1 from `elements`.
        """
        if type(self) is Array:
            row = Array(self.element_type, elements, depth=self.depth - 1)
        else:
            row = type(self)(elements, depth=self.depth - 1)
        row.set_pos(self.pos_start, self.pos_end)
        row.set_context(self.context)
        if row.depth >= 2:
            # deeper levels: rows inside the row must be typed too
            row._validate_all()
        return row

    def fresh_row(self):
        """
        Empty typed row for index-assign auto-vivification.

        Returns None when depth < 2 (elements are scalars, not rows).
        """
        if self.depth < 2:
            return None
        return self._make_row([])

    def _coerce_row(self, row):
        """
        Returns an independent typed copy of a validated row.
        """
        if (
            isinstance(row, Array)
            and row.element_type is self.element_type
            and row.depth == self.depth - 1
        ):
            return row.copy()
        src = row.copy() if isinstance(row, List) else row
        return self._make_row(list(src.list_of_elements))

    def _prepare_stored(self, element):
        """
        Normalizes a validated element before storage (typed rows).
        """
        if self.depth >= 2 and isinstance(element, List):
            return self._coerce_row(element)
        return element

    def _validate_element(self, element, level=1):
        """Strict depth-aware validation.

        Levels < depth must hold lists; the final level must hold
        `element_type` scalars. `level` is the 1-based position of
        `element` within the declared shape.
        """
        depth = self.depth
        expect = self._type_spelling()
        if isinstance(element, Empty):
            if self.element_type is Empty:
                return None
            return RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN115" if level == 1 else "RUN116",
                {"expected_type": expect},
            )
        if level >= depth:
            if isinstance(element, self.element_type):
                return None

            code = "RUN118" if level == 1 else "RUN117"
            return RunTimeError(
                self.pos_start,
                self.pos_end,
                code,
                {"expected_type": expect, "actual_type": type_spelling(element)},
            )

        if not isinstance(element, List):
            code = "RUN118" if level == 1 else "RUN117"
            return RunTimeError(
                self.pos_start,
                self.pos_end,
                code,
                {"expected_type": expect, "actual_type": type_spelling(element)},
            )
        for item in element.list_of_elements:
            err = self._validate_element(item, level + 1)
            if err:
                return err
        return None

    def _validate_all(self):
        for el in self.list_of_elements:
            err = self._validate_element(el)
            if err:
                return err
        if self.depth >= 2:
            for idx, el in enumerate(self.list_of_elements):
                self.list_of_elements[idx] = self._coerce_row(el)
        return None

    def multiplication(self, other):
        if isinstance(other, (NumericValue, List)):
            elements, error = List.multiplication(self, other)
            if error:
                return None, error
            return self._new_array(elements.list_of_elements), None

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "RUN119",
            {"type_name": type_spelling(other)},
        )

    def division(self, other):
        if isinstance(other, NumericValue):
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "RUN100",
                )
            elements, error = List.division(self, other)
            if error:
                return None, error
            return self._new_array(elements.list_of_elements), None

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "RUN120",
        )

    def is_equal(self, other):
        if isinstance(other, List):
            if len(self.list_of_elements) != len(other.list_of_elements):
                return Boolean(False), None
            for a, b in zip(self.list_of_elements, other.list_of_elements):
                res, error = a.is_equal(b)
                if error:
                    return Boolean(False), None
                if not res.value:
                    return Boolean(False), None
            return Boolean(True), None
        return Boolean(False), None

    def _new_array(self, elements):
        if type(self) is Array:
            arr = Array(self.element_type, elements, depth=self.depth)
        else:
            arr = type(self)(elements, depth=self.depth)
        arr.type_name = self.type_name
        arr.set_pos(self.pos_start, self.pos_end)
        arr.set_context(self.context)
        return arr

    def copy(self):
        new_elements = []
        for el in self.list_of_elements:
            if isinstance(el, (List, Array)):
                new_elements.append(el.copy())
            else:
                new_elements.append(el)
        return self._new_array(new_elements)

    def drop(self, start, end):
        """
        Remove slice [start:end] in place; return it as same typed array.
        Clamps like slice.
        """
        err = self._check_mutable()
        if err:
            return None, err
        n = len(self.list_of_elements)
        s, e = start, end
        if s < 0:
            s += n
        if e < 0:
            e += n
        s = max(0, min(s, n))
        e = max(0, min(e, n))
        if s > e:
            s = e
        removed = self.list_of_elements[s:e]
        deep_removed = []
        for el in removed:
            if isinstance(el, (List, Array)):
                deep_removed.append(el.copy())
            else:
                deep_removed.append(el)
        del self.list_of_elements[s:e]
        return self._new_array(deep_removed), None

    def assign_at(self, index, element):
        """
        Dynamic assignment for typed arrays - validates type then
        delegates with type-appropriate padding.
        """
        err = self._validate_element(element)
        if err:
            return None, err
        if isinstance(element, (List, Array)):
            element = self._prepare_stored(element)
        err = self._check_mutable()
        if err:
            return None, err
        n = len(self.list_of_elements)
        i = index
        if i < 0:
            i += n
        if i < 0:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN110",
                {"index": index, "length": n},
            )
        if i < n:
            self.list_of_elements[i] = element
            return None, None
        if i > MAX_AUTO_GROW_INDEX:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "RUN110",
                {"index": index, "length": n},
            )

        def _default():
            if isinstance(self.element_type, type) and issubclass(
                self.element_type, NumericValue
            ):
                # et(0) normalizes: integer zero for int kinds, 0.0 for
                # Float/Double.
                return (
                    self.element_type(0)
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is String:
                return (
                    String("")
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is Char:
                return (
                    Char("\0")
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is Boolean:
                return (
                    Boolean(False)
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is Empty:
                return (
                    Empty()
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is Inf:
                return (
                    Inf()
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is NaN:
                return (
                    NaN()
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            return (
                Empty().set_pos(self.pos_start, self.pos_end).set_context(self.context)
            )

        while len(self.list_of_elements) < i:
            if self.depth >= 2:
                self.list_of_elements.append(self._make_row([]))
            else:
                self.list_of_elements.append(_default())
        self.list_of_elements.append(element)
        return None, None

    def __repr__(self):
        return f"{self.list_of_elements}"


class ShortArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Short, list_of_elements, depth)


class SingleArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Single, list_of_elements, depth)


class IntegerArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Integer, list_of_elements, depth)


class LongArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Long, list_of_elements, depth)


class FloatArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Float, list_of_elements, depth)


class DoubleArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Double, list_of_elements, depth)


class CharArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Char, list_of_elements, depth)


class StringArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(String, list_of_elements, depth)


class BooleanArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Boolean, list_of_elements, depth)


class EmptyArray(Array):
    def __init__(self, list_of_elements=None, depth=1):
        super().__init__(Empty, list_of_elements, depth)


class Tuple(Value):
    """
    A complex datatype representing an immutable container of data.

    Tuples are immutable containers of ordered values. Its size and
    contents are fixed at creation: no operation grows, shrinks, or
    rewrites it. The variable holding a tuple may still be reassingned
    to a new tuple. Indices are Python-styled as well, where negative
    values wrap from the end.
    """

    def __init__(self, elements=None):
        self.set_pos()
        self.set_context()
        self.elements = list(elements) if elements is not None else []

    def get_at(self, index, pos_start=None, pos_end=None):
        n = len(self.elements)
        i = index

        if i < 0:
            i += n
        if i < 0 or i >= n:
            return None, RunTimeError(
                pos_start or self.pos_start,
                pos_end or self.pos_end,
                "RUN011",
            )
        return self.elements[i], None

    def is_equal(self, other):
        if isinstance(other, Tuple):
            if len(self.elements) != len(other.elements):
                return Boolean(False), None
            for a, b in zip(self.elements, other.elements):
                res, error = a.is_equal(b)
                if error or not res.value:
                    return Boolean(False), None
            return Boolean(True), None
        return Boolean(False), None

    def not_equal(self, other):
        res, error = self.is_equal(other)
        if error:
            return res, error
        return Boolean(not res.value), None

    def copy(self):
        return self

    def __repr__(self):
        return "(" + ", ".join(repr(e) for e in self.elements) + ")"


class TupleTypeSpec:
    """
    Parsed constraint behind a Tuple annotation spelling.

    kind is one of:
      "any"      -> bare `Tuple` (no constraint)
      "empty"    -> `Tuple()` (exactly zero elements)
      "hom"      -> `Tuple(T)` (any length, every element is T)
      "sequence" -> `Tuple(N1 : T1, T2, N2 : T3, ...)`; exact arity is the
                    sum of the per-slot counts, types are positional.
                    An uncounted slot counts as exactly one element.

    For "hom" and "sequence", slots is a list of (count, type_spelling)
    pairs; count is an int, or None for "hom" (unbounded length).
    """

    def __init__(self, kind, slots=None, spelling=None):
        self.kind = kind
        self.slots = slots or []
        self.spelling = spelling

    def expected_types(self, n):
        """
        Flat list of `n` expected element type spellings for a value with
        `n` elements, or None when `n` itself violates the spec's arity.
        """
        if self.kind == "hom":
            return [self.slots[0][1]] * n
        flat = []
        total = 0
        for count, type_spelling in self.slots:
            reps = 1 if count is None else count
            total += reps
            flat.extend([type_spelling] * reps)
        return flat if n == total else None


class ErrorInstance(Value):
    """
    Support for error catching in B#. This class helps in `try-catch` phases
    while catching an error.
    """

    def __init__(self, error: Error):
        super().__init__()

        self.error = error
        self.type_name = error.__class__.__name__

    def get_property(self, name):
        """Expose Python Error properties directly to B# code"""
        if name == "name":
            return String(self.error.error_name)
        if name == "details":
            return String(str(self.error.details))
        if name == "line":
            return (
                Long(self.error.pos_start.line + 1) if self.error.pos_start else Long(0)
            )
        if name == "file":
            return (
                String(self.error.pos_start.file_name)
                if self.error.pos_start
                else String("")
            )
        if name == "type":
            return String(self.type_name)
        return None

    def __str__(self):
        try:
            if hasattr(self.error, "as_string"):
                return self.error.as_string()
        except Exception:
            pass
        return f"{self.type_name}: {self.error.details}"

    def __repr__(self):
        return self.__str__()


class Context:
    """
    Runtime scope holding the variables table that persists across statements.
    """

    def __init__(
        self,
        display_name,
        parent=None,
        parent_entry_pos=None,
        in_function=False,
        in_loop=False,
    ):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.in_function = in_function
        self.in_loop = in_loop
        self.variables = EnvironmentVariable(parent.variables if parent else None)


class BodyScopeContext(Context):
    """Loop body context that reads from the loop scope but writes new
    variable definitions to the enclosing (non-loop) scope.

    This lets loop body code read loop control variables (like ``i`` in
    ``for`` headers) while ensuring ``var`` declarations inside the body
    are visible outside the loop.
    """

    def __init__(self, loop_context, write_to, in_loop=True, in_function=None):

        if in_function is None:
            in_function = bool(
                getattr(loop_context, "in_function", False)
                or getattr(write_to, "in_function", False)
            )
        super().__init__(
            "<loop body>", loop_context, in_loop=in_loop, in_function=in_function
        )
        self._write_to = write_to

    def define(self, name, data_type, value, is_const=False, type_spelling=None):
        return self._write_to.variables.set_pos(
            self.variables.pos_start, self.variables.pos_end
        ).define(name, data_type, value, is_const, type_spelling)


class EnvironmentVariable:
    """
    Unified Class of Variables Creation (UCVC).

    How it works: `EnvironmentVariable` declares a dictionary of static
    search time O(1). This helps saving all variables in a unefined structure
    matching the following example:
    ```
    DICT: EnvironmentVariable = [
        name_of_variable {
            "type":type,
            "value":value,
            "is_const":True|False
        }
    ]
    ```

    A type can be (Empty) invoking emptyness (see DATATYPE: `Empty` for more
    info). However, `is_const` is set by default to (`False`) to declare ability
    to reassign or change value.
    """

    def __init__(self, parent=None):
        self.pos_start = None
        self.pos_end = None
        self.variables = {}
        self.parent = parent
        self.set_pos()

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def define(self, name, data_type, value, is_const=False, type_spelling=None):
        """Declares a new variable in current environment scope."""

        if name in self.variables:
            return None, AssignmentError(
                self.pos_start,
                self.pos_end,
                "ASN001",
                {"name": name},
            )

        type_error = self._type_mismatch_error(data_type, value)
        if type_error:
            return None, type_error

        if type_spelling and type_spelling.startswith("Tuple("):
            value, coerce_err = coerce_tuple_elements(value, type_spelling)
            if coerce_err:
                return None, coerce_err
            spec, _ = parse_tuple_type(type_spelling)
            reason = tuple_violation(spec, value)
            if reason:
                return None, AssignmentError(
                    self.pos_start,
                    self.pos_end,
                    "ASN006",
                    {"expected": type_spelling, "reason": reason},
                )

        if is_const and isinstance(value, (List, Array)):

            def _deep_copy(v):
                if isinstance(v, Array):
                    new_elements = []
                    for el in v.list_of_elements:
                        if isinstance(el, (List, Array)):
                            new_elements.append(_deep_copy(el))
                        else:
                            new_elements.append(el)
                    if type(v) is Array:
                        new_v = Array(v.element_type, new_elements, depth=v.depth)
                    else:
                        new_v = type(v)(new_elements, depth=v.depth)
                    new_v.type_name = v.type_name
                    new_v.set_pos(v.pos_start, v.pos_end)
                    new_v.set_context(v.context)
                    new_v.is_const = True
                    return new_v
                elif isinstance(v, List):
                    new_elements = []
                    for el in v.list_of_elements:
                        if isinstance(el, (List, Array)):
                            new_elements.append(_deep_copy(el))
                        else:
                            new_elements.append(el)
                    new_v = List(new_elements)
                    new_v.set_pos(v.pos_start, v.pos_end)
                    new_v.set_context(v.context)
                    new_v.is_const = True
                    return new_v
                return v

            value = _deep_copy(value)

        self.variables[name] = {
            "type": data_type,
            "type_spelling": type_spelling,
            "value": value,
            "is_const": is_const,
        }
        return value, None

    def assign(self, name, value, pos_start=None, pos_end=None):
        """Updates an existing variable value."""

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        if name not in self.variables:
            if self.parent is not None:
                return self.parent.assign(name, value, pos_start, pos_end)
            return None, AssignmentError(
                pos_start,
                pos_end,
                "ASN002",
                {"name": name},
            )

        entry = self.variables[name]

        if entry["is_const"]:
            return None, ModificationError(
                pos_start,
                pos_end,
                "MOD002",
                {"name": name},
            )

        type_error = self._type_mismatch_error(entry["type"], value, pos_start, pos_end)
        if type_error:
            return None, type_error

        spelling = entry.get("type_spelling")
        if spelling and spelling.startswith("Tuple("):
            value, coerce_err = coerce_tuple_elements(value, spelling)
            if coerce_err:
                return None, coerce_err
            spec, _ = parse_tuple_type(spelling)
            reason = tuple_violation(spec, value)
            if reason:
                return None, AssignmentError(
                    pos_start,
                    pos_end,
                    "ASN006",
                    {"expected": spelling, "reason": reason},
                )

        entry["value"] = value
        return value, None

    def get(self, name, pos_start=None, pos_end=None):
        """Fetches variable value by name."""

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        if name not in self.variables:
            if self.parent is not None:
                return self.parent.get(name, pos_start, pos_end)
            return None, AssignmentError(
                pos_start,
                pos_end,
                "ASN003",
                {"name": name},
            )
        return self.variables[name]["value"], None

    def get_type(self, name, pos_start=None, pos_end=None):
        """Fetches variable declared type class by name."""

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        if name not in self.variables:
            if self.parent is not None:
                return self.parent.get_type(name, pos_start, pos_end)
            return None, AssignmentError(
                pos_start,
                pos_end,
                "ASN003",
                {"name": name},
            )
        return self.variables[name]["type"], None

    def _type_mismatch_error(self, data_type, value, pos_start=None, pos_end=None):
        """
        Validates value type against declared variable type.
        """

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        if data_type is None:  # Weakly typed variable will accept any value
            return None

        if value is None:  # Uninitialized value is treated as `none`
            return None

        if data_type is Empty:
            if isinstance(value, Empty):
                return None
            val_type_str = type_spelling(value)
            return AssignmentError(
                pos_start,
                pos_end,
                "ASN004",
                {"actual_type": val_type_str},
            )

        if isinstance(data_type, type) and issubclass(data_type, NumericValue):
            # Numeric declarations demand the exact type: a Long value
            # never satisfies an Integer annotation (promote in math,
            # error on assign - convert explicitly with `cast`).
            if type(value) is data_type:
                # A literal-typed value flowing straight into its
                # annotation position is consumed here.
                if getattr(value, "_from_literal", False):
                    try:
                        delattr(value, "_from_literal")
                    except AttributeError:
                        pass
                return None
        elif isinstance(value, data_type):
            return None
        # A literal marker that reaches a mismatching annotation is stale.
        if getattr(value, "_from_literal", False):
            try:
                delattr(value, "_from_literal")
            except AttributeError:
                pass

        val_type_str = type_spelling(value)
        return AssignmentError(
            pos_start,
            pos_end,
            "ASN005",
            {"actual_type": val_type_str, "expected_type": class_spelling(data_type)},
        )


class Function(Value):
    """
    Runtime representation of a defined function in B-Sharp.
    """

    def __init__(
        self, name, body_node, arg_nodes, return_type_tok, parent_context=None
    ):
        self.name = name
        self.body_node = body_node
        self.arg_nodes = arg_nodes  # (param_name_tok, param_type_tok, default_node)
        self.return_type_tok = return_type_tok
        self.return_type = (
            resolve_type(return_type_tok.value) if return_type_tok else None
        )
        self.set_context(parent_context)
        self.set_pos()

    def _bind_arguments(self, args, arg_names, pos_start, pos_end, arg_is_literal=None):
        """
        Maps call arguments onto the declared parameters.

        Positional arguments fill parameters in declaration order; named
        arguments (`name = value`) may follow them in any order. Returns
        (bindings, lit_params, None) on success, or (None, None, error),
        where lit_params maps each bound parameter name to whether the
        argument filling it was a numeric literal (for annotation
        narrowing of `f(5)` against `x : Integer`).
        """
        param_names = [name_tok.value for name_tok, _, _ in self.arg_nodes]
        bindings = {}
        lit_params = {}
        positional_index = 0
        seen_named = False

        for i, arg_value in enumerate(args):
            name_tok = arg_names[i] if arg_names else None

            if name_tok is None:
                if seen_named:
                    return None, None, RunTimeError(pos_start, pos_end, "RUN141", {})
                if positional_index >= len(param_names):
                    return (
                        None,
                        None,
                        RunTimeError(
                            pos_start,
                            pos_end,
                            "RUN122",
                            {
                                "func_name": self.name,
                                "expected": len(param_names),
                                "actual": len(args),
                            },
                        ),
                    )
                param_name = param_names[positional_index]
                positional_index += 1
                err_pos_start, err_pos_end = pos_start, pos_end
            else:
                seen_named = True
                if name_tok.value not in param_names:
                    return (
                        None,
                        None,
                        RunTimeError(
                            name_tok.pos_start,
                            name_tok.pos_end,
                            "RUN142",
                            {"func_name": self.name, "param": name_tok.value},
                        ),
                    )
                param_name = name_tok.value
                err_pos_start, err_pos_end = name_tok.pos_start, name_tok.pos_end

            if param_name in bindings:
                return (
                    None,
                    None,
                    RunTimeError(
                        err_pos_start,
                        err_pos_end,
                        "RUN143",
                        {"param": param_name},
                    ),
                )

            bindings[param_name] = arg_value
            lit_params[param_name] = bool(
                arg_is_literal is not None
                and i < len(arg_is_literal)
                and arg_is_literal[i]
            )

        return bindings, lit_params, None

    def execute(
        self,
        args,
        interpreter,
        arg_names=None,
        call_pos_start=None,
        call_pos_end=None,
        arg_is_literal=None,
    ):
        from B_Sharp.ASTNodes.interpreter import RunTimeResult

        res = RunTimeResult()

        err_pos_start = call_pos_start or self.pos_start
        err_pos_end = call_pos_end or self.pos_end

        exec_context = Context(
            display_name=f"<function {self.name}>",
            parent=self.context,
            parent_entry_pos=self.pos_start,
            in_function=True,
        )

        bindings, lit_params, err = self._bind_arguments(
            args, arg_names, err_pos_start, err_pos_end, arg_is_literal
        )
        if err:
            return res.failure(err)

        # Every parameter without a default must have been given a value.
        required = [
            name_tok.value
            for name_tok, _, default_node in self.arg_nodes
            if default_node is None
        ]
        missing = [name for name in required if name not in bindings]
        if missing:
            return res.failure(
                RunTimeError(
                    err_pos_start,
                    err_pos_end,
                    "RUN122",
                    {
                        "func_name": self.name,
                        "expected": len(required),
                        "actual": len(required) - len(missing),
                    },
                )
            )

        for param_name_tok, param_type_tok, param_default in self.arg_nodes:
            pname = param_name_tok.value
            if pname in bindings:
                arg_value = bindings[pname]
                from_literal = bool(lit_params.get(pname, False))
            else:
                # Parameter was omitted: fall back to its declared default.
                default_res = interpreter.visit(param_default, exec_context)
                if default_res.error:
                    return res.failure(default_res.error)
                arg_value = default_res.value
                # A literal default (`x : Integer = 5`) narrows like a
                # literal call argument. The parser only builds NumberNode
                # defaults for numeric literal text.
                from B_Sharp.ASTNodes.nodes import NumberNode

                from_literal = isinstance(param_default, NumberNode)

            # Full isolation: deep copy List/Array args so caller not mutated
            if isinstance(arg_value, (List, Array)):
                arg_value = arg_value.copy()

            param_type = resolve_type(param_type_tok.value) if param_type_tok else None

            if (
                isinstance(param_type, type)
                and issubclass(param_type, NumericValue)
                and isinstance(arg_value, NumericValue)
                and from_literal
            ):
                payload, reason = _typesys.context_literal(
                    arg_value.value,
                    arg_value.type_name in _typesys.FLOAT_TYPE_NAMES,
                    param_type.__name__,
                )
                if reason is None:
                    arg_value = param_type(payload)
                    arg_value.set_pos(param_name_tok.pos_start, param_name_tok.pos_end)
                    arg_value.set_context(exec_context)
                else:
                    return res.failure(
                        AssignmentError(
                            param_name_tok.pos_start,
                            param_name_tok.pos_end,
                            "ASN005",
                            {
                                "actual_type": type_spelling(arg_value),
                                "expected_type": class_spelling(param_type),
                            },
                        )
                    )

            if (
                param_type
                and issubclass(param_type, Array)
                and isinstance(arg_value, List)
            ):
                array_class = resolve_type(param_type_tok.value)
                if array_class:
                    arg_value = array_class(
                        arg_value.list_of_elements,
                        depth=max(1, array_depth(param_type_tok.value)),
                    )
                    arg_value.type_name = param_type_tok.value
                    arg_value.set_pos(err_pos_start, err_pos_end)
                    err = arg_value._validate_all()
                    if err:
                        return res.failure(err)
                # Ensure typed wrapper also isolated (deep copy already done)
            elif isinstance(arg_value, (List, Array)):
                # Already copied above, but keep for clarity - no extra wrapper needed
                pass

            _, err = exec_context.variables.set_pos(
                param_name_tok.pos_start, param_name_tok.pos_end
            ).define(
                name=param_name_tok.value,
                data_type=param_type,
                value=arg_value,
                type_spelling=param_type_tok.value if param_type_tok else None,
            )
            if err:
                return res.failure(err)

        body_res = interpreter.visit(self.body_node, exec_context)

        if body_res.error:
            return res.failure(body_res.error)

        return_val = body_res.func_return_value
        if return_val is None:
            return_val = (
                Empty().set_context(exec_context).set_pos(self.pos_start, self.pos_end)
            )

        if self.return_type is not None:
            if issubclass(self.return_type, Array) and isinstance(return_val, List):
                array_class = resolve_type(self.return_type_tok.value)
                if array_class:
                    return_val = array_class(
                        return_val.list_of_elements,
                        depth=max(1, array_depth(self.return_type_tok.value)),
                    )
                    return_val.type_name = self.return_type_tok.value
                    return_val.set_pos(err_pos_start, err_pos_end)
                    err = return_val._validate_all()
                    if err:
                        return res.failure(err)

            # Literal narrowing: `return 5` inside a function declared
            # `-> Integer` types the literal when it converts cleanly,
            # mirroring annotated variable declarations.
            if (
                isinstance(self.return_type, type)
                and issubclass(self.return_type, NumericValue)
                and isinstance(return_val, NumericValue)
                and getattr(return_val, "_from_literal", False)
            ):
                converted, _reason = _typesys.context_literal(
                    return_val.value,
                    return_val.type_name in _typesys.FLOAT_TYPE_NAMES,
                    self.return_type.__name__,
                )
                if _reason is None:
                    return_val = self.return_type(converted)
                    return_val.set_pos(err_pos_start, err_pos_end)
                    return_val.set_context(exec_context)
            if getattr(return_val, "_from_literal", False):
                try:
                    delattr(return_val, "_from_literal")
                except AttributeError:
                    pass

            if isinstance(self.return_type, type) and issubclass(
                self.return_type, NumericValue
            ):
                # Numeric returns demand the exact type (promote in math,
                # error on assign - convert explicitly with `cast`).
                matches = type(return_val) is self.return_type
            else:
                matches = isinstance(return_val, self.return_type)
            if not matches and not (
                self.return_type is Empty and isinstance(return_val, Empty)
            ):
                val_type_str = type_spelling(return_val)
                return res.failure(
                    RunTimeError(
                        err_pos_start,
                        err_pos_end,
                        "RUN123",
                        {
                            "func_name": self.name,
                            "actual_type": val_type_str,
                            "expected_type": class_spelling(self.return_type),
                        },
                    )
                )

            # Tuple(...) annotations constrain length and element types
            spelling = self.return_type_tok.value if self.return_type_tok else None
            if spelling and spelling.startswith("Tuple("):
                return_val, coerce_err = coerce_tuple_elements(return_val, spelling)
                if coerce_err:
                    return res.failure(coerce_err)
                spec, _ = parse_tuple_type(spelling)
                reason = tuple_violation(spec, return_val)
                if reason:
                    return res.failure(
                        RunTimeError(
                            err_pos_start,
                            err_pos_end,
                            "RUN123",
                            {
                                "func_name": self.name,
                                "actual_type": (
                                    f"Tuple with {len(return_val.elements)} "
                                    "element(s)"
                                ),
                                "expected_type": spelling,
                            },
                        )
                    )

        return res.success(return_val)

    def is_equal(self, other):
        if isinstance(other, Function):
            return Boolean(self is other), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, Function):
            return Boolean(self is not other), None
        return Boolean(True), None

    def true_(self):
        return True

    def __repr__(self):
        return f"<function {self.name}>"


class StructDefinition(Value):
    """
    Structures Instance for B-Sharp `struct`.

    A `struct` (structure) in B-Sharp, is a data model to organize data
    inside, it houses multiple assignment of variables in an organized way
    that keeps them all grouped to one *super-variable*
    """

    def __init__(self, name, member_nodes, parent_context=None):
        self.name = name
        self.member_nodes = member_nodes
        self.parent_context = parent_context
        self.set_pos()

    def instantiate(
        self,
        interpreter,
        args=None,
        arg_names=None,
        pos_start=None,
        pos_end=None,
        arg_is_literal=None,
    ):
        exec_context = Context(
            display_name=f"<struct {self.name}>", parent=self.parent_context
        )

        for node in self.member_nodes:
            res = interpreter.visit(node, exec_context)
            if res.error:
                return None, res.error

        if args:
            err = self._bind_fields(
                exec_context,
                args,
                arg_names,
                pos_start or self.pos_start,
                pos_end or self.pos_end,
                arg_is_literal,
            )
            if err:
                return None, err

        instance = StructInstance(self.name, exec_context.variables)
        return instance, None

    def _bind_fields(
        self, exec_context, args, arg_names, pos_start, pos_end, arg_is_literal=None
    ):
        """Fills the struct's fields from its constructor arguments.

        Positional arguments fill writable fields in declaration order; named
        arguments (`field = value`) may follow them in any order. Fields left
        unbound keep the value their declaration gave them. Numeric literal
        arguments narrow into numeric-typed fields, mirroring annotated
        variable declarations.
        """
        variables = exec_context.variables.variables
        positional_fields = [
            name for name, entry in variables.items() if not entry["is_const"]
        ]
        bindings = {}
        lit_fields = {}
        positional_index = 0
        seen_named = False

        for i, value in enumerate(args):
            name_tok = arg_names[i] if arg_names else None

            if name_tok is None:
                if seen_named:
                    return RunTimeError(pos_start, pos_end, "RUN141", {})
                if positional_index >= len(positional_fields):
                    return RunTimeError(
                        pos_start,
                        pos_end,
                        "RUN140",
                        {
                            "struct_name": self.name,
                            "expected": len(positional_fields),
                            "actual": len(args),
                        },
                    )
                field_name = positional_fields[positional_index]
                positional_index += 1
                err_pos_start, err_pos_end = pos_start, pos_end
            else:
                seen_named = True
                if name_tok.value not in variables:
                    return RunTimeError(
                        name_tok.pos_start,
                        name_tok.pos_end,
                        "RUN144",
                        {"struct_name": self.name, "field": name_tok.value},
                    )
                field_name = name_tok.value
                err_pos_start, err_pos_end = name_tok.pos_start, name_tok.pos_end

            if field_name in bindings:
                return RunTimeError(
                    err_pos_start, err_pos_end, "RUN143", {"param": field_name}
                )

            bindings[field_name] = value
            lit_fields[field_name] = bool(
                arg_is_literal is not None
                and i < len(arg_is_literal)
                and arg_is_literal[i]
            )

        for field_name, value in bindings.items():
            declared = variables[field_name]["type"]
            if (
                lit_fields.get(field_name, False)
                and isinstance(declared, type)
                and issubclass(declared, NumericValue)
                and isinstance(value, NumericValue)
            ):
                payload, reason = _typesys.context_literal(
                    value.value,
                    value.type_name in _typesys.FLOAT_TYPE_NAMES,
                    declared.__name__,
                )
                if reason is None:
                    value = declared(payload)
                    value.set_pos(pos_start, pos_end)
                    value.set_context(exec_context)
                # Otherwise the assign() below reports ASN005.
            _, err = exec_context.variables.assign(
                field_name, value, pos_start, pos_end
            )
            if err:
                return err
        return None

    def __repr__(self):
        return f"<struct_def {self.name}>"


class StructInstance(Value):
    def __init__(self, struct_name, environment):
        self.struct_name = struct_name
        self.environment = environment

        self.set_pos()
        self.set_context()

    def get_field(self, name, pos_start=None, pos_end=None):
        if name not in self.environment.variables:
            if pos_start is None:
                pos_start, pos_end = self.pos_start, self.pos_end
            return None, AssignmentError(
                pos_start,
                pos_end,
                "ASN003",
                {"name": name},
            )
        return self.environment.get(name, pos_start, pos_end)

    def field_type(self, name):
        """Declared type class of a struct field (None when unannotated)."""
        entry = self.environment.variables.get(name)
        if entry is None:
            return None
        return entry.get("type")

    def set_field(self, name, value, pos_start=None, pos_end=None):
        if name not in self.environment.variables:
            if pos_start is None:
                pos_start, pos_end = self.pos_start, self.pos_end
            return None, AssignmentError(
                pos_start,
                pos_end,
                "ASN002",
                {"name": name},
            )
        return self.environment.assign(name, value, pos_start, pos_end)

    def __repr__(self):
        fields = ", ".join(
            f"{k}: {v['value']}" for k, v in self.environment.variables.items()
        )
        return f"{self.struct_name} {{ {fields} }}"


_ARRAY_CLASSES = {
    Boolean: BooleanArray,
    Short: ShortArray,
    Single: SingleArray,
    Integer: IntegerArray,
    Long: LongArray,
    Float: FloatArray,
    Double: DoubleArray,
    Char: CharArray,
    String: StringArray,
    Empty: EmptyArray,
}

_CLASS_SPELLING = {
    Boolean: "Bool",
    ShortArray: "Short[]",
    SingleArray: "Single[]",
    IntegerArray: "Integer[]",
    LongArray: "Long[]",
    FloatArray: "Float[]",
    DoubleArray: "Double[]",
    CharArray: "Char[]",
    StringArray: "String[]",
    BooleanArray: "Bool[]",
    EmptyArray: "Empty[]",
}

_TYPE_CLASSES = {
    "Bool": Boolean,
    "Short": Short,
    "Single": Single,
    "Integer": Integer,
    "Long": Long,
    "Float": Float,
    "Double": Double,
    "Char": Char,
    "String": String,
    "Inf": Inf,
    "NaN": NaN,
    "Empty": Empty,
    "List": List,
    "Function": Function,
    "Tuple": Tuple,
}

ERROR_TYPE_MAP = {
    "Error": Error,
    "B_SharpSyntaxError": B_SharpSyntaxError,
    "RunTimeError": RunTimeError,
    "AssignmentError": AssignmentError,
    "ModificationError": ModificationError,
    "ComparisonError": ComparisonError,
    "BSharpMathError": BSharpMathError,
    "ShadowingError": ShadowingError,
}

NUMERIC_CLASSES = {
    "Short": Short,
    "Single": Single,
    "Integer": Integer,
    "Long": Long,
    "Float": Float,
    "Double": Double,
}


def class_spelling(cls):
    return _CLASS_SPELLING.get(cls, cls.__name__)


def type_spelling(value):
    if isinstance(value, Array):
        return value._type_spelling()
    return class_spelling(type(value))


def resolve_type(name):
    if not name:
        return None
    if name.startswith("Tuple("):
        spec, _ = parse_tuple_type(name)
        return Tuple if spec is not None else None
    match = _ARRAY_TYPE_RE.match(name)
    base = match.group("base") if match else name
    if base not in TYPE_KEYWORDS:
        return None
    cls = _TYPE_CLASSES[base]
    return _ARRAY_CLASSES.get(cls) if match else cls


def is_castable_type(name):
    """True when `name` is an allowed `cast(value, Type)` target spelling."""
    return name in _typesys.CASTABLE_TYPES


def array_depth(name):
    if not name:
        return 0
    match = _ARRAY_TYPE_RE.match(name)
    if not match:
        return 0
    return (len(name) - len(match.group("base"))) // 2


def _split_top_level(inner):
    parts, depth, cur = [], 0, []
    for ch in inner:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur).strip())
    return parts


def parse_tuple_type(name):
    """Parses a Tuple annotation spelling into a TupleTypeSpec.

    Accepted forms:
      Tuple                          -> any elements
      Tuple()                        -> exactly the empty tuple
      Tuple(T)                       -> any length, every element is T
      Tuple(4 : Long)                -> exactly 4 Longs
      Tuple(Long, String)            -> exactly 2, positional
      Tuple(2 : Long, 3 : String)    -> 2 Longs, then 3 Strings

    Returns (spec, None) on success, (None, reason) when `name` looks like
    a Tuple(...) annotation but is malformed, and (None, None) when `name`
    is not a tuple annotation at all.
    """
    if not isinstance(name, str) or not name.startswith("Tuple"):
        return None, None
    if name == "Tuple":
        return TupleTypeSpec("any", spelling=name), None
    if not name.startswith("Tuple(") or not name.endswith(")"):
        return None, "expected '(' after 'Tuple'"
    inner = name[len("Tuple(") : -1].strip()
    if not inner:
        return TupleTypeSpec("empty", spelling=name), None

    parsed = []
    for slot in _split_top_level(inner):
        if not slot:
            return None, "empty type in parameter list"
        match = re.match(r"^(\d+)\s*:\s*(.+)$", slot, re.DOTALL)
        if match:
            count = int(match.group(1))
            slot_type = match.group(2).strip()
        else:
            count = None
            slot_type = slot
        if resolve_type(slot_type) is None:
            return None, f"unknown element type '{slot_type}'"
        parsed.append((count, slot_type))

    if len(parsed) == 1 and parsed[0][0] is None:
        return TupleTypeSpec("hom", slots=parsed, spelling=name), None
    return TupleTypeSpec("sequence", slots=parsed, spelling=name), None


def tuple_violation(spec, value):
    if spec is None or spec.kind == "any":
        return None
    if not isinstance(value, Tuple):
        return f"expected a tuple, got {type_spelling(value)}"
    n = len(value.elements)

    if spec.kind == "empty":
        return None if n == 0 else f"expected 0 elements, got {n}"

    slots = spec.expected_types(n)
    if slots is None:
        expected = sum(1 if count is None else count for count, _ in spec.slots)
        return f"expected {expected} elements, got {n}"

    for i, (element, slot) in enumerate(zip(value.elements, slots)):
        if slot.startswith("Tuple("):
            nested_spec, _ = parse_tuple_type(slot)
            nested_reason = tuple_violation(nested_spec, element)
            if nested_reason:
                return f"element {i}: {nested_reason}"
            continue
        cls = resolve_type(slot)
        if cls is None or not isinstance(element, cls):
            return f"element {i} must be {slot}, got {type_spelling(element)}"
    return None


def coerce_tuple_elements(value, spelling):
    """
    Wraps plain List elements into typed arrays when the tuple annotation
    declares array slots (e.g. `Tuple(Long[]) = ([1], [2])`), mirroring how
    `var x : Long[] = [1, 2]` coerces its list literal.

    Returns (value, error).
    """
    if not isinstance(value, Tuple) or not spelling:
        return value, None
    if not spelling.startswith("Tuple("):
        return value, None

    spec, _ = parse_tuple_type(spelling)
    if spec is None or spec.kind in ("any", "empty"):
        return value, None

    slots = spec.expected_types(len(value.elements))
    if slots is None:
        return value, None

    for i, (element, slot) in enumerate(zip(value.elements, slots)):
        if slot.startswith("Tuple("):
            nested, nested_err = coerce_tuple_elements(element, slot)
            if nested_err:
                return value, nested_err
            value.elements[i] = nested
            continue
        cls = resolve_type(slot)
        if cls is None or not issubclass(cls, Array):
            continue
        if not isinstance(element, List) or isinstance(element, Array):
            continue
        arr = cls(element.list_of_elements, depth=max(1, array_depth(slot)))
        arr.type_name = slot
        arr.set_pos(element.pos_start, element.pos_end)
        arr.set_context(element.context)
        err = arr._validate_all()
        if err:
            return value, err
        value.elements[i] = arr
    return value, None


def _default_for_type(
    data_type_class,
    pos_start=None,
    pos_end=None,
    context=None,
    depth=1,
):
    """Returns type-appropriate fallback value for
    implicit `var x : Type;` without initializer.
    """

    def _set(v):
        v.set_pos(pos_start, pos_end)
        v.set_context(context)
        return v

    if data_type_class is None:
        return _set(Empty())
    if isinstance(data_type_class, type) and issubclass(data_type_class, NumericValue):
        # data_type_class(0) normalizes: integer zero for int kinds,
        # 0.0 for Float/Double.
        return _set(data_type_class(0))
    if data_type_class is String:
        return _set(String(""))
    if data_type_class is Char:
        return _set(Char("\0"))
    if data_type_class is Boolean:
        return _set(Boolean(False))
    if data_type_class is Empty:
        return _set(Empty())
    if data_type_class is Inf:
        return _set(Inf(1))
    if data_type_class is NaN:
        return _set(NaN())
    if data_type_class is List:
        return _set(List([]))
    if data_type_class is Tuple:
        return _set(Tuple())

    if issubclass(data_type_class, Array):
        try:
            return _set(data_type_class([], depth=max(1, depth)))
        except Exception:
            return _set(Empty())
    return _set(Empty())


def convert_scalar(value, target_name, pos_start=None, pos_end=None):
    """
    Explicit scalar conversion for `cast(value, Type)` and the
    `__to_Long` / `__to_Double` builtins.

    Numeric conversions follow LLVM semantics (int->int wraps,
    float->int truncates toward zero then wraps, int->float converts
    with sitofp rounding). String parsing failures report RUN136;
    impossible conversions report RUN137.

    Returns (new_value, None) on success or (None, error). String
    targets are NOT handled here: callers render those with the active
    per-file config (see `visit_CastNode` / `_to_string`).
    """

    def _fail(code, ctx):
        return None, RunTimeError(pos_start, pos_end, code, ctx)

    def _bad_type():
        return _fail(
            "RUN137",
            {"type_name": type_spelling(value), "target_type": target_name},
        )

    if target_name in _typesys.NUMERIC_TYPE_NAMES:
        is_float_target = target_name in _typesys.FLOAT_TYPE_NAMES
        cls = NUMERIC_CLASSES[target_name]
        if isinstance(value, NumericValue):
            from_kind = (
                _typesys.FLOAT if isinstance(value.value, float) else _typesys.INT
            )
            payload = _typesys.convert_numeric(value.value, from_kind, target_name)
            return cls(payload), None
        if isinstance(value, Boolean):
            payload = _typesys.convert_numeric(
                1 if value.value else 0, _typesys.INT, target_name
            )
            return cls(payload), None
        if isinstance(value, Char):
            payload = _typesys.convert_numeric(
                ord(value.value), _typesys.INT, target_name
            )
            return cls(payload), None
        if isinstance(value, String):
            text = value.value.strip()
            if not is_float_target:
                try:
                    number = int(text, 10)
                except ValueError:
                    return _fail("RUN136", {"value": value.value})
                if not _typesys.fits_int(target_name, number):
                    return _fail("RUN136", {"value": value.value})
                return cls(number), None
            try:
                number = float(text)
            except ValueError:
                return _fail("RUN136", {"value": value.value})
            if target_name == "Float":
                number = _typesys.to_f32(number)
            return cls(number), None
        if isinstance(value, NaN):
            if is_float_target:
                number = float("nan")
                if target_name == "Float":
                    number = _typesys.to_f32(number)
                return cls(number), None
            return _bad_type()
        if isinstance(value, Inf):
            if is_float_target:
                return cls(math.inf * value.sign), None
            return _bad_type()
        return _bad_type()

    if target_name == "Char":
        if isinstance(value, Char):
            return Char(value.value), None
        if isinstance(value, String):
            if len(value.value) == 1:
                return Char(value.value), None
            return _bad_type()
        if isinstance(value, NumericValue) and (
            _typesys.TYPES[value.type_name].kind == _typesys.INT
        ):
            code = int(value.value)
            if 0 <= code <= 0x10FFFF:
                return Char(chr(code)), None
            return _bad_type()
        return _bad_type()

    if target_name == "Bool":
        if isinstance(value, Boolean):
            return Boolean(value.value), None
        if isinstance(value, NumericValue):
            return Boolean(value.value != 0), None
        if isinstance(value, Char):
            return Boolean(True), None
        if isinstance(value, String):
            lowered = value.value.strip().lower()
            if lowered == "true":
                return Boolean(True), None
            if lowered == "false":
                return Boolean(False), None
            return _bad_type()
        return _bad_type()

    return _bad_type()


default_for_type = _default_for_type
