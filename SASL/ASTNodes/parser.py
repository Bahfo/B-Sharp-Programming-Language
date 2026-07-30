from SASL.tokens import *
from SASL.errors import *
from SASL.ASTNodes.number_node import *


class ParserResults:
    def __init__(self):
        self.error = None
        self.node = None

    def register(self, res):
        if isinstance(res, ParserResults):
            if res.error:
                self.error = res.error
            return res.node

        return res

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        self.error = error
        return self


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_index = -1
        self.forward()

    def forward(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        return self.current_token

    def factor(self):
        res = ParserResults()
        token = self.current_token

        if token.type in (TOKEN_PLUS, TOKEN_MINUS):
            res.register(self.forward())
            factor = res.register(self.factor())
            if res.error:
                return res

            return res.success(BinaryNegationNode(token, factor))

        elif token.type in (TOKEN_INT, TOKEN_FLOAT):
            res.register(self.forward())
            return res.success(NumberNode(token))

        elif token.type in (TOKEN_LPAREN):
            res.register(self.forward())
            expression = res.register(self.expression())

            if res.error:
                return res

            if token.type in (TOKEN_RPAREN):
                res.register(self.forward())
                return res.success(expression)
            else:
                return res.failure(
                    SASLSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected ')' at end of expression.\n",
                    )
                )

        return res.failure(
            SASLSyntaxError(
                token.pos_start, token.pos_end, "Expected number <int,float>"
            )
        )

    def term(self):
        return self.binary_operation(self.factor, (TOKEN_MUL, TOKEN_DIV))

    def expression(self):
        return self.binary_operation(self.term, (TOKEN_PLUS, TOKEN_MINUS))

    def binary_operation(self, function, operations) -> BinaryOpNode:
        """
        A helper function to add binary operations.
        """
        res = ParserResults()
        left = res.register(function())
        if res.error:
            return res

        while self.current_token.type in operations:
            op_token = self.current_token
            res.register(self.forward())
            right = res.register(function())

            if res.error:
                return res

            left = BinaryOpNode(left, op_token, right)
        return res.success(left)

    def parser(self):
        res = self.expression()
        if not res.error and self.current_token.type != TOKEN_EOF:
            return res.failure(
                SASLSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected a binary operation, got an unknown syntax.",
                )
            )
        return res
