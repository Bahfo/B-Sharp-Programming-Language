from errors import IllegalCharacaterError
from position import Position

TOKEN_INT = "INT"
TOKEN_FLOAT = "FLOAT"
TOKEN_PLUS = "PLUS"
TOKEN_MINUS = "MINUS"
TOKEN_MUL = "MUL"
TOKEN_DIV = "DIV"
TOKEN_LPAREN = "LPAREN"
TOKEN_RPAREN = "RPAREN"
DIGITS = "0123456789"


class Token:
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

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
            return Token(TOKEN_INT, int(number_str))
        else:
            return Token(TOKEN_FLOAT, float(number_str))

    def tokenize(self):
        tokens = []

        while self.current_char != None:
            if self.current_char in " \t":
                self.forward()
            elif self.current_char == "+":
                tokens.append(Token(TOKEN_PLUS))
                self.forward()
            elif self.current_char == "-":
                tokens.append(Token(TOKEN_MINUS))
                self.forward()
            elif self.current_char == "*":
                tokens.append(Token(TOKEN_MUL))
                self.forward()
            elif self.current_char == "/":
                tokens.append(Token(TOKEN_DIV))
                self.forward()
            elif self.current_char == "(":
                tokens.append(Token(TOKEN_LPAREN))
                self.forward()
            elif self.current_char == ")":
                tokens.append(Token(TOKEN_RPAREN))
                self.forward()
            elif self.current_char in DIGITS:
                tokens.append(self.numberize())
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.forward()
                return [], IllegalCharacaterError(pos_start, self.pos, "'" + char + "'")

        return tokens, None


def run(file_name, text):
    lexer = Lexer(file_name, text)
    tokens, error = lexer.tokenize()

    return tokens, error
