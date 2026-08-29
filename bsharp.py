import sys
import os

from B_Sharp.ASTNodes.parser import Parser, Interpreter
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.lexer import Lexer
from B_Sharp.builtins import register_builtins


def run_source(file_name, source_text, context=None):
    """
    Executes B_Sharp source text through Lexer, Parser, and Interpreter.
    """

    if context is None:
        context = Context("<main>")
        register_builtins(context)

    lexer = Lexer(file_name, source_text)
    tokens, error = lexer.tokenize()
    if error:
        return None, error

    parser = Parser(tokens)
    ast = parser.parser()
    if ast.error:
        return None, ast.error

    interpreter = Interpreter()
    result = interpreter.visit(ast.node, context)
    if result.error:
        return None, result.error

    return result.value, None


def run_file(file_path):
    """
    Validates and executes a .bsharp file.
    """
    if not file_path.endswith(".bsharp"):
        print(f"""
            Error: Invalid file extension. 
            B_Sharp runner supports '.bsharp' files.""")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_text = f.read()
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)

    value, error = run_source(file_path, source_text)

    if error:
        print(error)
    elif value is not None and repr(value) != "none":
        print(value)


def run_repl():
    """
    Interactive Command Line REPL for B_Sharp.
    """
    print("B_Sharp Language REPL v1.0")
    print("Type 'exit()' or press Ctrl+C to exit.\n")

    global_context = Context("<main>")
    register_builtins(global_context)

    while True:
        try:
            line = input("bsharp> ")
            if line.strip() in ("exit()", "quit()"):
                break
            if not line.strip():
                continue

            value, error = run_source("<stdin>", line, global_context)

            if error:
                print(error)
            elif value is not None and repr(value) != "none":
                print(value)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting B_Sharp.")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        run_repl()
