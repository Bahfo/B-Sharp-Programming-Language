import SASL.lexer as lexer

while True:
    text = input("SASL >>> ")
    result, error = lexer.run("<SHELL_STD_REPL>", text)

    if error:
        print(error.as_string())
    else:
        print(result)
