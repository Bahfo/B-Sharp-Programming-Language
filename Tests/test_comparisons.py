import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser, Interpreter
from B_Sharp.ASTNodes.instances import EnvironmentVariable


class Context:
    def __init__(self, name):
        self.name = name
        self.variables = EnvironmentVariable()


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


context = Context("<global>")

passed = 0
failed = 0
errors = []


def test(code, description, expected=None, expect_error=False):
    global passed, failed
    val, error = run_code(code, context)

    print(f"\n[Code]: {code}")
    print(f"[Description]: {description}")

    if expect_error:
        if error:
            print(f"[ERROR CATCH]: {error.error_name.strip()} - {error.details}")
            passed += 1
        else:
            print(f"[FAIL]: Expected error but got {val}")
            failed += 1
            errors.append((code, description, "Expected error but got success"))
    elif error:
        print(f"[FAIL]: {error.error_name.strip()} - {error.details}")
        failed += 1
        errors.append((code, description, f"{error.error_name}: {error.details}"))
    else:
        result_str = str(val)
        if expected is not None and result_str != expected:
            print(f"[FAIL]: Expected {expected}, got {result_str}")
            failed += 1
            errors.append((code, description, f"Expected {expected}, got {result_str}"))
        else:
            print(f"[SUCCESS]: Result = {val}")
            passed += 1


print("=" * 60)
print("RUNNING B_Sharp COMPARISON & LOGICAL OPERATION TESTS")
print("=" * 60)

# ──────────────────────────────────────────────────────────────
# 1. Equality (==)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("1. EQUALITY (==)")
print("=" * 60)

test("5 == 5", "Integer equality: same values")
test("5 == 6", "Integer equality: different values")
test("3.14 == 3.14", "Float equality: same values")
test("3.14 == 3.15", "Float equality: different values")
test("0 == 0", "Zero equality")
test("-5 == -5", "Negative number equality")
test("-5 == 5", "Negative vs positive equality")
test("1 == 1.0", "Int vs float equality (1 == 1.0)")

# ──────────────────────────────────────────────────────────────
# 2. Inequality (!=)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. INEQUALITY (!=)")
print("=" * 60)

test("5 != 6", "Integer inequality: different values")
test("5 != 5", "Integer inequality: same values")
test("3.14 != 3.15", "Float inequality: different values")
test("0 != 1", "Zero inequality")
test("-5 != 5", "Negative vs positive inequality")

# ──────────────────────────────────────────────────────────────
# 3. Less Than (<)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. LESS THAN (<)")
print("=" * 60)

test("5 < 10", "Less than: true case")
test("10 < 5", "Less than: false case")
test("5 < 5", "Less than: equal values (false)")
test("-5 < 0", "Less than: negative vs zero")
test("-10 < -5", "Less than: both negative")
test("3.14 < 3.15", "Float less than")
test("3.15 < 3.14", "Float greater than (false)")

# ──────────────────────────────────────────────────────────────
# 4. Greater Than (>)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. GREATER THAN (>)")
print("=" * 60)

test("10 > 5", "Greater than: true case")
test("5 > 10", "Greater than: false case")
test("5 > 5", "Greater than: equal values (false)")
test("0 > -5", "Greater than: zero vs negative")
test("-5 > -10", "Greater than: both negative")
test("3.15 > 3.14", "Float greater than")

# ──────────────────────────────────────────────────────────────
# 5. Less Than or Equal (<=)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("5. LESS THAN OR EQUAL (<=)")
print("=" * 60)

test("5 <= 10", "Less than or equal: less (true)")
test("5 <= 5", "Less than or equal: equal (true)")
test("10 <= 5", "Less than or equal: greater (false)")

# ──────────────────────────────────────────────────────────────
# 6. Greater Than or Equal (>=)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("6. GREATER THAN OR EQUAL (>=)")
print("=" * 60)

test("10 >= 5", "Greater than or equal: greater (true)")
test("5 >= 5", "Greater than or equal: equal (true)")
test("5 >= 10", "Greater than or equal: less (false)")

# ──────────────────────────────────────────────────────────────
# 7. Boolean Literals
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("7. BOOLEAN LITERALS")
print("=" * 60)

test("true", "Boolean literal: true")
test("false", "Boolean literal: false")
test("true == true", "Boolean equality: true == true")
test("false == false", "Boolean equality: false == false")
test("true == false", "Boolean equality: true == false")
test("true != false", "Boolean inequality: true != false")
test("true != true", "Boolean inequality: true != true")

# ──────────────────────────────────────────────────────────────
# 8. Cross-Type: Number vs Boolean
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("8. CROSS-TYPE: Number vs Boolean")
print("=" * 60)

test("1 == true", "Number 1 == true (true: 1 == 1)")
test("5 == true", "Number 5 == true (false: 5 != 1)")
test("0 == false", "Number 0 == false (true: 0 == 0)")
test("0 != true", "Number 0 != true (true: 0 != 1)")
test("1 != false", "Number 1 != false (true: 1 != 0)")
test("2 > true", "Number 2 > true (true: 2 > 1)")
test("2 > false", "Number 2 > false (true: 2 > 0)")
test("0 < true", "Number 0 < true (true: 0 < 1)")
test("true == 1", "Boolean true == 1 (true: 1 == 1)")
test("false == 0", "Boolean false == 0 (true: 0 == 0)")
test("false < 1", "Boolean false < 1 (true: 0 < 1)")
test("true <= 1", "Boolean true <= 1 (true: 1 <= 1)")
test("true >= 1", "Boolean true >= 1 (true: 1 >= 1)")
test("false >= 0", "Boolean false >= 0 (true: 0 >= 0)")

# ──────────────────────────────────────────────────────────────
# 9. Logical AND
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("9. LOGICAL AND")
print("=" * 60)

test("true and true", "AND: true and true")
test("true and false", "AND: true and false")
test("false and true", "AND: false and true")
test("false and false", "AND: false and false")

# ──────────────────────────────────────────────────────────────
# 10. Logical OR
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("10. LOGICAL OR")
print("=" * 60)

test("true or true", "OR: true or true")
test("true or false", "OR: true or false")
test("false or true", "OR: false or true")
test("false or false", "OR: false or false")

# ──────────────────────────────────────────────────────────────
# 11. Unary NOT
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("11. UNARY NOT")
print("=" * 60)

test("not true", "not true")
test("not false", "not false")
test("not not true", "double not: not not true")
test("not not false", "double not: not not false")

# ──────────────────────────────────────────────────────────────
# 12. Combined Logical Expressions
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("12. COMBINED LOGICAL EXPRESSIONS")
print("=" * 60)

test("(5 > 3) and (2 < 4)", "AND of two comparisons: both true")
test("(5 > 3) and (2 > 4)", "AND of two comparisons: one false")
test("(5 < 3) and (2 < 4)", "AND of two comparisons: one false")
test("(5 > 3) or (2 > 4)", "OR of two comparisons: one true")
test("(5 < 3) or (2 > 4)", "OR of two comparisons: both false")
test("(5 < 3) or (2 < 4)", "OR of two comparisons: one true")
test("not (5 > 3)", "NOT of comparison: true")
test("not (3 > 5)", "NOT of comparison: false")
test("not (5 > 3) and (2 < 4)", "NOT + AND: not(true and true)")
test("not (5 > 3) or (2 < 4)", "NOT + OR: not(true) or true")

# ──────────────────────────────────────────────────────────────
# 13. Operator Precedence
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("13. OPERATOR PRECEDENCE")
print("=" * 60)

test("2 + 3 > 4", "Addition before comparison: (2+3) > 4")
test("2 + 3 == 5", "Addition before equality: (2+3) == 5")
test("2 * 3 == 6", "Multiplication before equality: (2*3) == 6")
test("2 * 3 != 5", "Multiplication before inequality: (2*3) != 5")
test("10 / 2 == 5", "Division before equality: (10/2) == 5")
test("2 + 3 * 2 > 7", "Multiplication before addition before comparison")
test("2 ^ 3 == 8", "Power before equality: (2^3) == 8")
test("true and 2 + 3 == 5", "Arithmetic before logical: true and (2+3)==5")
test("(2 + 3) > 4 and (5 - 1) == 4", "Parenthesized precedence")

# ──────────────────────────────────────────────────────────────
# 14. Parenthesized Expressions
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("14. PARENTHESIZED EXPRESSIONS")
print("=" * 60)

test("(5 > 3)", "Simple parenthesized comparison")
test("((5 > 3))", "Double parenthesized comparison")
test("(2 + 3) == 5", "Parenthesized arithmetic in comparison")
test("(true and false) or true", "Parenthesized logical")

# ──────────────────────────────────────────────────────────────
# 15. Comparisons with Variables
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("15. COMPARISONS WITH VARIABLES")
print("=" * 60)

test("var x = 10", "Declare variable x = 10")
test("x > 5", "Variable comparison: x > 5")
test("x == 10", "Variable comparison: x == 10")
test("x != 5", "Variable comparison: x != 5")
test("x <= 10", "Variable comparison: x <= 10")
test("x >= 10", "Variable comparison: x >= 10")
test("var y = true", "Declare boolean variable y = true")
test("y and true", "Boolean variable in logical: y and true")
test("y == true", "Boolean variable comparison: y == true")
test("x > 5 and y == true", "Mixed variable comparison")

# ──────────────────────────────────────────────────────────────
# 16. Strong Typing Enforcement
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("16. STRONG TYPING ENFORCEMENT")
print("=" * 60)

test("var a : Boolean = true", "Correct: Boolean = true")
test("var b : Boolean = false", "Correct: Boolean = false")
test("var c : Boolean = 5 > 3", "Correct: Boolean = comparison result")
test("var d : Boolean = 1 == 1", "Correct: Boolean = equality result")
test("var e : Boolean = 5", "ERROR: Boolean = Number", expect_error=True)
test("var f : Number = true", "ERROR: Number = Boolean", expect_error=True)
test("var g : Number = 5 > 3", "ERROR: Number = comparison (returns Boolean)", expect_error=True)
test("var h : Number = true and false", "ERROR: Number = logical (returns Boolean)", expect_error=True)

# ──────────────────────────────────────────────────────────────
# 17. Chained Comparisons (via variables)
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("17. COMPARISONS IN VARIABLE ASSIGNMENTS")
print("=" * 60)

test("var p = 10 > 5", "Weak var = comparison (holds Boolean)")
test("var q = 10 == 10", "Weak var = equality (holds Boolean)")
test("var r = true and false", "Weak var = logical (holds Boolean)")
test("var s = not true", "Weak var = unary not (holds Boolean)")

# ──────────────────────────────────────────────────────────────
# 18. Edge Cases: Boundary Values
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("18. EDGE CASES: BOUNDARY VALUES")
print("=" * 60)

test("0 == 0", "Zero equality")
test("0 != 1", "Zero inequality")
test("0 > -1", "Zero greater than negative")
test("0 < 1", "Zero less than positive")
test("0 >= 0", "Zero greater than or equal")
test("0 <= 0", "Zero less than or equal")
test("-1 == -1", "Negative equality")
test("-1 < 0", "Negative less than zero")
test("-1 > -2", "Negative greater than negative")
test("999999 == 999999", "Large number equality")
test("1.0000001 > 1", "Float precision comparison")

# ──────────────────────────────────────────────────────────────
# 19. Edge Cases: Invalid Operations
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("19. EDGE CASES: INVALID OPERATIONS")
print("=" * 60)

test("5 + true", "ERROR: arithmetic with Boolean", expect_error=True)
test("true + 5", "ERROR: arithmetic with Boolean (reversed)", expect_error=True)
test("true and 5", "ERROR: logical AND with Number", expect_error=True)
test("5 and true", "ERROR: logical AND with Number (reversed)", expect_error=True)
test("true or 5", "ERROR: logical OR with Number", expect_error=True)

# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Total:  {passed + failed}")

if errors:
    print("\n" + "=" * 60)
    print("FAILURES:")
    print("=" * 60)
    for code, desc, reason in errors:
        print(f"\n  [{code}]")
        print(f"  {desc}")
        print(f"  -> {reason}")

print("\n" + "=" * 60)
print("FINAL ENVIRONMENT STATE:")
print("=" * 60)
for var_name, data in context.variables.variables.items():
    type_name = data["type"].__name__ if data["type"] else "Any"
    const_flag = "const" if data["is_const"] else "var"
    print(f" - {const_flag} {var_name} : {type_name} = {data['value']}")
