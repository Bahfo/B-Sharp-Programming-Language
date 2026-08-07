from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.ASTNodes.parser import Interpreter, Parser

code = """
var greeting : String = "Hello, "
var user = "World"
var full_greeting = greeting + user

var line = "=" * 5
var match_test = (full_greeting == "Hello, World")

full_greeting
"""

lexer = Lexer("test_string.bsharp", code)
tokens, error = lexer.tokenize()
if not error:
    parser = Parser(tokens)
    ast = parser.parser()
    if not ast.error:
        context = Context("<main>")
        interpreter = Interpreter()
        res = interpreter.visit(ast.node, context)
        print("Result:", res.value)
        print("Line Variable:", context.variables.get("line")[0])
        print("Match Test:", context.variables.get("match_test")[0])
