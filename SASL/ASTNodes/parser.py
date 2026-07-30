from SASL.lexer import *
from SASL.ASTNodes.number_node import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_index = 1
        self.forward()

    def forward(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        return self.current_token

    def factor(self):
        token = self.current_token
        if token.type in (TOKEN_INT, TOKEN_FLOAT):
            self.forward()
            return NumberNode(token)

    def term(self):
        left = self.factor()

        while self.current_token.type in (TOKEN_MUL, TOKEN_DIV):
            op_token = self.current_token
            self.forward()
            right = self.factor()

            left = BinaryOpNode(left, op_token, right)
        return left

    def expression(self):
        left = self.term()

        while self.current_token.type in (TOKEN_PLUS, TOKEN_MINUS):
            op_token = self.current_token
            self.forward()
            right = self.term()

            left = BinaryOpNode(left, op_token, right)

    def binary_operation(self, function, operations) -> BinaryOpNode:
        """
        A helper function if to add more binary operations other than
        hardcoded later.
        """
        left = function()

        while self.current_token.type in operations:
            op_token = self.current_token
            self.forward()
            right = function()

            left = BinaryOpNode(left, op_token, right)
        return left

    def parser(self):
        res = self.expression()
        return res
