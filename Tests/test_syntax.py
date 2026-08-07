import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser, Interpreter
from B_Sharp.ASTNodes.instances import Context


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


class TestBSharpLanguage(unittest.TestCase):

    # ==========================================
    # 1. VARIABLES, CONSTANTS & ARITHMETIC
    # ==========================================
    def test_variable_declaration_and_reassignment(self):
        code = """
        var x = 10
        x = 25
        var y = x + 5
        y
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 30)

    def test_operator_precedence(self):
        code = "var res = 5 + 3 * 2 ^ 2 - 10 / 2; res"
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 12.0)  # 5 + (3 * 4) - 5 = 12

    def test_const_reassignment_fails(self):
        code = """
        const MAX = 100
        MAX = 200
        """
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)
        self.assertIn("Cannot change value", err.as_string())

    # ==========================================
    # 2. SEMICOLON SEPARATORS & SINGLE-LINE STATEMENTS
    # ==========================================
    def test_single_line_semicolons(self):
        code = "var a = 1; var b = 2; var c = 3; a + b + c"
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 6)

    def test_mixed_semicolons_and_newlines(self):
        code = """
        var x = 10; var y = 20
        var z = x + y;
        z
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 30)

    # ==========================================
    # 3. STRINGS & ESCAPE SEQUENCES
    # ==========================================
    def test_string_concatenation_and_repetition(self):
        code = """
        var prefix = "B#"
        var version = " 1.0"
        var divider = "-" * 3
        var header = prefix + version + " " + divider
        header
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, "B# 1.0 ---")

    def test_string_escape_sequences(self):
        code = r'var escaped = "Line1\nLine2\tTabbed\"Quote\""; escaped'
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 'Line1\nLine2\tTabbed"Quote"')

    def test_string_equality(self):
        code = """
        var str1 = "hello"
        var str2 = "hello"
        var str3 = "world"
        (str1 == str2) and (str1 != str3)
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertTrue(val.value)

    # ==========================================
    # 4. INCREMENT (++) AND DECREMENT (--)
    # ==========================================
    def test_prefix_vs_postfix_increment(self):
        code = """
        var a = 5
        var post = a++
        var b = 5
        var pre = ++b
        var sum = post + pre + a + b
        sum
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 23)  # 5 + 6 + 6 + 6 = 23

    def test_postfix_and_prefix_decrement(self):
        code = """
        var x = 10
        var post_dec = x--
        var pre_dec = --x
        post_dec - pre_dec + x
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 10)  # 10 - 8 + 8 = 10

    # ==========================================
    # 5. IF STATEMENTS (BLOCK, INLINE, EXPRESSIONS)
    # ==========================================
    def test_if_elif_else_block(self):
        code = """
        var score = 85
        var grade = ""
        
        if (score >= 90) {
            grade = "A"
        } elif score >= 80 {
            grade = "B"
        } else {
            grade = "C"
        }
        grade
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, "B")

    def test_inline_if_then_else(self):
        code = """
        var status = 200
        var msg = "none"
        if status == 200 then msg = "OK" else msg = "ERROR"
        msg
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, "OK")

    def test_if_expression_assignment(self):
        code = """
        var age = 18
        var status = if (age >= 18) then "Adult" else "Minor"
        status
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, "Adult")

    # ==========================================
    # 6. WHILE LOOPS
    # ==========================================
    def test_while_loop_block(self):
        code = """
        var sum = 0
        var i = 1
        while (i <= 5) {
            sum = sum + i
            i++
        }
        sum
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 15)

    def test_while_loop_inline_then(self):
        code = """
        var count = 0
        while count < 4 then ++count
        count
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 4)

    # ==========================================
    # 7. FOR LOOPS (STRICT C-STYLE)
    # ==========================================
    def test_for_loop_block(self):
        code = """
        var total = 0
        for (var i = 0; i < 5; i++) {
            total = total + i
        }
        total
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 10)  # 0 + 1 + 2 + 3 + 4

    def test_for_loop_inline_then(self):
        code = """
        var acc = 0
        for (var j = 1; j <= 3; ++j) then acc = acc + 10
        acc
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, 30)

    def test_for_loop_decrement(self):
        code = """
        var countdown = ""
        for (var k = 3; k > 0; k--) {
            countdown = countdown + k
        }
        countdown
        """
        val, err = execute_bsharp(code)
        self.assertIsNone(err)
        self.assertEqual(val.value, "321")

    # ==========================================
    # 8. ERROR & EDGE CASES
    # ==========================================
    def test_invalid_string_multiplication(self):
        code = '"hello" * "world"'
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)

    def test_unterminated_string_syntax_error(self):
        code = 'var x = "Unterminated string'
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)

    def test_missing_semicolon_in_for_loop_fails(self):
        code = "for (var i = 0 i < 5; i++) { }"
        val, err = execute_bsharp(code)
        self.assertIsNotNone(err)


if __name__ == "__main__":
    unittest.main()
