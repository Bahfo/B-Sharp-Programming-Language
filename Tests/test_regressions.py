import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading
import unittest

from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser, Interpreter
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.errors import RunTimeError


def execute_bsharp(source_code):
    """Helper function to execute B# source code and return (value, error)."""
    lexer = Lexer("<test_suite>", source_code)
    tokens, error = lexer.tokenize()
    if error:
        return None, error

    parser = Parser(tokens)
    ast = parser.parser()
    if ast.error:
        return None, ast.error

    interpreter = Interpreter()
    context = Context("<main>")
    result = interpreter.visit(ast.node, context)
    if result.error:
        return None, result.error

    return result.value, None


class TestBooleanAndNoneLiterals(unittest.TestCase):
    def test_boolean_literals_evaluate(self):
        val, err = execute_bsharp("true")
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_false_literal_evaluates(self):
        val, err = execute_bsharp("false")
        self.assertIsNone(err)
        self.assertFalse(val.value)

    def test_boolean_literal_in_variable(self):
        val, err = execute_bsharp("var x = true\nx")
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_none_literal_in_variable(self):
        val, err = execute_bsharp("var x = none\nx")
        self.assertIsNone(err)
        self.assertEqual(repr(val), "none")

    def test_boolean_literal_in_condition(self):
        val, err = execute_bsharp("if true then 1 else 0")
        self.assertIsNone(err)
        self.assertEqual(val.value, 1)

    def test_double_negation(self):
        val, err = execute_bsharp("not not true")
        self.assertIsNone(err)
        self.assertTrue(val.value)


class TestAndOrPrecedence(unittest.TestCase):
    def test_and_binds_tighter_than_or(self):
        # (1<2) or ((5>1) and (2>9)) == true or false == true
        val, err = execute_bsharp(
            "var x = (1 < 2) or (5 > 1) and (2 > 9)\nx"
        )
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_left_associative_or_chain(self):
        val, err = execute_bsharp(
            "var x = (1 > 2) or (3 > 4) or (1 < 2)\nx"
        )
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_mixed_arithmetic_logical(self):
        val, err = execute_bsharp("var x = true and (2 + 3 == 5)\nx")
        self.assertIsNone(err)
        self.assertTrue(val.value)


class TestDivisionSemantics(unittest.TestCase):
    def test_number_division_by_zero(self):
        val, err = execute_bsharp("var x = 1 / 0")
        self.assertIsNotNone(err)
        self.assertEqual(err.error_name.strip(), "RunTime Error")
        self.assertIn("division by zero", err.details.lower())

    def test_boolean_division_type_mismatch(self):
        val, err = execute_bsharp("var x = true / 0")
        self.assertIsNotNone(err)
        self.assertIn("Unexpected type", err.details)

    def test_string_division_type_mismatch(self):
        val, err = execute_bsharp('var x = "abc" / 0')
        self.assertIsNotNone(err)
        self.assertIn("Unexpected type", err.details)

    def test_integer_division(self):
        val, err = execute_bsharp("var x = 7 // 2\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 3)
        self.assertIsInstance(val.value, int)

    def test_integer_division_of_float(self):
        val, err = execute_bsharp("var x = 8.0 // 3\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 2)
        self.assertIsInstance(val.value, int)

    def test_integer_division_by_zero(self):
        val, err = execute_bsharp("var x = 7 // 0")
        self.assertIsNotNone(err)
        self.assertIn("division by zero", err.details.lower())

    def test_power_zero_negative_reports_division(self):
        val, err = execute_bsharp("var x = 0 ^ -1")
        self.assertIsNotNone(err)
        self.assertIn("division by zero", err.details.lower())
        self.assertNotIn("Complex", err.details)


class TestLexerRegressions(unittest.TestCase):
    def test_double_floating_error(self):
        val, err = execute_bsharp("var x = 1.2.3")
        self.assertIsNotNone(err)
        self.assertEqual(err.error_name.strip(), "Double Floating Assigned Error.")

    def test_double_star_not_defined(self):
        val, err = execute_bsharp("var x = 2 ** 3")
        self.assertIsNotNone(err)
        self.assertIn("**", err.details)

    def test_invalid_escape_sequence(self):
        val, err = execute_bsharp('var x = "\\q"')
        self.assertIsNotNone(err)
        self.assertIn("Invalid escape sequence", err.details)

    def test_valid_escapes_still_work(self):
        val, err = execute_bsharp('var x = "a\\nb\\t\\\\"\nx')
        self.assertIsNone(err)
        self.assertEqual(val.value, 'a\nb\t\\')


class TestScopeIsolation(unittest.TestCase):
    def test_variable_declared_in_while_block_not_visible_outside(self):
        code = """
        var s = 0
        while s < 2 {
            var inner = 5
            s = s + 1
        }
        inner
        """
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("not defined", err.details)

    def test_variable_declared_in_if_block_not_visible_outside(self):
        code = """
        if 1 == 1 {
            var t = 5
        }
        t
        """
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("not defined", err.details)

    def test_for_counter_does_not_leak(self):
        code = """
        for (var i = 0; i < 3; i++) { }
        i
        """
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("not defined", err.details)

    def test_loop_body_declaration_across_iterations(self):
        code = """
        var total = 0
        var i = 0
        while i < 3 {
            var tmp = i * 2
            total = total + tmp
            i = i + 1
        }
        total
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 6)

    def test_outer_variable_assignment_from_block(self):
        code = """
        var grade = ""
        if 1 == 1 {
            grade = "A"
        }
        grade
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, "A")

    def test_if_expression_assignment_still_works(self):
        val, err = execute_bsharp('var s = if (1 > 0) then "A" else "B"\ns')
        self.assertIsNone(err)
        self.assertEqual(val.value, "A")


class TestStringOperatorEdges(unittest.TestCase):
    def test_string_subtraction_is_error_not_crash(self):
        val, err = execute_bsharp('var x = "abc" - "a"')
        self.assertIsNotNone(err)
        self.assertIn("string subtraction", err.details)

    def test_string_less_than_lexical(self):
        val, err = execute_bsharp('var x = "abc" < "abd"\nx')
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_string_greater_than_lexical(self):
        val, err = execute_bsharp('var x = "abc" > "abd"\nx')
        self.assertIsNone(err)
        self.assertFalse(val.value)

    def test_string_not_is_error_not_crash(self):
        val, err = execute_bsharp('var x = not "abc"')
        self.assertIsNotNone(err)
        self.assertIn("Unexpected type", err.details)

    def test_string_negative_repetition_is_error(self):
        val, err = execute_bsharp('var x = "a" * -2')
        self.assertIsNotNone(err)
        self.assertIn("non-negative", err.details)


class TestEmptyOperatorEdges(unittest.TestCase):
    def test_negate_empty_is_error_not_crash(self):
        code = "var e\n-e"
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("Unexpected type", err.details)

    def test_empty_addition_is_error_not_crash(self):
        code = "var e\ne + 5"
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("Unexpected type", err.details)

    def test_empty_not_is_error_not_crash(self):
        code = "var e\nnot e"
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("Unexpected type", err.details)


class TestNoneLeakPrevention(unittest.TestCase):
    def test_unmatched_if_assigns_empty_not_python_none(self):
        # x becomes Empty; x + 5 must be a clean RunTimeError, not AttributeError
        code = "var x = if (5 > 9) then 1\nvar y = x + 5"
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIsInstance(err, RunTimeError)


class TestTracebackSafety(unittest.TestCase):
    def test_error_as_string_with_none_position(self):
        err = RunTimeError(None, None, "isolated error")
        rendered = err.as_string()
        self.assertIsInstance(rendered, str)
        self.assertIn("isolated error", rendered)

    def test_increment_value_error_renders(self):
        code = "var a = 5\nvar post = a++\npost + \"x\""
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        rendered = err.as_string()
        self.assertIsInstance(rendered, str)
        self.assertIn("in Line", rendered)

    def test_error_after_empty_else_block_does_not_crash(self):
        code = "if 1 == 2 { 1 } else { }\nvar z = 2\nz"
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 2)

    def test_error_line_number_in_loop_block(self):
        code = "var a = 1\nwhile a < 2 { a = a + 1 }\nmissing_var"
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        rendered = err.as_string()
        self.assertIn("in Line 3", rendered)


class TestReplRedefinition(unittest.TestCase):
    def test_redeclare_var_becomes_reassignment(self):
        from bsharp import run_source

        context = Context("<repl>", redefine=True)
        value, error = run_source("<repl>", "var a = 1", context)
        self.assertIsNone(error)
        value, error = run_source("<repl>", "var a = 2", context)
        self.assertIsNone(error)

        val, err = context.variables.get("a")
        self.assertIsNone(err)
        self.assertEqual(val.value, 2)

    def test_const_still_protected_in_repl(self):
        from bsharp import run_source

        context = Context("<repl>", redefine=True)
        run_source("<repl>", "const c = 5", context)
        value, error = run_source("<repl>", "const c = 6", context)
        self.assertIsNotNone(error)

    def test_typed_var_redeclaration_validates_type(self):
        from bsharp import run_source

        context = Context("<repl>", redefine=True)
        run_source("<repl>", "var n : Number = 1", context)
        value, error = run_source("<repl>", 'var n = "text"', context)
        self.assertIsNotNone(error)


class TestThreadedExecutionSafety(unittest.TestCase):
    def test_independent_contexts_are_isolated_across_threads(self):
        results = {}
        errors = {}

        def worker(idx):
            code = "var base = %d\nvar r = base * 2\nr" % idx
            val, err = execute_bsharp(code)
            results[idx] = val
            errors[idx] = err

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(8):
            self.assertIsNone(errors[i])
            self.assertEqual(results[i].value, i * 2)

    def test_shared_interpreter_object_is_reusable(self):
        interpreter = Interpreter()
        for expected in (10, 20, 30):
            lexer = Lexer("<t>", "var x = %d\nx" % expected)
            tokens, error = lexer.tokenize()
            self.assertIsNone(error)
            ast = Parser(tokens).parser()
            self.assertIsNone(ast.error)
            result = interpreter.visit(ast.node, Context("<main>"))
            self.assertIsNone(result.error)
            self.assertEqual(result.value.value, expected)


if __name__ == "__main__":
    unittest.main()
