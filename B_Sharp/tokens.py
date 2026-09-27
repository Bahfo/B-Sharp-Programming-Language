# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# (Simple Abstracted Syntax Language)
# The code is guarded and licensed under the GPLv3 License.
# --------------------------------------------------------------
# Module: tokens.py: All B_Sharp defined tokens.

# Code Tokens
TOKEN_INT = "INT"
TOKEN_FLOAT = "FLOAT"
TOKEN_PLUS = "PLUS"
TOKEN_MINUS = "MINUS"
TOKEN_MUL = "MUL"
TOKEN_DIV = "DIV"
TOKEN_IDIV = "IDIV"
TOKEN_LPAREN = "LPAREN"
TOKEN_RPAREN = "RPAREN"
TOKEN_EOF = "EOF"
TOKEN_POWER = "POWER"
TOKEN_INC = "INC"
TOKEN_DEC = "DEC"
TOKEN_ARROW = "ARROW"
TOKEN_MODULO = "MODULO"
# Keywords
TOKEN_KEYWORD = "KEYWORD"
# Variables
TOKEN_IDENTIFIER = "IDENTIFIER"
# Identifiers
TOKEN_EQUAL = "EQ"
TOKEN_COLON = "COLON"
TOKEN_COMMA = "COMMA"
# Comparisons
TOKEN_EE = "EQUAL_EQUAL"
TOKEN_LT = "LESS_THAN"
TOKEN_GT = "GREATER_THAN"
TOKEN_LTE = "LESS_THAN_EQUAL"
TOKEN_GTE = "GREATER_THAN_EQUAL"
TOKEN_NOT_E = "NOT_EQUAL"
# Delimiters
TOKEN_NEWLINE = "NEWLINE"
TOKEN_SEMICOLON = "SEMICOLON"
TOKEN_LCURLY = "LCURLY"
TOKEN_RCURLY = "RCURLY"
# Strings
TOKEN_STRING = "STRING"
# Lists
TOKEN_LBRACKET = "LBRACKET"
TOKEN_RBRACKET = "RBRACKET"
# Comments
TOKEN_COMMENT = "TOKEN_COMMENT"
TOKEN_COMMENT_MULTILINE = "START_COMMENT_MULTILINE"
# Dot Notations
TOKEN_DOT = "TOKEN_DOT"
TOKEN_DOTDOT = "TOKEN_DOTDOT"
# Bang Token
TOKEN_BANG = "BANG"
# Macros
TOKEN_MACRO = "MACRO"
# Ellipsis
TOKEN_ELLIPSIS = "ELLIPSIS"

# All Keywords
KEYWORDS = [
    "do",
    "or",
    "if",
    "fn",
    "try",
    "var",
    "for",
    "and",
    "not",
    "inf",
    "nan",
    "Inf",
    "NaN",
    "Bool",
    "List",
    "else",
    "elif",
    "then",
    "none",
    "pass",
    "true",
    "false",
    "catch",
    "using",
    "break",
    "const",
    "while",
    "Empty",
    "Number",
    "String",
    "return",
    "struct",
    "pragma",
    "continue",
    "function",
]

# All Caller Macros Types
possible_macros = [
    "pragma",
    "error",
    "panic",
    "allow",
    "remember",
]

# Colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
BOLD_RED = "\033[1;31m"
YELLOW = "\033[33m"
BOLD_YELLOW = "\033[1;33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
