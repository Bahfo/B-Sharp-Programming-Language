import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest

from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser, Interpreter
from B_Sharp.ASTNodes.instances import Context


def run_code(code_str, context):
    lexer = Lexer("<test>", code_str)
    tokens, error = lexer.tokenize()
    if error:
        return None, error

    parser = Parser(tokens)
    ast = parser.parser()
    if ast.error:
        return None, ast.error

    interpreter = Interpreter()
    result = interpreter.visit(ast.node, context)
    return result.value, result.error


class TestComparisonsAndLogic(unittest.TestCase):
    """Comparison & logical operation coverage.

    Mirrors the original script-style suite: all cases share one global
    context so later sections can reference variables from earlier ones.
    """

    ctx = None

    @classmethod
    def setUpClass(cls):
        cls.ctx = Context("<global>")

    def check(self, code, expect_error=False):
        val, error = run_code(code, self.ctx)
        if expect_error:
            self.assertIsNotNone(error, f"expected error for: {code}")
        else:
            self.assertIsNone(error, f"{code}: {error}")
        return val

    # ── 1. Equality (==) ─────────────────────────────────────
    def test_equality(self):
        for code in [
            "5 == 5",
            "5 == 6",
            "3.14 == 3.14",
            "3.14 == 3.15",
            "0 == 0",
            "-5 == -5",
            "-5 == 5",
            "1 == 1.0",
        ]:
            self.check(code)

    # ── 2. Inequality (!=) ───────────────────────────────────
    def test_inequality(self):
        for code in [
            "5 != 6",
            "5 != 5",
            "3.14 != 3.15",
            "0 != 1",
            "-5 != 5",
        ]:
            self.check(code)

    # ── 3. Less Than (<) ─────────────────────────────────────
    def test_less_than(self):
        for code in [
            "5 < 10",
            "10 < 5",
            "5 < 5",
            "-5 < 0",
            "-10 < -5",
            "3.14 < 3.15",
            "3.15 < 3.14",
        ]:
            self.check(code)

    # ── 4. Greater Than (>) ──────────────────────────────────
    def test_greater_than(self):
        for code in [
            "10 > 5",
            "5 > 10",
            "5 > 5",
            "0 > -5",
            "-5 > -10",
            "3.15 > 3.14",
        ]:
            self.check(code)

    # ── 5/6. <= and >= ───────────────────────────────────────
    def test_less_or_equal(self):
        for code in ["5 <= 10", "5 <= 5", "10 <= 5"]:
            self.check(code)

    def test_greater_or_equal(self):
        for code in ["10 >= 5", "5 >= 5", "5 >= 10"]:
            self.check(code)

    # ── 7. Boolean literals ──────────────────────────────────
    def test_boolean_literals(self):
        for code in [
            "true",
            "false",
            "true == true",
            "false == false",
            "true == false",
            "true != false",
            "true != true",
        ]:
            self.check(code)

    # ── 8. Cross-type: Number vs Boolean ─────────────────────
    def test_cross_type_number_boolean(self):
        for code in [
            "1 == true",
            "5 == true",
            "0 == false",
            "0 != true",
            "1 != false",
            "2 > true",
            "2 > false",
            "0 < true",
            "true == 1",
            "false == 0",
            "false < 1",
            "true <= 1",
            "true >= 1",
            "false >= 0",
        ]:
            self.check(code)

    # ── 9-11. Logical AND / OR / NOT ─────────────────────────
    def test_logical_and(self):
        for code in [
            "true and true",
            "true and false",
            "false and true",
            "false and false",
        ]:
            self.check(code)

    def test_logical_or(self):
        for code in [
            "true or true",
            "true or false",
            "false or true",
            "false or false",
        ]:
            self.check(code)

    def test_unary_not(self):
        for code in [
            "not true",
            "not false",
            "not not true",
            "not not false",
        ]:
            self.check(code)

    # ── 12. Combined logical expressions ─────────────────────
    def test_combined_logical(self):
        for code in [
            "(5 > 3) and (2 < 4)",
            "(5 > 3) and (2 > 4)",
            "(5 < 3) and (2 < 4)",
            "(5 > 3) or (2 > 4)",
            "(5 < 3) or (2 > 4)",
            "(5 < 3) or (2 < 4)",
            "not (5 > 3)",
            "not (3 > 5)",
            "not (5 > 3) and (2 < 4)",
            "not (5 > 3) or (2 < 4)",
        ]:
            self.check(code)

    # ── 13. Operator precedence ──────────────────────────────
    def test_operator_precedence(self):
        for code in [
            "2 + 3 > 4",
            "2 + 3 == 5",
            "2 * 3 == 6",
            "2 * 3 != 5",
            "10 / 2 == 5",
            "2 + 3 * 2 > 7",
            "2 ^ 3 == 8",
            "true and 2 + 3 == 5",
            "(2 + 3) > 4 and (5 - 1) == 4",
        ]:
            self.check(code)

    # ── 14. Parenthesized expressions ────────────────────────
    def test_parenthesized(self):
        for code in [
            "(5 > 3)",
            "((5 > 3))",
            "(2 + 3) == 5",
            "(true and false) or true",
        ]:
            self.check(code)

    # ── 15. Comparisons with variables ───────────────────────
    def test_comparisons_with_variables(self):
        for code in [
            "var x = 10",
            "x > 5",
            "x == 10",
            "x != 5",
            "x <= 10",
            "x >= 10",
            "var y = true",
            "y and true",
            "y == true",
            "x > 5 and y == true",
        ]:
            self.check(code)

    # ── 16. Strong typing enforcement ────────────────────────
    def test_strong_typing(self):
        for code in [
            "var a : Bool = true",
            "var b : Bool = false",
            "var c : Bool = 5 > 3",
            "var d : Bool = 1 == 1",
        ]:
            self.check(code)
        for code in [
            "var e : Bool = 5",
            "var f : Number = true",
            "var g : Number = 5 > 3",
            "var h : Number = true and false",
        ]:
            self.check(code, expect_error=True)

    # ── 17. Comparisons in variable assignments ──────────────
    def test_comparison_assignments(self):
        for code in [
            "var p = 10 > 5",
            "var q = 10 == 10",
            "var r = true and false",
            "var s = not true",
        ]:
            self.check(code)

    # ── 18. Boundary values ──────────────────────────────────
    def test_boundary_values(self):
        for code in [
            "0 == 0",
            "0 != 1",
            "0 > -1",
            "0 < 1",
            "0 >= 0",
            "0 <= 0",
            "-1 == -1",
            "-1 < 0",
            "-1 > -2",
            "999999 == 999999",
            "1.0000001 > 1",
        ]:
            self.check(code)

    # ── 19. Invalid operations ───────────────────────────────
    def test_invalid_operations(self):
        # Arithmetic strictly requires numbers; comparisons coerce booleans.
        for code in ["5 + true", "true + 5", "true and 5", "5 and true", "false or 5"]:
            self.check(code, expect_error=True)
        # 'or' short-circuits before reaching the number.
        self.check("true or 5")


if __name__ == "__main__":
    unittest.main()
