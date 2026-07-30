import SASL.lexer as lexer
from SASL.ASTNodes.parser import Interpreter

while True:
    text = input("SASL >>> ")
    ast, error = lexer.run("<SHELL_STD_REPL>", text)

    if error:
        print(error.as_string())
    else:
        interpreter = Interpreter()
        result = interpreter.visit(ast, None)

        if result.error:
            print(result.error.as_string())
        else:
            print(result.value)
