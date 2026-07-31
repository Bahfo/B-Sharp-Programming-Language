from SASL.errors import *


class Number:
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

    def power(self, power_factor):
        if isinstance(power_factor, Number):
            return Number(self.value**power_factor.value), None

        else:
            return None, RunTimeError(
                self.pos_start,
                self.pos_end,
                "Unexpected type for power operation.",
            )

    def __repr__(self):
        return str(self.value)


class Boolean:
    pass


class Complex:
    pass


class String:
    pass


class Empty:
    pass


class NaN:
    pass


class Reference:
    pass


class EnvironmentVariable:
    def __init__(self):
        self.set_pos()
        self.variables = {}

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def define(self, name, value, is_const=False):
        if name in self.variables:
            return AssignmentError(
                self.pos_start,
                self.pos_end,
                f"Attempting to redefine {name} which was already defined.",
            )

        self.variables[name] = {"value": value, "is_const": is_const}

    def assign(self, name, value):
        if name not in self.variables:
            return AssignmentError(
                self.pos_start,
                self.pos_end,
                f"Attempting to access an unassigned variable {name}",
            )

        elif self.variables[name]["is_const"]:
            return ModificationError(
                self.pos_start,
                self.pos_end,
                f"Cannot change value of {name} of type const.",
            )

        self.variables[name]["value"] = value

    def get(self, name):
        if name in self.variables:
            return AssignmentError(
                self.pos_start,
                self.pos_end,
                f"{name} is not defined.",
            )

        return self.variables[name]["value"]
