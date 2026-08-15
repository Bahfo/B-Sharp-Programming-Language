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
            "String multiplication requires an integer power factor.",
        )

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

    def true_(self):
        return len(self.value) > 0

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

    def __repr__(self):
        return "none"


class NaN:
    pass


class Reference:
    pass


class Context:
    """
    Runtime scope holding the variables table that persists across statements.
    """

    def __init__(
        self, display_name, parent=None, parent_entry_pos=None, redefine=False
    ):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
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

    def _type_mismatch_error(self, data_type, value, pos_start=None, pos_end=None):
        """Validates value type against declared variable type."""

        if pos_start is None:
            pos_start, pos_end = self.pos_start, self.pos_end

        if data_type is None:  # Weakly typed variable will accepts any value
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
            TYPE_MAP.get(return_type_tok.value.lower()) if return_type_tok else None
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

    def execute(self, args, interpreter):
        from B_Sharp.ASTNodes.parser import RunTimeResult

        res = RunTimeResult()

        exec_context = Context(
            display_name=f"<function {self.name}>",
            parent=self.context,
            parent_entry_pos=self.pos_start,
        )

        if len(args) != len(self.arg_nodes):
            return res.failure(
                RunTimeError(
                    self.pos_start,
                    self.pos_end,
                    f"Function '{self.name}' expects {len(self.arg_nodes)} arguments, but got {len(args)}.",
                )
            )

        for i in range(len(args)):
            param_name_tok, param_type_tok = self.arg_nodes[i]
            arg_value = args[i]

            param_type = (
                TYPE_MAP.get(param_type_tok.value.lower()) if param_type_tok else None
            )

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
            if not isinstance(return_val, self.return_type) and not (
                self.return_type is Empty and isinstance(return_val, Empty)
            ):
                val_type_str = type(return_val).__name__
                return res.failure(
                    RunTimeError(
                        self.pos_start,
                        self.pos_end,
                        f"Function '{self.name}' returned type {val_type_str}, expected {self.return_type.__name__}.",
                    )
                )

        return res.success(return_val)

    def true_(self):
        return True

    def __repr__(self):
        return f"<function {self.name}>"


# A helper dictionary for all declared types before.
# Keys are normalized to lowercase so both `Number` and `number` resolve.
TYPE_MAP = {
    "boolean": Boolean,
    "bool": Boolean,
    "number": Number,
    "int": Number,
    "float": Number,
    "string": String,
    "empty": Empty,
    "complex": Complex,
    "nan": NaN,
    "function": Function,
}
