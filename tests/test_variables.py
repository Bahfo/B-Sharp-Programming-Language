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

test_cases = [
    # --- 1. Strong vs Weak Typing ---
    ("var x : Number = 10", "Strong declaration: Number"),
    ("var y = 12", "Weak declaration: Any type allowed"),
    # --- 2. Constants & Reassignment ---
    ("const pi : Number = 3.14", "Constant declaration"),
    ("const y_const = 12", "Weak constant declaration"),
    # --- 3. Empty & Defaults ---
    ("const z : Empty", "Const declared as Empty (defaults to none)"),
    ("var standalone : Number", "Uninitialized strong variable (defaults to none)"),
    ("var y_null : Number = none", "Strong Number assigned explicit none"),
    # --- 4. Multi-assignment & Chaining ---
    ("var a, b, c : Number = 15", "Multi-variable strong assignment"),
    ("var p : Number = var q : Number = 15", "Chained variable assignment"),
    ("var m, n = 12", "Multi-variable weak assignment"),
    # --- 5. Error Triggers ---
    ("const w", "ERROR expected: Uninitialized const without type"),
    ("var err1 : Empty = 12", "ERROR expected: Assigning number to Empty"),
    ("pi = 5", "ERROR expected: Modifying constant 'pi'"),
    (
        "var err2, err3 = 14, none",
        "ERROR expected: Syntax error on tuple initialization",
    ),
]

print("=" * 60)
print("RUNNING B_Sharp VARIABLE SPECIFICATION TESTS")
print("=" * 60)

for code, description in test_cases:
    val, error = run_code(code, context)
    print(f"\n[Code]: {code}")
    print(f"[Description]: {description}")

    if error:
        print(f"[ERROR CATCH]: {error.error_name.strip()} - {error.details}")
    else:
        print(f"[SUCCESS]: Result = {val}")

print("\n" + "=" * 60)
print("FINAL ENVIRONMENT STATE:")
print("=" * 60)
for var_name, data in context.variables.variables.items():
    type_name = data["type"].__name__ if data["type"] else "Any"
    const_flag = "const" if data["is_const"] else "var"
    print(f" - {const_flag} {var_name} : {type_name} = {data['value']}")
