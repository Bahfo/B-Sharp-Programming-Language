from B_Sharp.errors import IllegalCharacaterError
from B_Sharp.ASTNodes.parser import Parser
from B_Sharp.position import Position
from B_Sharp.tokens import *

import string

DIGITS = "0123456789"
LETTERS = string.ascii_letters
LETTERS_DIGITS = LETTERS + DIGITS + "_"


class Token:
    def __init__(self, type, value=None, pos_start=None, pos_end=None):
        self.type = type
        self.value = value

        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy()
            self.pos_end.forward()

        if pos_end:
            self.pos_end = pos_end.copy()

    def __repr__(self):
        if self.value:
            return f"{self.type} : {self.value}"
        return f"{self.type}"


class Lexer:
    def __init__(self, file_name, text):
        self.text = text
        self.file_name = file_name
        self.pos = Position(-1, 0, -1, self.file_name, self.text)
        self.current_char = None
        self.forward()

    def forward(self):
        self.pos.forward(self.current_char)
        if self.pos.index < len(self.text):
            self.current_char = self.text[self.pos.index]
        else:
            self.current_char = None

    def numberize(self):
        number_str = ""
        dot_count = 0
        pos_start = self.pos.copy()

        while self.current_char != None and self.current_char in DIGITS + ".":
            if self.current_char == ".":
                if dot_count == 1:
                    break
                dot_count += 1
                number_str += "."
            else:
                number_str += self.current_char
            self.forward()

        if dot_count == 0:
            return Token(TOKEN_INT, int(number_str), pos_start, self.pos)
        else:
            return Token(TOKEN_FLOAT, float(number_str), pos_start, self.pos)

    def identifiers(self):
        pos_start = self.pos.copy()
        identifier = ""  # An empty string to hold the identifier

        while self.current_char is not None and self.current_char in LETTERS_DIGITS:
            identifier += self.current_char
            self.forward()

        token_type = TOKEN_KEYWORD if identifier in KEYWORDS else TOKEN_IDENTIFIER

        # Returning the new token
        return Token(token_type, identifier, pos_start, self.pos)

    def tokenize(self):
        tokens = []

        while self.current_char != None:
            if self.current_char in " \t":
                self.forward()
            elif self.current_char in LETTERS:
                tokens.append(self.identifiers())
            elif self.current_char == "+":
                tokens.append(Token(TOKEN_PLUS, pos_start=self.pos))
                self.forward()
            elif self.current_char == "-":
                tokens.append(Token(TOKEN_MINUS, pos_start=self.pos))
                self.forward()
            elif self.current_char == "*":
                tokens.append(Token(TOKEN_MUL, pos_start=self.pos))
                self.forward()
            elif self.current_char == "/":
                tokens.append(Token(TOKEN_DIV, pos_start=self.pos))
                self.forward()
            elif self.current_char == "(":
                tokens.append(Token(TOKEN_LPAREN, pos_start=self.pos))
                self.forward()
            elif self.current_char == ")":
                tokens.append(Token(TOKEN_RPAREN, pos_start=self.pos))
                self.forward()
            elif self.current_char == "^":
                tokens.append(Token(TOKEN_POWER, pos_start=self.pos))
                self.forward()
            elif self.current_char == "=":
                tokens.append(Token(TOKEN_EQUAL, pos_start=self.pos))
                self.forward()
            elif self.current_char == ":":
                tokens.append(Token(TOKEN_COLON, pos_start=self.pos))
                self.forward()
            elif self.current_char == ",":
                tokens.append(Token(TOKEN_COMMA, pos_start=self.pos))
                self.forward()
            elif self.current_char in DIGITS:
                tokens.append(self.numberize())
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.forward()
                return [], IllegalCharacaterError(pos_start, self.pos, "'" + char + "'")

        tokens.append(Token(TOKEN_EOF, pos_start=self.pos))
        return tokens, None


def run(file_name, text):
    lexer = Lexer(file_name, text)
    tokens, error = lexer.tokenize()

    if error:
        return None, error

    parser = Parser(tokens)
    ast = parser.parser()

    return ast.node, ast.error
