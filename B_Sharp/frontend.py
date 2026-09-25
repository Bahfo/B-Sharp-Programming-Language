"""
Unified Frontend Pipeline for B-Sharp.

Parses raw source code into an Abstract Syntax Tree consumed by both
the Interpreter and he Native LLVM/C Compiler Engine.
"""

from B_Sharp.lexer import Lexer
from B_Sharp.ASTNodes.parser import Parser
from B_Sharp.CodeExecution.caller_macros import preprocess_pragmas


class FrontendResult:
    def __init__(self, ast_root=None, file_config=None, error=None):
        self.ast_root = ast_root
        self.file_config = file_config
        self.error = error

    @property
    def has_error(self):
        return self.error is not None


def parse_source(file_name: str, source_code: str) -> FrontendResult:
    """
    Executes lexical analysis, macros preprocessing and parsing.
    """

    lexer = Lexer(file_name, source_code)
    tokens, error = lexer.tokenize()
    if error:
        return FrontendResult(error=error)

    tokens, file_cfg, macro_error = preprocess_pragmas(tokens, file_name)
    if macro_error:
        return FrontendResult(error=macro_error)

    parser = Parser(tokens, file_config=file_cfg)
    ast = parser.parser()
    if ast.error:
        return FrontendResult(error=ast.error)

    return FrontendResult(ast_root=ast.node, file_config=file_cfg)
