from B_Sharp.position import Position
from B_Sharp.Errors.errors import *
from B_Sharp.tokens import *

import string

DIGITS = "0123456789"
LETTERS = string.ascii_letters + "_"
LETTERS_DIGITS = LETTERS + DIGITS


class Token:
    def __init__(self, type, value=None, pos_start=None, pos_end=None):
        self.type = type
        self.value = value
        self.pos_start = None
        self.pos_end = None

        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy()
            self.pos_end.forward()

        if pos_end:
            self.pos_end = pos_end.copy()

    def matches(self, type_, value=None):
        return self.type == type_ and (value is None or self.value == value)

    def __repr__(self):
        if self.value is not None:
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

    def peek(self, offset=1):
        peek_index = self.pos.index + offset
        if peek_index < len(self.text):
            return self.text[peek_index]
        return None

    def numberize(self):
        number_str = ""
        dot_count = 0
        pos_start = self.pos.copy()

        while self.current_char != None and self.current_char in DIGITS + ".":
            if self.current_char == ".":
                if dot_count == 1:
                    return None, DoubleFloatingAssignedError(
                        pos_start,
                        self.pos,
                        "A number literal cannot contain more than one decimal point.",
                    )

                if self.peek() is None or self.peek() not in DIGITS:
                    break
                dot_count += 1
                number_str += "."
            else:
                number_str += self.current_char
            self.forward()

        # Scientific notation: 1e5, 2.5E-3, 7e+10
        if (
            self.current_char is not None
            and self.current_char in ("e", "E")
            and number_str
            and number_str != "."
        ):
            exponent_part = ""
            offset = 1
            if self.peek(offset) in ("+", "-"):
                exponent_part += self.peek(offset)
                offset += 1
            if self.peek(offset) is not None and self.peek(offset) in DIGITS:
                while self.peek(offset) is not None and self.peek(offset) in DIGITS:
                    exponent_part += self.peek(offset)
                    offset += 1

                for _ in range(offset):
                    self.forward()
                number_str += "e" + exponent_part
                dot_count = max(dot_count, 1)

        if dot_count == 0:
            return Token(TOKEN_INT, int(number_str), pos_start, self.pos), None
        else:
            return Token(TOKEN_FLOAT, float(number_str), pos_start, self.pos), None

    def identifiers(self):
        pos_start = self.pos.copy()
        identifier = ""  # An empty string to hold the identifier

        while self.current_char is not None and self.current_char in LETTERS_DIGITS:
            identifier += self.current_char
            self.forward()

        token_type = TOKEN_KEYWORD if identifier in KEYWORDS else TOKEN_IDENTIFIER

        # Returning the new token
        return Token(token_type, identifier, pos_start, self.pos)

    def make_token_not_equal(self):
        pos_start = self.pos.copy()
        self.forward()

        if self.current_char == "=":
            self.forward()
            return Token(TOKEN_NOT_E, pos_start=pos_start, pos_end=self.pos), None

        return None, B_SharpSyntaxError(
            pos_start,
            self.pos,
            "Expected an equalizer after NOT logical operation",
        )

    def make_token_equal(self):
        pos_start = self.pos.copy()
        token_type = TOKEN_EQUAL
        self.forward()

        if self.current_char == "=":
            self.forward()
            token_type = TOKEN_EE

        return Token(token_type, pos_start=pos_start, pos_end=self.pos)

    def make_token_greater_than(self):
        pos_start = self.pos.copy()
        token_type = TOKEN_GT
        self.forward()

        if self.current_char == "=":
            self.forward()
            token_type = TOKEN_GTE

        return Token(token_type, pos_start=pos_start, pos_end=self.pos)

    def make_token_less_than(self):
        pos_start = self.pos.copy()
        token_type = TOKEN_LT
        self.forward()

        if self.current_char == "=":
            self.forward()
            token_type = TOKEN_LTE

        return Token(token_type, pos_start=pos_start, pos_end=self.pos)

    def stringnize(self, quote_char):
        # IDK why I called it like this
        string_val = ""
        pos_start = self.pos.copy()
        escape_character = False
        self.forward()

        escape_characters = {
            "n": "\n",
            "t": "\t",
            "r": "\r",
            "\\": "\\",
            '"': '"',
            "'": "'",
        }

        while self.current_char is not None and (
            self.current_char != quote_char or escape_character
        ):
            if escape_character:
                char = self.current_char
                if char in escape_characters:
                    string_val += escape_characters[char]
                else:
                    return None, B_SharpSyntaxError(
                        pos_start,
                        self.pos,
                        f"Invalid escape sequence '\\{char}'.",
                    )
                escape_character = False
            else:
                if self.current_char == "\\":
                    escape_character = True
                else:
                    string_val += self.current_char
            self.forward()

        if self.current_char != quote_char:
            return None, B_SharpSyntaxError(
                pos_start,
                self.pos,
                f"Unterminated string literal, expected closing {quote_char}.",
            )

        self.forward()
        return Token(TOKEN_STRING, string_val, pos_start, self.pos), None

    def commentize(self, comment_type: str):
        if comment_type == "single":
            while self.current_char is not None and self.current_char != "\n":
                self.forward()
            return None
        elif comment_type == "multi":
            while self.current_char is not None:
                if self.current_char == "*" and self.peek() == "/":
                    self.forward()  # skip '*'
                    self.forward()  # skip '/'
                    return None
                self.forward()

            return B_SharpSyntaxError(
                pos_start=self.pos.copy(),
                pos_end=self.pos.copy(),
                details="Unterminated block comment. Expected closing '*/'.",
            )

        return None

    def tokenize(self):
        tokens = []

        while self.current_char != None:
            if self.current_char in " \t\x0b\x0c":
                self.forward()
            elif self.current_char in ("\n", ";"):
                token_type = (
                    TOKEN_NEWLINE if self.current_char == "\n" else TOKEN_SEMICOLON
                )
                tokens.append(Token(token_type, pos_start=self.pos))
                self.forward()
            elif self.current_char == "/" and self.peek() == "/":
                self.forward()  # skip first '/'
                self.forward()  # skip second '/'
                self.commentize("single")
            elif self.current_char == "/" and self.peek() == "*":
                self.forward()  # skip first '/'
                self.forward()  # skip '*'
                comment_error = self.commentize("multi")
                if comment_error:
                    return [], comment_error
            elif self.current_char == "\r":
                self.forward()  # Skip carriage return
            elif self.current_char == "{":
                tokens.append(Token(TOKEN_LCURLY, pos_start=self.pos))
                self.forward()
            elif self.current_char == "}":
                tokens.append(Token(TOKEN_RCURLY, pos_start=self.pos))
                self.forward()
            elif self.current_char == ".":
                if self.peek() == ".":
                    tokens.append(Token(TOKEN_DOTDOT, pos_start=self.pos))
                    self.forward()
                    self.forward()
                else:
                    tokens.append(Token(TOKEN_DOT, pos_start=self.pos))
                    self.forward()
            elif self.current_char in LETTERS:
                tokens.append(self.identifiers())
            elif self.current_char in DIGITS:
                token, error = self.numberize()
                if error:
                    return [], error
                tokens.append(token)
            elif self.current_char == "+":
                pos_start = self.pos.copy()
                self.forward()
                if self.current_char == "+":
                    self.forward()
                    tokens.append(
                        Token(TOKEN_INC, pos_start=pos_start, pos_end=self.pos)
                    )
                else:
                    tokens.append(
                        Token(TOKEN_PLUS, pos_start=pos_start, pos_end=self.pos)
                    )
            elif self.current_char == "-":
                pos_start = self.pos.copy()
                self.forward()
                if self.current_char == "-":
                    self.forward()
                    tokens.append(
                        Token(TOKEN_DEC, pos_start=pos_start, pos_end=self.pos)
                    )
                elif self.current_char == ">":
                    self.forward()
                    tokens.append(
                        Token(TOKEN_ARROW, pos_start=pos_start, pos_end=self.pos)
                    )
                else:
                    tokens.append(
                        Token(TOKEN_MINUS, pos_start=pos_start, pos_end=self.pos)
                    )
            elif self.current_char == "%":
                pos_start = self.pos.copy()
                self.forward()
                tokens.append(Token(TOKEN_IDIV, pos_start=pos_start, pos_end=self.pos))
            elif self.current_char == "~":
                pos_start = self.pos.copy()
                self.forward()
                tokens.append(
                    Token(TOKEN_MODULO, pos_start=pos_start, pos_end=self.pos)
                )
            elif self.current_char == "*":
                pos_start = self.pos.copy()
                self.forward()
                if self.current_char == "*":
                    return [], B_SharpSyntaxError(
                        pos_start,
                        self.pos,
                        "The '**' operator is not defined.",
                    )
                tokens.append(Token(TOKEN_MUL, pos_start=pos_start, pos_end=self.pos))
            elif self.current_char == "/":
                pos_start = self.pos.copy()
                self.forward()
                tokens.append(Token(TOKEN_DIV, pos_start=pos_start, pos_end=self.pos))
            elif self.current_char == "(":
                tokens.append(Token(TOKEN_LPAREN, pos_start=self.pos))
                self.forward()
            elif self.current_char == ")":
                tokens.append(Token(TOKEN_RPAREN, pos_start=self.pos))
                self.forward()
            elif self.current_char == "^":
                tokens.append(Token(TOKEN_POWER, pos_start=self.pos))
                self.forward()
            elif self.current_char == ":":
                tokens.append(Token(TOKEN_COLON, pos_start=self.pos))
                self.forward()
            elif self.current_char == ",":
                tokens.append(Token(TOKEN_COMMA, pos_start=self.pos))
                self.forward()
            elif self.current_char == "!":
                token, error = self.make_token_not_equal()
                if error:
                    return [], error
                if token:
                    tokens.append(token)
            elif self.current_char == "=":
                tokens.append(self.make_token_equal())
            elif self.current_char == ">":
                tokens.append(self.make_token_greater_than())
            elif self.current_char == "<":
                tokens.append(self.make_token_less_than())
            elif self.current_char == "[":
                tokens.append(Token(TOKEN_LBRACKET, pos_start=self.pos))
                self.forward()
            elif self.current_char == "]":
                tokens.append(Token(TOKEN_RBRACKET, pos_start=self.pos))
                self.forward()
            elif self.current_char in ('"', "'"):
                token, error = self.stringnize(self.current_char)
                if error:
                    return [], error
                tokens.append(token)
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.forward()
                return [], IllegalCharacterError(pos_start, self.pos, "'" + char + "'")

        tokens.append(Token(TOKEN_EOF, pos_start=self.pos))
        return tokens, None
