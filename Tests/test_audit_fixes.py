"""Regression tests for the 2026 codebase audit fixes.

Covers: parser depth guard, %-operator in expressions, power overflow,
underscore identifiers, scientific notation, NaN/Inf equality, chained
comparison rejection, strict type names, redefinition typing, in-place
list/array methods, element-wise math, slice normalization, string
.length, unterminated block comments and Python-style printing.
"""

import sys
import os
import io
import unittest
from contextlib import redirect_stdout

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser, Interpreter
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.builtins import register_builtins
from B_Sharp.errors import B_SharpSyntaxError, RunTimeError


def execute_bsharp(source_code, context=None):
    if context is None:
        context = Context("<main>")
        register_builtins(context)
    tokens, error = Lexer("<test_suite>", source_code).tokenize()
    if error:
        return None, error
    ast = Parser(tokens).parser()
    if ast.error:
        return None, ast.error
    result = Interpreter().visit(ast.node, context)
    if result.error:
        return None, result.error
    return result.value, None


def output_of(source_code):
    buf = io.StringIO()
    with redirect_stdout(buf):
        val, err = execute_bsharp(source_code)
    return buf.getvalue(), val, err


class TestParserDepthGuard(unittest.TestCase):
    def test_deep_nesting_reports_syntax_error(self):
        deep = "(" * 5000 + "1" + ")" * 5000
        val, err = execute_bsharp(f"var x = {deep}")
        self.assertIsNotNone(err)
        self.assertIsInstance(err, B_SharpSyntaxError)

    def test_moderate_nesting_still_parses(self):
        val, err = execute_bsharp("var x = " + "(" * 60 + "1" + ")" * 60 + "\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 1)

    def test_deep_unary_chain_reports_cleanly(self):
        val, err = execute_bsharp("var x = " + "-" * 5000 + "1")
        self.assertIsNotNone(err)


class TestModuloInExpressions(unittest.TestCase):
    def test_modulo_inside_arithmetic(self):
        val, err = execute_bsharp("var x = 2 + 3 % 2\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 3)

    def test_integer_division_inside_arithmetic(self):
        val, err = execute_bsharp("var x = 10 - 7 % 2\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 7)

    def test_modulo_with_power(self):
        val, err = execute_bsharp("var x = 2 ^ 3 % 3\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 2)


class TestPowerGuard(unittest.TestCase):
    def test_huge_power_is_clean_error(self):
        val, err = execute_bsharp("var x = 9 ^ 99999")
        self.assertIsNotNone(err)

    def test_reasonable_power_exact(self):
        val, err = execute_bsharp("var x = 2 ^ 100\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 2**100)

    def test_huge_negative_power_falls_back_to_float(self):
        val, err = execute_bsharp("var x = 2 ^ -20000\nx")
        self.assertIsNone(err)
        self.assertIsInstance(val.value, float)

    def test_overflowing_positive_power_is_error(self):
        val, err = execute_bsharp("var x = 2 ^ 20000")
        self.assertIsNotNone(err)


class TestLexerFixes(unittest.TestCase):
    def test_identifier_may_start_with_underscore(self):
        val, err = execute_bsharp("var _private = 7\n_private")
        self.assertIsNone(err)
        self.assertEqual(val.value, 7)

    def test_scientific_notation(self):
        for src, expected in [("1e3", 1000.0), ("2.5E-1", 0.25), ("1E+2", 100.0)]:
            val, err = execute_bsharp(f"var x = {src}\nx")
            self.assertIsNone(err, src)
            self.assertAlmostEqual(val.value, expected)

    def test_unterminated_block_comment_is_error(self):
        tokens, err = Lexer("<t>", "/* never closed").tokenize()
        self.assertIsNotNone(err)
        self.assertIsInstance(err, B_SharpSyntaxError)
        self.assertIn("Unterminated block comment", err.details)

    def test_closed_block_comment_still_works(self):
        val, err = execute_bsharp("/* ok */ 1 + /* inner */ 2")
        self.assertIsNone(err)
        self.assertEqual(val.value, 3)


class TestNaNInfSemantics(unittest.TestCase):
    def test_nan_unequal_to_itself(self):
        val, err = execute_bsharp("nan == nan")
        self.assertIsNone(err)
        self.assertFalse(val.value)

    def test_nan_not_equal_always_true(self):
        val, err = execute_bsharp("nan != nan")
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_inf_equals_inf(self):
        val, err = execute_bsharp("inf == inf")
        self.assertIsNone(err)
        self.assertTrue(val.value)

    def test_inf_vs_number_is_false_not_error(self):
        val, err = execute_bsharp("inf == 5")
        self.assertIsNone(err)
        self.assertFalse(val.value)

    def test_nan_repr(self):
        val, err = execute_bsharp("nan")
        self.assertIsNone(err)
        self.assertEqual(repr(val), "nan")


class TestChainedComparisonRejected(unittest.TestCase):
    def test_chained_less_than_is_syntax_error(self):
        val, err = execute_bsharp("var x = 1 < 2 < 3")
        self.assertIsNotNone(err)

    def test_chained_equality_is_syntax_error(self):
        val, err = execute_bsharp("var x = 1 == 2 == 3")
        self.assertIsNotNone(err)

    def test_single_comparison_still_works(self):
        val, err = execute_bsharp("var x = 1 < 2\nx")
        self.assertIsNone(err)
        self.assertTrue(val.value)


class TestStrictTypeNames(unittest.TestCase):
    def test_lowercase_type_annotation_rejected(self):
        val, err = execute_bsharp("var x : number = 5")
        self.assertIsNotNone(err)

    def test_canonical_type_names_accepted(self):
        val, err = execute_bsharp("var x : Number = 5\nx")
        self.assertIsNone(err)
        self.assertEqual(val.value, 5)

    def test_bool_array_alias_accepted(self):
        val, err = execute_bsharp("var x : Bool[] = [true]\nx")
        self.assertIsNone(err)

    def test_bool_array_alias_same_as_boolean_array(self):
        from B_Sharp.ASTNodes.instances import TYPE_MAP

        self.assertIs(TYPE_MAP["Bool[]"], TYPE_MAP["Boolean[]"])


class TestListMethodSemantics(unittest.TestCase):
    def test_push_appends_in_place(self):
        out, _, err = output_of(
            "var l = [1, 2]\nl.push(3)\nwriteln(l)"
        )
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2, 3]")

    def test_push_at_index_in_place(self):
        out, _, err = output_of(
            "var l = [1, 2, 4]\nl.push(3, 2)\nwriteln(l)"
        )
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2, 3, 4]")

    def test_append_in_place(self):
        out, _, err = output_of("var l = [1]\nl.append(2)\nwriteln(l)")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2]")

    def test_swap_in_place(self):
        out, _, err = output_of("var l = [1, 2, 3]\nl.swap(9, 1)\nwriteln(l)")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 9, 3]")

    def test_delete_negative_index(self):
        out, _, err = output_of("var l = [1, 2, 3]\nl.delete(-1)\nwriteln(l)")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2]")

    def test_drop_returns_removed_slice(self):
        out, _, err = output_of(
            "var l = [1, 2, 3, 4]\nvar r = l.drop(1, 3)\nwriteln(l)\nwriteln(r)"
        )
        self.assertIsNone(err)
        self.assertEqual(out.split(), ["[1,", "4]", "[2,", "3]"])

    def test_methods_return_empty_not_new_list(self):
        out, val, err = output_of("var l = [1]\nvar r = l.push(2)\nr")
        self.assertIsNone(err)
        self.assertEqual(repr(val), "none")

    def test_out_of_bounds_push_index_errors(self):
        _, err = execute_bsharp("var l = [1]\nl.push(2, 5)")
        self.assertIsNotNone(err)

    def test_non_integer_index_errors(self):
        _, err = execute_bsharp("var l = [1]\nl.swap(2, 0.5)")
        self.assertIsNotNone(err)

    def test_unknown_method_errors(self):
        _, err = execute_bsharp("var l = [1]\nl.sort()")
        self.assertIsNotNone(err)

    def test_method_on_non_list_errors(self):
        _, err = execute_bsharp("var x = 5\nx.push(1)")
        self.assertIsNotNone(err)

    def test_array_push_validates_element_type(self):
        _, err = execute_bsharp('var a : Number[] = [1]\na.push("x")')
        self.assertIsNotNone(err)

    def test_array_push_accepts_valid_element(self):
        out, _, err = output_of('var a : Number[] = [1]\na.push(2)\nwriteln(a)')
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2]")


class TestElementWiseMath(unittest.TestCase):
    def test_refusal_keeps_element(self):
        out, _, err = output_of('writeln(["x", 2, true] * [1, 2, 3])')
        self.assertIsNone(err)
        self.assertEqual(out.strip(), '["x", 4, true]')

    def test_scalar_times_vector_left(self):
        out, _, err = output_of("writeln([1, 2, 3] * 2)")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[2, 4, 6]")

    def test_scalar_times_vector_right(self):
        out, _, err = output_of("writeln(2 * [1, 2, 3])")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[2, 4, 6]")

    def test_vector_divided_by_scalar(self):
        out, _, err = output_of("writeln([10, 20] / 2)")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[5.0, 10.0]")

    def test_list_divided_by_list_is_error(self):
        _, err = execute_bsharp("[1, 2] / [3, 4]")
        self.assertIsNotNone(err)

    def test_size_mismatch_is_error(self):
        _, err = execute_bsharp("[1, 2] * [1, 2, 3]")
        self.assertIsNotNone(err)

    def test_division_by_zero_keeps_element(self):
        out, _, err = output_of("writeln([1, 2, 3] / 0)")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2, 3]")


class TestSliceNormalization(unittest.TestCase):
    def test_negative_start_slice(self):
        out, _, err = output_of("writeln([1, 2, 3, 4, 5][-3..])")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[3, 4, 5]")

    def test_negative_end_slice(self):
        out, _, err = output_of("writeln([1, 2, 3, 4, 5][1..-1])")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[2, 3, 4]")

    def test_open_start_slice(self):
        out, _, err = output_of("writeln([1, 2, 3][..2])")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2]")

    def test_out_of_range_bounds_clamp(self):
        out, _, err = output_of("writeln([1, 2, 3][0..99])")
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "[1, 2, 3]")

    def test_typed_array_slice_keeps_type(self):
        from B_Sharp.ASTNodes.instances import Array

        val, err = execute_bsharp("var a : Number[] = [1, 2, 3]\nvar s = a[0..2]\ns")
        self.assertIsNone(err)
        self.assertIsInstance(val, Array)

    def test_string_slice(self):
        out, _, err = output_of('writeln("hello"[1..4])')
        self.assertIsNone(err)
        self.assertEqual(out.strip(), "ell")


class TestStringLengthProperty(unittest.TestCase):
    def test_length_on_string(self):
        val, err = execute_bsharp('"hello".length')
        self.assertIsNone(err)
        self.assertEqual(val.value, 5)

    def test_size_alias_on_string(self):
        val, err = execute_bsharp('"hi".size')
        self.assertIsNone(err)
        self.assertEqual(val.value, 2)

    def test_length_on_list(self):
        val, err = execute_bsharp("[1, 2, 3].length")
        self.assertIsNone(err)
        self.assertEqual(val.value, 3)

    def test_length_on_number_is_error(self):
        _, err = execute_bsharp("x = 5\nx.length")
        self.assertIsNotNone(err)


class TestPythonStylePrinting(unittest.TestCase):
    def test_top_level_strings_unquoted(self):
        out, _, err = output_of('write("a"); writeln("b")')
        self.assertIsNone(err)
        self.assertEqual(out, "ab\n")

    def test_nested_strings_quoted(self):
        out, _, err = output_of('writeln([1, "two"])')
        self.assertIsNone(err)
        self.assertEqual(out.strip(), '[1, "two"]')

    def test_numbers_and_booleans_render_python_like(self):
        out, _, err = output_of("writeln(42)\nwriteln(true)")
        self.assertIsNone(err)
        self.assertEqual(out, "42\ntrue\n")


class TestInfinityOrdering(unittest.TestCase):
    """IEEE-style signed-infinity ordering and equality."""

    def check_true(self, src):
        val, err = execute_bsharp(src)
        self.assertIsNone(err, src)
        self.assertTrue(val.value, src)

    def check_false(self, src):
        val, err = execute_bsharp(src)
        self.assertIsNone(err, src)
        self.assertFalse(val.value, src)

    # --- +inf against finite values (both dispatch directions) ---
    def test_inf_greater_than_finite(self):
        self.check_true("inf > 5")
        self.check_true("inf > 5.5")
        self.check_true("5 < inf")
        self.check_true("0 <= inf")
        self.check_true("inf >= 999999")

    def test_inf_less_than_finite_is_false(self):
        self.check_false("inf < 5")
        self.check_false("5 > inf")
        self.check_false("inf <= 5")

    # --- -inf ---
    def test_negative_infinity_orders(self):
        self.check_true("-inf < 5")
        self.check_true("-inf < inf")
        self.check_true("5 > -inf")
        self.check_false("-inf > 5")
        self.check_false("-inf >= 5")

    # --- infinities among themselves ---
    def test_inf_self_comparison(self):
        self.check_false("inf < inf")
        self.check_true("inf <= inf")
        self.check_false("inf > inf")
        self.check_true("inf >= inf")
        self.check_false("-inf < -inf")
        self.check_true("-inf >= -inf")

    # --- NaN poisons ordering comparisons on either side ---
    def test_nan_poisons_ordering(self):
        self.check_false("nan < 5")
        self.check_false("nan > 5")
        self.check_false("5 < nan")
        self.check_false("5 >= nan")
        self.check_false("inf > nan")
        self.check_false("-inf < nan")
        self.check_false("nan <= -inf")

    # --- booleans coerce numerically as before ---
    def test_boolean_coercion(self):
        self.check_true("true < 2.5")
        self.check_false("false >= true")
        self.check_true("true <= inf")
        self.check_true("-inf < false")

    # --- huge exact integers order correctly against infinities ---
    def test_huge_integers_vs_inf(self):
        self.check_true("2 ^ 1000 < inf")
        self.check_true("-(2 ^ 1000) > -inf")
        self.check_false("2 ^ 1000 > inf")

    # --- sign-aware equality ---
    def test_sign_aware_equality(self):
        self.check_true("inf == inf")
        self.check_true("-inf == -inf")
        self.check_false("inf == -inf")
        self.check_true("inf != -inf")
        self.check_false("-inf != -inf")
        self.check_false("inf == 5")
        self.check_false("-inf == 0")

    def test_repr_and_type(self):
        val, err = execute_bsharp("var x = -inf\nx")
        self.assertIsNone(err)
        self.assertEqual(repr(val), "-inf")
        val, err = execute_bsharp("- -inf")
        self.assertIsNone(err)
        self.assertEqual(repr(val), "inf")


class TestUnaryNegation(unittest.TestCase):
    """Unary '-' semantics: flip inf, distribute over lists, clear errors."""

    def test_negate_numbers(self):
        val, err = execute_bsharp("-42")
        self.assertIsNone(err)
        self.assertEqual(val.value, -42)

    def test_negate_inf_flips_sign(self):
        for src, expected in [("-inf", "-inf"), ("- -inf", "inf"), ("- - -inf", "-inf")]:
            val, err = execute_bsharp(f"var q = {src}\nq")
            self.assertIsNone(err, src)
            self.assertEqual(repr(val), expected)

    def test_negate_list_distributes(self):
        val, err = execute_bsharp("-[1, 2, 3]")
        self.assertIsNone(err)
        self.assertEqual([e.value for e in val.list_of_elements], [-1, -2, -3])

    def test_unnegatable_types_report_clearly(self):
        cases = [
            ("-true", "cannot negate Boolean"),
            ('-"str"', "cannot negate String"),
            ("-none", "cannot negate Empty"),
            ("-nan", "cannot negate NaN"),
        ]
        for src, frag in cases:
            _, err = execute_bsharp(f"var q = 1\nvar z = ({src})")
            self.assertIsNotNone(err, src)
            self.assertIn(frag, err.details, src)
            self.assertNotIn("multiplication", err.details, src)

    def test_negated_inf_still_compares(self):
        val, err = execute_bsharp("var x = -inf\nx < 10000000000")
        self.assertIsNone(err)
        self.assertTrue(val.value)


class TestInterpreterRobustness(unittest.TestCase):
    def test_missing_visit_method_returns_failure(self):
        res = Interpreter().visit(object(), Context("<main>"))
        self.assertIsNotNone(res.error)

    def test_multi_assign_copies_lists(self):
        val, err = execute_bsharp("var a, b = [1]\nb.push(2)\na")
        self.assertIsNone(err)
        self.assertEqual(len(val.list_of_elements), 1)

    def test_no_sys_recursionlimit_side_effect(self):
        import sys as _sys

        before = _sys.getrecursionlimit()
        execute_bsharp("var q = 1")
        self.assertEqual(_sys.getrecursionlimit(), before)


if __name__ == "__main__":
    unittest.main()
