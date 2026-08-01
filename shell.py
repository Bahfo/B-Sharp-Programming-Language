import B_Sharp.lexer as lexer
from B_Sharp.ASTNodes.parser import Interpreter
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.ASTNodes.nodes import (
    VariableAssignNode,
    MultiVariableAssignNode,
    VariableReassignNode,
)

global_context = Context("<program>")

while True:
    text = input("B_Sharp >>> ")
    ast, error = lexer.run("<SHELL_STD_REPL>", text)

    if error:
        print(error.as_string())
    else:
        interpreter = Interpreter()
        result = interpreter.visit(ast, global_context)

        if result.error:
            print(result.error.as_string())
        elif not isinstance(
            ast, (VariableAssignNode, MultiVariableAssignNode, VariableReassignNode)
        ):
            print(result.value)
