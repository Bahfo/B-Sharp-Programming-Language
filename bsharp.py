import time
import sys
import os

from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.builtins import register_builtins
from B_Sharp.ASTNodes.interpreter import Interpreter
from B_Sharp.CodeExecution.caller_macros import (
    preprocess_pragmas,
    get_config,
    render_value,
)


def run_source(file_name, source_text, context=None, measure_time=False):
    """
    Executes B_Sharp source text through Lexer, Parser, and Interpreter.
    Always returns a 3-tuple: (value, error, elapsed_time)
    """
    start_time = time.perf_counter()

    if context is None:
        context = Context("<main>")
        register_builtins(context)

    lexer = Lexer(file_name, source_text)
    tokens, error = lexer.tokenize()
    if error:
        return None, error, None

    tokens, file_cfg, macro_error = preprocess_pragmas(tokens, file_name)
    if macro_error:
        return None, macro_error, None

    parser = Parser(tokens, file_config=file_cfg)
    ast = parser.parser()
    if ast.error:
        return None, ast.error, None

    interpreter = Interpreter()
    result = interpreter.visit(ast.node, context)
    if result.error:
        return None, result.error, None

    elapsed_time = (time.perf_counter() - start_time) if measure_time else None
    return result.value, None, elapsed_time


def run_file(file_path, measure_time=False):
    """
    Validates and executes a .bsharp file.
    """
    if not file_path.endswith(".bsharp"):
        print("Error: Invalid file extension. B_Sharp runner supports '.bsharp' files.")
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

    value, error, elapsed_time = run_source(
        file_path, source_text, measure_time=measure_time
    )

    if error:
        print(error)
    elif value is not None and repr(value) != "none":
        print(render_value(value, get_config(file_path)))

    if elapsed_time is not None:
        print(f"Measured runtime: {elapsed_time:.6f}s")


def run_repl():
    """
    Interactive Command Line REPL for B_Sharp.
    """
    print("B_Sharp Language REPL v1.0")
    print("Type 'exit()','quit()' or press Ctrl+C to exit.\n")

    global_context = Context("<main>")
    register_builtins(global_context)

    while True:
        try:
            line = input("bsharp> ")
            if line.strip() in ("exit()", "quit()"):
                break
            if not line.strip():
                continue

            value, error, _ = run_source("<stdin>", line, global_context)

            if error:
                print(error)
            elif value is not None and repr(value) != "none":
                print(render_value(value, get_config("<stdin>")))

        except (KeyboardInterrupt, EOFError):
            print("\nExiting B_Sharp.")
            break


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        run_repl()
    else:
        measure_time = False
        if "--measure" in args:
            measure_time = True
            args.remove("--measure")
        elif "-m" in args:
            measure_time = True
            args.remove("-m")

        if args:
            run_file(args[0], measure_time=measure_time)
        else:
            print("Error: No file specified.")
            sys.exit(1)
