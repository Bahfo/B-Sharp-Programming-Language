# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# (Simple Abstracted Syntax Language)
# The code is guarded and licensed under the GPLv3 License.
# ----------------------------------------------------------------
# Module: instances.py: All B_Sharp datatypes and environment
# needed-to-define keyword instances (functions, variables, etc.).

from B_Sharp.errors import *


class Number:
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

    def set_context(self, context=None):
        self.context = context
        return self

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def addition(self, other):
        if isinstance(other, Number):
            return Number(self.value + other.value), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for addition operation.",
            )

    def subtraction(self, other):
        if isinstance(other, Number):
            return Number(self.value - other.value), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for subtraction operation.",
            )

    def multiplication(self, other):
        if isinstance(other, Number):
            return Number(self.value * other.value), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for multiplication operation.",
            )

    def division(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero.",
                )
            return Number(self.value / other.value), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for division operation.",
            )

    def integer_division(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    "Unallowed division by zero.",
                )
            return Number(int(self.value // other.value)), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for division operation.",
            )

    def power(self, power_factor):
        if isinstance(power_factor, Number):
            try:
                result = self.value**power_factor.value
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
            return Number(result), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for power operation.",
            )

    def _to_number(self, other):
        if isinstance(other, Boolean):
            return Number(1 if other.value else 0)
        return other

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
        if isinstance(other, (Number, Boolean)):
            other = self._to_number(other)
            return Boolean(self.value < other.value), None
        return Boolean(False), None

    def greater_than(self, other):
        if isinstance(other, (Number, Boolean)):
            other = self._to_number(other)
            return Boolean(self.value > other.value), None
        return Boolean(False), None

    def less_than_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other = self._to_number(other)
            return Boolean(self.value <= other.value), None
        return Boolean(False), None

    def greater_than_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other = self._to_number(other)
            return Boolean(self.value >= other.value), None
        return Boolean(False), None

    def and_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def not_(self):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'not' operation.",
        )

    def true_(self):
        return self.value != 0

    def __repr__(self):
        return str(self.value)


class Boolean:
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

    def set_context(self, context=None):
        self.context = context
        return self

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def _to_number(self, other):
        if isinstance(other, Boolean):
            return Number(1 if other.value else 0)
        return other

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
        if isinstance(other, (Number, Boolean)):
            other_num = self._to_number(other)
            my_num = Number(1 if self.value else 0)
            return Boolean(my_num.value < other_num.value), None
        return Boolean(False), None

    def greater_than(self, other):
        if isinstance(other, (Number, Boolean)):
            other_num = self._to_number(other)
            my_num = Number(1 if self.value else 0)
            return Boolean(my_num.value > other_num.value), None
        return Boolean(False), None

    def less_than_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other_num = self._to_number(other)
            my_num = Number(1 if self.value else 0)
            return Boolean(my_num.value <= other_num.value), None
        return Boolean(False), None

    def greater_than_equal(self, other):
        if isinstance(other, (Number, Boolean)):
            other_num = self._to_number(other)
            my_num = Number(1 if self.value else 0)
            return Boolean(my_num.value >= other_num.value), None
        return Boolean(False), None

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

    def addition(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for addition operation.",
        )

    def subtraction(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for subtraction operation.",
        )

    def multiplication(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for multiplication operation.",
        )

    def division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def integer_division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def power(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for power operation.",
        )

    def true_(self):
        return self.value

    def __repr__(self):
        return "true" if self.value == True else "false"


class Complex:
    pass


class String:
    """ """

    def __init__(self, value: str):
        self.value = str(value)
        self.set_pos()
        self.set_context()

    def set_context(self, context=None):
        self.context = context
        return self

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def addition(self, other):
        if isinstance(other, String):
            return String(self.value + other.value), None
        elif isinstance(other, (Number, Boolean)):
            return String(self.value + str(other)), None
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for string addition.",
        )

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

    def subtraction(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for string subtraction.",
        )

    def division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def integer_division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def power(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for string power operation.",
        )

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

    def not_(self):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'not' operation.",
        )

    def and_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def true_(self):
        return len(self.value) > 0

    def get_index(self, index):
        i = int(index)
        if i < 0:
            i += len(self.value)
        if i < 0 or i >= len(self.value):
            return None, RunTimeError(
                self.pos_start, self.pos_end, "Index out of bounds"
            )
        return String(self.value[i]), None

    def get_slice(self, start, end):
        return String(self.value[start:end]), None

    def __repr__(self):
        return f'"{self.value}"'


class Empty:
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
        self.set_pos()
        self.set_context()

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def true_(self):
        return False

    def addition(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for addition operation.",
        )

    def subtraction(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for subtraction operation.",
        )

    def multiplication(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for multiplication operation.",
        )

    def division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def integer_division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def power(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for power operation.",
        )

    def and_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def not_(self):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'not' operation.",
        )

    def is_equal(self, other):
        if isinstance(other, Empty):
            return Boolean(True), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, Empty):
            return Boolean(False), None
        return Boolean(True), None

    def less_than(self, other):
        return Boolean(False), None

    def greater_than(self, other):
        return Boolean(False), None

    def less_than_equal(self, other):
        return Boolean(False), None

    def greater_than_equal(self, other):
        return Boolean(False), None

    def __repr__(self):
        return "none"


class NaN:
    pass


class Reference:
    pass


class List:
    """
    A complex datatype representing a collection of data.

    Introduction:\n
    A list is a datatype that holds a collection of other complex or atomic
    data types. It can hold.
    """

    def __init__(self, list_of_elements: list):
        self.set_pos()
        self.set_context()
        self.list_of_elements = list_of_elements

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def append(self, element):
        self.list_of_elements.append(element)

    def push(self, element, index=None):
        """
        Insert element at index (or append if index is None).
        Returns new List.
        """
        new_elements = self.list_of_elements.copy()
        if index is None:
            new_elements.append(element)
        else:
            new_elements.insert(int(index), element)
        return List(new_elements)

    def drop(self, index):
        """
        Remove element at index. Returns new List.
        """
        new_elements = self.list_of_elements.copy()
        del new_elements[int(index)]
        return List(new_elements)

    def delete(self, start, end):
        """
        Remove elements from start to end (exclusive).
        Returns new List.
        """
        new_elements = self.list_of_elements.copy()
        del new_elements[int(start) : int(end)]
        return List(new_elements)

    def multiplication(self, other):
        if isinstance(other, Number):
            new_elements = []
            for element in self.list_of_elements:
                res, error = element.multiplication(other)
                if not error:
                    new_elements.append(res)
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
            for i, j in zip(self.list_of_elements, other.list_of_elements):
                res, error = i.multiplication(j)
                if not error:
                    new_elements.append(res)
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

    def _reversed_multiplication(self, other):
        return self.multiplication(other)

    def addition(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list addition.",
        )

    def subtraction(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list subtraction.",
        )

    def division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list division.",
        )

    def integer_division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list integer division.",
        )

    def power(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list power operation.",
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

    def not_equal(self, other):
        res, error = self.is_equal(other)
        if error:
            return res, error
        return Boolean(not res.value), None

    def less_than(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list less than comparison.",
        )

    def greater_than(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list greater than comparison.",
        )

    def less_than_equal(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list less than or equal comparison.",
        )

    def greater_than_equal(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for list greater than or equal comparison.",
        )

    def and_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def not_(self):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'not' operation.",
        )

    def true_(self):
        return Boolean(len(self.list_of_elements) > 0)

    def copy(self):
        copy = List(self.list_of_elements[:])
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return f"{self.list_of_elements}"


class Array:
    """Base class for typed arrays. Element type is enforced at assignment time."""

    def __init__(self, element_type_class, list_of_elements=None):
        self.element_type = element_type_class
        self.list_of_elements = list_of_elements or []
        self.set_pos()
        self.set_context()

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def push(self, element, index=None):
        """
        Insert element at index (or append if index is None).
        Returns new List.
        """
        if isinstance(self._validate_element(element), RunTimeError):
            return
        new_elements = self.list_of_elements.copy()
        if index is None:
            new_elements.append(element)
        else:
            new_elements.insert(int(index), element)
        return List(new_elements)

    def drop(self, index):
        """
        Remove element at index. Returns new List.
        """
        new_elements = self.list_of_elements.copy()
        del new_elements[int(index)]
        return List(new_elements)

    def delete(self, start, end):
        """
        Remove elements from start to end (exclusive).
        Returns new List.
        """
        new_elements = self.list_of_elements.copy()
        del new_elements[int(start) : int(end)]
        return List(new_elements)

    def _validate_element(self, element):
        if isinstance(element, Empty):
            return None
        if isinstance(element, self.element_type):
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
        if isinstance(other, Number):
            new_elements = []
            for element in self.list_of_elements:
                res, error = element.multiplication(other)
                if not error:
                    new_elements.append(res)
            return self._new_array(new_elements), None

        if isinstance(other, Array):
            if not isinstance(other, type(self)):
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    f"Cannot perform element-wise multiplication between {type(self).__name__} and {type(other).__name__}.",
                )
            if len(self.list_of_elements) != len(other.list_of_elements):
                return None, RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    f"Array multiplication requires both arrays to be the same size, got {len(self.list_of_elements)} and {len(other.list_of_elements)}.",
                )
            new_elements = []
            for a, b in zip(self.list_of_elements, other.list_of_elements):
                res, error = a.multiplication(b)
                if not error:
                    new_elements.append(res)
            return self._new_array(new_elements), None

        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            f"Unsupported type '{type(other).__name__}' for array multiplication.",
        )

    def _reversed_multiplication(self, other):
        return self.multiplication(other)

    def addition(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array addition.",
        )

    def subtraction(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array subtraction.",
        )

    def division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array division.",
        )

    def integer_division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array integer division.",
        )

    def power(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array power operation.",
        )

    def is_equal(self, other):
        if isinstance(other, Array) and type(self) is type(other):
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

    def less_than(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array less than comparison.",
        )

    def greater_than(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array greater than comparison.",
        )

    def less_than_equal(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array less than or equal comparison.",
        )

    def greater_than_equal(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unsupported operand type for array greater than or equal comparison.",
        )

    def and_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def not_(self):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'not' operation.",
        )

    def true_(self):
        return Boolean(len(self.list_of_elements) > 0)

    def _new_array(self, elements):
        arr = type(self)(elements)
        arr.set_pos(self.pos_start, self.pos_end)
        arr.set_context(self.context)
        return arr

    def copy(self):
        return self._new_array(self.list_of_elements[:])

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


class Context:
    """
    Runtime scope holding the variables table that persists across statements.
    """

    def __init__(
        self,
        display_name,
        parent=None,
        parent_entry_pos=None,
        redefine=False,
        in_function=False,
    ):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.in_function = in_function
        self.variables = EnvironmentVariable(parent.variables if parent else None)
        self.variables.allow_redefine = redefine


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
        self.allow_redefine = False
        self.set_pos()

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def define(self, name, data_type, value, is_const=False):
        """Declares a new variable in current environment scope."""

        # 1. Check for redefinition
        if name in self.variables:
            if self.allow_redefine:
                entry = self.variables[name]
                if entry["is_const"]:
                    return None, ModificationError(
                        self.pos_start,
                        self.pos_end,
                        f"Cannot change value of '{name}' of type const.",
                    )
                type_error = self._type_mismatch_error(entry["type"], value)
                if type_error:
                    return None, type_error
                entry["value"] = value
                return value, None

            return None, AssignmentError(
                self.pos_start,
                self.pos_end,
                f"Attempting to redefine '{name}' which was already defined.",
            )

        # 2. Check for type mismatch
        type_error = self._type_mismatch_error(data_type, value)
        if type_error:
            return None, type_error

        # 3. Store symbol entry
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

        # Strongly typed variable will accepts target type OR Empty (none)
        if isinstance(value, data_type) or isinstance(value, Empty):
            return None

        val_type_str = type(value).__name__
        return AssignmentError(
            pos_start,
            pos_end,
            f"Cannot assign value of type {val_type_str} to a variable declared with {data_type.__name__}.",
        )


class Function:
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

    def set_context(self, context=None):
        self.context = context
        return self

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

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

    def addition(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for addition operation.",
        )

    def subtraction(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for subtraction operation.",
        )

    def multiplication(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for multiplication operation.",
        )

    def division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def integer_division(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for division operation.",
        )

    def power(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for power operation.",
        )

    def and_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'and' operation.",
        )

    def or_(self, other):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'or' operation.",
        )

    def not_(self):
        return None, RunTimeError(
            self.pos_start,
            self.pos_end,
            "Unexpected type for 'not' operation.",
        )

    def is_equal(self, other):
        if isinstance(other, Function):
            return Boolean(self is other), None
        return Boolean(False), None

    def not_equal(self, other):
        if isinstance(other, Function):
            return Boolean(self is not other), None
        return Boolean(True), None

    def less_than(self, other):
        return Boolean(False), None

    def greater_than(self, other):
        return Boolean(False), None

    def less_than_equal(self, other):
        return Boolean(False), None

    def greater_than_equal(self, other):
        return Boolean(False), None

    def true_(self):
        return True

    def __repr__(self):
        return f"<function {self.name}>"


class OverloadSet:
    """
    A supportive declaration for functions. It basically is the key behind
    overloading and overwriting in B-Sharp.

    Overloading: The process of overloading is defining an already defined
    function by keeping *same identifier*, but with *different parameter
    signature*.

    Overwriting: The process of completely replacing an existing signature
    or in other words *redeclaring the existing signature in the same
    context.*
    """

    def __init__(self, name):
        self.name = name

        # A helper dictionary to map a signature key to a function's instance.
        # Key format: (arity, args)
        self.variants = {}

    def get_signature_key(self, func):
        """
        Extracts a key based on parameter count and type names
        """


# A helper dictionary for all declared types before.
# Keys are normalized to lowercase so both `Number` and `number` resolve.
TYPE_MAP = {
    "Bool": Boolean,
    "Number": Number,
    "String": String,
    "Empty": Empty,
    "List": List,
    "Function": Function,
    "Number[]": NumberArray,
    "String[]": StringArray,
    "Boolean[]": BooleanArray,
    "Empty[]": EmptyArray,
}
