# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# (Simple Abstracted Syntax Language)
# The code is guarded and licensed under the GPLv3 License.
# ----------------------------------------------------------------
# Module: instances.py: All B_Sharp datatypes and environment
# needed-to-define keyword instances (functions, variables, etc.).

from B_Sharp.Errors.errors import *

import math
import sys


class Value:
    """
    Base class for all B_Sharp runtime values.

    Provides shared infrastructure (set_pos, set_context) and safe default
    implementations for every operation. Subclasses only override the
    operations they actually support — undefined operations automatically
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
        if isinstance(other, Boolean):
            return Number(1 if other.value else 0)
        return other

    def _op_error(self, op):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            f"Unexpected type for {type(self).__name__.lower()} {op} operation.",
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


def _order_key(value):
    """Maps a numeric-domain value to a float for ordering comparisons.

    NaN maps to None (poisoning the comparison to false, per IEEE);
    signed infinities map to +/-math.inf; Booleans coerce to 0.0/1.0;
    anything non-numeric returns None so comparisons fall through false.
    """
    if isinstance(value, NaN):
        return None
    if isinstance(value, Inf):
        return math.inf * value.sign
    if isinstance(value, Number):
        try:
            return float(value.value)
        except OverflowError:
            # Huge exact integers overflow float conversion; they simply
            # order beyond the finite float range.
            return math.inf if value.value > 0 else -math.inf
    if isinstance(value, Boolean):
        return 1.0 if value.value else 0.0
    return None


def _numeric_order(self, other, operator):
    """Shared implementation for <, >, <=, >= over numeric operands."""
    a = _order_key(self)
    b = _order_key(other)
    if a is None or b is None:
        return Boolean(False), None
    return Boolean(operator(a, b)), None


class Number(Value):
    """
    A datatype representing a number value.

    Introduction:\n
    An atomic data type in B_Sharp that represents a number value. It holds
    for a number of any real type: integers or floating numbers mainly.
    Other values may be accepted are doubles. Be careful, because a `Number`
    datatype is only of a decimal value. Hexadecimals, Octals, and Binary
    values are not defined here.

    Usage:\n
    `Number` is easy to define. Use one of two: `var` or `const` depending
    on your needs. Here are some examples:
    ```
    var x = 5
    var y = 323.1231

    const pi = 3.14 // const holds the value without ability to change it
    const pi_approx = 22/7  // here it also enforces expression evaluation
    ```

    Datatype declaration is also possible. For example:
    ```
    var x : number = 12
    var y : number = 323 + 23

    const pi : number = 3.14
    ```

    However, be careful. Because mixing datatypes results in runtime errors.
    """

    def __init__(self, value):
        self.value = value
        self.set_pos()
        self.set_context()

    def addition(self, other):
        if isinstance(other, Number):
            return Number(self.value + other.value), None
        return self._op_error("addition")

    def subtraction(self, other):
        if isinstance(other, Number):
            return Number(self.value - other.value), None
        return self._op_error("subtraction")

    def multiplication(self, other):
        if isinstance(other, Number):
            return Number(self.value * other.value), None
        if isinstance(other, (List, Array)):
            # Scalar-vector multiplication works in both directions.
            return other._reversed_multiplication(self)
        return self._op_error("multiplication")

    def division(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero.",
                )
            return Number(self.value / other.value), None
        return self._op_error("division")

    def integer_division(self, other):
        """'%' — C-style integer division (truncates toward zero)."""
        if isinstance(other, Number):
            if not isinstance(self.value, int) or not isinstance(other.value, int):
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "'%' integer division requires integer operands.",
                )
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero.",
                )
            quotient = abs(self.value) // abs(other.value)
            if (self.value < 0) != (other.value < 0):
                quotient = -quotient
            return Number(quotient), None
        return self._op_error("division")

    def modulo_division(self, other):
        """'~' — C-style modulo (result takes the sign of the dividend)."""
        if not isinstance(other, Number):
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for non-number types in modulo operation.",
            )
        if not isinstance(self.value, int) or not isinstance(other.value, int):
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "'~' modulo requires integer operands.",
            )
        if other.value == 0:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unallowed modulo by zero.",
            )
        remainder = abs(self.value) % abs(other.value)
        if self.value < 0:
            remainder = -remainder
        return Number(remainder), None

    # Above this many result bits, an exact integer power is refused:
    # it would either not fit any practical use or exhaust memory/CPU.
    MAX_POWER_RESULT_BITS = 16384

    def power(self, power_factor):
        if isinstance(power_factor, Number):
            base, exponent = self.value, power_factor.value
            try:
                if (
                    isinstance(base, int)
                    and isinstance(exponent, int)
                    and abs(exponent) > 1
                    and base not in (0, 1, -1)
                ):
                    estimated_bits = abs(base).bit_length() * abs(exponent)
                    if estimated_bits > self.MAX_POWER_RESULT_BITS:
                        approximate = float(base) ** float(exponent)
                        if math.isinf(approximate):
                            return None, BSharpMathError(
                                self.pos_start,
                                self.pos_end,
                                "Result too large to represent.",
                            )
                        # Emit precision loss warning per D3 requirement
                        try:
                            warn = PrecisionLossWarning(
                                self.pos_start,
                                self.pos_end,
                                f"Huge power {base}^{exponent} approximated as float; precision may be lost.",
                            )
                            print(warn, end="", file=sys.stderr)
                        except Exception:
                            pass
                        return Number(approximate), None

                result = base**exponent
            except (ValueError, OverflowError):
                return None, BSharpMathError(
                    self.pos_start, self.pos_end, "Result too large to represent."
                )
            except ZeroDivisionError:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero in exponentiation.",
                )
            except Exception:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Complex numbers are not yet supported.",
                )
            if isinstance(result, complex):
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Complex numbers are not yet supported.",
                )
            if isinstance(result, float) and math.isinf(result):
                return None, BSharpMathError(
                    self.pos_start,
                    self.pos_end,
                    "Result too large to represent.",
                )
            return Number(result), None
        return self._op_error("power")

    def is_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other = self._to_number(other)
            return Boolean(self.value == other.value), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other = self._to_number(other)
            return Boolean(self.value != other.value), None
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
        try:
            return str(self.value)
        except ValueError:
            return "<value too large>"


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
    var boolean_example : Boolean = true
    var boolean_2 = false
    const BooleanValue = true
    ```
    """

    def __init__(self, value: bool):
        self.value = value
        self.set_pos()
        self.set_context()

    def is_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other_num = self._to_number(other)
            my_num = Number(1 if self.value else 0)
            return Boolean(my_num.value == other_num.value), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other_num = self._to_number(other)
            my_num = Number(1 if self.value else 0)
            return Boolean(my_num.value != other_num.value), None
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
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value or other.value), None
        return None, ComparisonError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def not_(self):
        return Boolean(not self.value), None

    def true_(self):
        return self.value

    def __repr__(self):
        return "true" if self.value == True else "false"


class String(Value):
    """ """

    def __init__(self, value: str):
        self.value = str(value)
        self.set_pos()
        self.set_context()

    def addition(self, other):
        if isinstance(other, String):
            return String(self.value + other.value), None
        elif isinstance(other, (Number, Boolean)):
            return String(self.value + str(other)), None
        return self._op_error("addition")

    def multiplication(self, other):
        if isinstance(other, Number) and isinstance(other.value, int):
            if other.value < 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "String multiplication requires a non-negative integer power factor.",
                )
            return String(self.value * other.value), None
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "String multiplication requires an integer factor.",
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
     - `const x : Empty   // Be careful because (x) cannot be changeable after this`
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
    def __init__(self):
        self.set_pos()
        self.set_context()

    def is_equal(self, other):
        # IEEE semantics: NaN is unequal to everything, including itself.
        return Boolean(False), None

    def not_equal(self, other):
        return Boolean(True), None

    def true_(self):
        return False

    def __repr__(self):
        return "nan"


class Inf(Value):
    """Signed infinity.

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
        # Infinities are equal only to another infinity of the SAME sign;
        # +inf == -inf is false. Any other value simply compares false.
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
                "Cannot mutate a const list/array (it is immutable). Use 'var' for mutable collections.",
            )
        return None

    # ---------- index helpers ----------

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
                f"Insert index {index} is out of bounds for length {n}.",
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
                f"Index {index} is out of bounds for length {n}.",
            )
        return i, None

    # ---------- in-place mutation methods ----------

    def push(self, element, index=None):
        """Insert at index (or append when index is omitted). In place."""
        err = self._check_mutable()
        if err:
            return None, err
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
        self.list_of_elements.append(element)
        return None, None

    def swap(self, element, index):
        """Replace the element at index. In place."""
        err = self._check_mutable()
        if err:
            return None, err
        i, err = self._resolve_access_index(index)
        if err:
            return None, err
        self.list_of_elements[i] = element
        return None, None

    def delete(self, index):
        """Remove a single element by index. In place."""
        err = self._check_mutable()
        if err:
            return None, err
        i, err = self._resolve_access_index(index)
        if err:
            return None, err
        del self.list_of_elements[i]
        return None, None

    def drop(self, start, end):
        """Remove slice [start:end] in place; return it as a new List. Clamps like slice `l[s..e]`."""
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
        del self.list_of_elements[s:e]
        return List(removed), None

    def assign_at(self, index, element):
        """Dynamic index assignment: replaces if in bounds, extends if at/past end."""
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
                f"Index {index} is out of bounds for length {n}.",
            )
        if i < n:
            # validate element type if this is a typed Array (overridden in Array)
            self.list_of_elements[i] = element
            return None, None
        # dynamic growth: extend with none (Empty) up to i, then append
        while len(self.list_of_elements) < i:
            self.list_of_elements.append(
                Empty().set_pos(self.pos_start, self.pos_end).set_context(self.context)
            )
        self.list_of_elements.append(element)
        # if we extended, we now have i+1 elements; but if i == n we just appended, if i > n we padded
        # For i == n case, the while loop didn't run and append gives correct
        # For i > n, we padded to i then appended -> length i+1 correct
        # However the above does: while len < i: append Empty, then append element -> for i = n+5, we pad 5 empties then element
        return None, None

    # ---------- arithmetic ----------

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
        if isinstance(other, Number):
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
                    f"List multiplication requires both lists to be the same size, got {len(self.list_of_elements)} and {len(other.list_of_elements)}.",
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
            f"Unsupported type '{type(other).__name__}' for list multiplication.",
        )

    def division(self, other):
        if isinstance(other, Number):
            # Fix 5: division by zero must be a hard error (math language semantics).
            # Keep silent refusal for non-numeric element types (e.g. "x" / 2),
            # but propagate div-by-zero.
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero.",
                )
            new_elements = []
            for element in self.list_of_elements:
                res, error = element.division(other)
                if error:
                    if error.details and "division by zero" in error.details.lower():
                        return None, error
                    # Silent refusal for type errors (e.g. "x" / 2) preserves size
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
                "Division between two lists is not supported.",
            )

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            f"Unsupported type '{type(other).__name__}' for list division.",
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
    """Typed array: element type enforced on every mutation."""

    def __init__(self, element_type_class, list_of_elements=None):
        self.element_type = element_type_class
        self.set_pos()
        self.set_context()
        self.list_of_elements = list_of_elements if list_of_elements is not None else []
        self.is_const = False

    # Mutations validate the element type first, then behave exactly like a list.

    def push(self, element, index=None):
        err = self._validate_element(element)
        if err:
            return None, err
        return List.push(self, element, index)

    def append(self, element):
        err = self._validate_element(element)
        if err:
            return None, err
        return List.append(self, element)

    def swap(self, element, index):
        err = self._validate_element(element)
        if err:
            return None, err
        return List.swap(self, element, index)

    def _validate_element(self, element):
        if isinstance(element, Empty):
            # V6: only Empty[] may hold none; Number[]/String[]/Bool[] must not
            if self.element_type is Empty:
                return None
            return RunTimeError(
                self.pos_start,
                self.pos_end,
                f"Expected {self.element_type.__name__} element, got Empty (none). Use Empty[] for none values.",
            )
        if isinstance(element, self.element_type):
            return None
        # Support arrays of arrays: allow List (including typed Array) whose
        # leaves are all of the expected element type. Empty only allowed for Empty[].
        if isinstance(element, List):
            stack = [element]
            while stack:
                cur = stack.pop()
                for item in cur.list_of_elements:
                    if isinstance(item, Empty):
                        if self.element_type is Empty:
                            continue
                        return RunTimeError(
                            self.pos_start,
                            self.pos_end,
                            f"Expected {self.element_type.__name__} element, got Empty inside nested list.",
                        )
                    if isinstance(item, self.element_type):
                        continue
                    if isinstance(item, List):
                        stack.append(item)
                        continue
                    return RunTimeError(
                        self.pos_start,
                        self.pos_end,
                        f"Expected {self.element_type.__name__} element, got {type(item).__name__} inside nested list.",
                    )
            return None
        return RunTimeError(
            self.pos_start,
            self.pos_end,
            f"Expected {self.element_type.__name__} element, got {type(element).__name__}.",
        )

    def _validate_all(self):
        for el in self.list_of_elements:
            err = self._validate_element(el)
            if err:
                return err
        return None

    def multiplication(self, other):
        if isinstance(other, (Number, List)):
            elements, error = List.multiplication(self, other)
            if error:
                return None, error
            return self._new_array(elements.list_of_elements), None

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            f"Unsupported type '{type(other).__name__}' for array multiplication.",
        )

    def division(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero.",
                )
            elements, error = List.division(self, other)
            if error:
                return None, error
            return self._new_array(elements.list_of_elements), None

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Division between two arrays or lists is not supported.",
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
            arr = Array(self.element_type, elements)
        else:
            arr = type(self)(elements)
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
        """Remove slice [start:end] in place; return it as same typed array. Clamps like slice."""
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
        del self.list_of_elements[s:e]
        return self._new_array(removed), None

    def assign_at(self, index, element):
        """Dynamic assignment for typed arrays – validates type then delegates with type-appropriate padding."""
        err = self._validate_element(element)
        if err:
            return None, err
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
                f"Index {index} is out of bounds for length {n}.",
            )
        if i < n:
            self.list_of_elements[i] = element
            return None, None

        # dynamic growth: pad with type-default values
        def _default():
            if self.element_type is Number:
                return (
                    Number(0)
                    .set_pos(self.pos_start, self.pos_end)
                    .set_context(self.context)
                )
            if self.element_type is String:
                return (
                    String("")
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
            self.list_of_elements.append(_default())
        self.list_of_elements.append(element)
        return None, None

    def __repr__(self):
        return f"{self.list_of_elements}"


class NumberArray(Array):
    def __init__(self, list_of_elements=None):
        super().__init__(Number, list_of_elements)


class StringArray(Array):
    def __init__(self, list_of_elements=None):
        super().__init__(String, list_of_elements)


class BooleanArray(Array):
    def __init__(self, list_of_elements=None):
        super().__init__(Boolean, list_of_elements)


class EmptyArray(Array):
    def __init__(self, list_of_elements=None):
        super().__init__(Empty, list_of_elements)


class Tuple(Value):
    """
    A complex datatype representing an immutable container of data.
    """


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
        # Inherit function flag from the nearest enclosing scope
        if in_function is None:
            in_function = bool(
                getattr(loop_context, "in_function", False)
                or getattr(write_to, "in_function", False)
            )
        super().__init__(
            "<loop body>", loop_context, in_loop=in_loop, in_function=in_function
        )
        self._write_to = write_to

    def define(self, name, data_type, value, is_const=False):
        return self._write_to.variables.set_pos(
            self.variables.pos_start, self.variables.pos_end
        ).define(name, data_type, value, is_const)


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

    def define(self, name, data_type, value, is_const=False):
        """Declares a new variable in current environment scope."""

        # 1. Check for redefinition
        if name in self.variables:
            return None, AssignmentError(
                self.pos_start,
                self.pos_end,
                f"Attempting to redefine '{name}' which was already defined.",
            )

        # 2. Check for type mismatch
        type_error = self._type_mismatch_error(data_type, value)
        if type_error:
            return None, type_error

        # 3. For const collections, deep copy so `const b = a` does not mutate `a`
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
                        new_v = Array(v.element_type, new_elements)
                    else:
                        new_v = type(v)(new_elements)
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

        # 4. Store symbol entry
        self.variables[name] = {
            "type": data_type,
            "value": value,
            "is_const": is_const,
        }
        return value, None

    def assign(self, name, value, pos_start=None, pos_end=None):
        """Updates an existing variable value."""

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        # Check existence
        if name not in self.variables:
            if self.parent is not None:
                return self.parent.assign(name, value, pos_start, pos_end)
            return None, AssignmentError(
                pos_start,
                pos_end,
                f"Attempting to access an unassigned variable '{name}'.",
            )

        entry = self.variables[name]

        # Check immutability (const)
        if entry["is_const"]:
            return None, ModificationError(
                pos_start,
                pos_end,
                f"Cannot change value of '{name}' of type const.",
            )

        # Check type compatibility
        type_error = self._type_mismatch_error(entry["type"], value, pos_start, pos_end)
        if type_error:
            return None, type_error

        # Update value
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
                f"'{name}' is not defined.",
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
                f"'{name}' is not defined.",
            )
        return self.variables[name]["type"], None

    def _type_mismatch_error(self, data_type, value, pos_start=None, pos_end=None):
        """Validates value type against declared variable type."""

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        if data_type is None:  # Weakly typed variable will accept any value
            return None

        if value is None:  # Uninitialized value is treated as `none`
            return None

        # Explicit Empty declaration requires an Empty instance
        if data_type is Empty:
            if isinstance(value, Empty):
                return None
            val_type_str = type(value).__name__
            return AssignmentError(
                pos_start,
                pos_end,
                f"Cannot assign value of type {val_type_str} to a variable declared with Empty.",
            )

        # Strongly typed variable: only accepts exact type (Empty not allowed for non-Empty types)
        if isinstance(value, data_type):
            return None

        val_type_str = type(value).__name__
        return AssignmentError(
            pos_start,
            pos_end,
            f"Cannot assign value of type {val_type_str} to a variable declared with {data_type.__name__}.",
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
        self.arg_nodes = arg_nodes  # List of tuples: (param_name_tok, param_type_tok)
        self.return_type_tok = return_type_tok
        self.return_type = (
            TYPE_MAP.get(return_type_tok.value) if return_type_tok else None
        )
        self.set_context(parent_context)
        self.set_pos()

    def execute(self, args, interpreter, call_pos_start=None, call_pos_end=None):
        from B_Sharp.ASTNodes.parser import RunTimeResult

        res = RunTimeResult()

        err_pos_start = call_pos_start or self.pos_start
        err_pos_end = call_pos_end or self.pos_end

        exec_context = Context(
            display_name=f"<function {self.name}>",
            parent=self.context,
            parent_entry_pos=self.pos_start,
            in_function=True,
        )

        if len(args) != len(self.arg_nodes):
            expected_count = len(self.arg_nodes)
            arg_label = "argument" if expected_count == 1 else "arguments"

            return res.failure(
                RunTimeError(
                    err_pos_start,
                    err_pos_end,
                    f"Function '{self.name}' expects {expected_count} {arg_label}, but got {len(args)}.",
                )
            )

        for i in range(len(args)):
            param_name_tok, param_type_tok = self.arg_nodes[i]
            arg_value = args[i]

            param_type = TYPE_MAP.get(param_type_tok.value) if param_type_tok else None

            if (
                param_type
                and issubclass(param_type, Array)
                and isinstance(arg_value, List)
            ):
                array_class = TYPE_MAP.get(param_type_tok.value)
                if array_class:
                    arg_value = array_class(arg_value.list_of_elements)
                    arg_value.set_pos(err_pos_start, err_pos_end)
                    err = arg_value._validate_all()
                    if err:
                        return res.failure(err)

            _, err = exec_context.variables.set_pos(
                param_name_tok.pos_start, param_name_tok.pos_end
            ).define(
                name=param_name_tok.value,
                data_type=param_type,
                value=arg_value,
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
                array_class = TYPE_MAP.get(self.return_type_tok.value)
                if array_class:
                    return_val = array_class(return_val.list_of_elements)
                    return_val.set_pos(err_pos_start, err_pos_end)
                    err = return_val._validate_all()
                    if err:
                        return res.failure(err)

            if not isinstance(return_val, self.return_type) and not (
                self.return_type is Empty and isinstance(return_val, Empty)
            ):
                val_type_str = type(return_val).__name__
                return res.failure(
                    RunTimeError(
                        err_pos_start,
                        err_pos_end,
                        f"Function '{self.name}' returned type {val_type_str}, expected {self.return_type.__name__}.",
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


# A helper dictionary for all declared types.
# Only these canonical uppercase spellings are valid type annotations.
TYPE_MAP = {
    "Bool": Boolean,
    "Number": Number,
    "String": String,
    "Inf": Inf,
    "NaN": NaN,
    "Empty": Empty,
    "List": List,
    "Function": Function,
    "Number[]": NumberArray,
    "String[]": StringArray,
    "Boolean[]": BooleanArray,
    "Bool[]": BooleanArray,
    "Empty[]": EmptyArray,
}
