from SASL.tokens import *
from SASL.errors import *
from SASL.ASTNodes.instances import *
from SASL.ASTNodes.nodes import *


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

            if self.current_token.type in (TOKEN_RPAREN):
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

    def power(self):
        res = ParserResults()
        left = res.register(self.factor())
        if res.error:
            return res

        if self.current_token.type == TOKEN_POWER:
            op_token = self.current_token
            res.register(self.forward())
            right = res.register(self.power())
            if res.error:
                return res
            left = BinaryOpNode(left, op_token, right)

        return res.success(left)

    def term(self):
        return self.binary_operation(self.power, (TOKEN_MUL, TOKEN_DIV))

    def expression(self):
        return self.binary_operation(self.term, (TOKEN_PLUS, TOKEN_MINUS))

    def binary_operation(self, function, operations) -> BinaryOpNode:
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


class RunTimeResult:
    def __init__(self):
        self.error = None
        self.value = None

    def register(self, res):
        if isinstance(res, RunTimeResult):
            if res.error:
                self.error = res.error
            return res.value
        return res

    def success(self, value):
        self.value = value
        return self

    def failure(self, error):
        self.error = error
        return self


class Interpreter:
    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")

    ###################################

    def visit_NumberNode(self, node, context):
        return RunTimeResult().success(
            Number(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_BinaryOpNode(self, node, context):
        res = RunTimeResult()
        left = res.register(self.visit(node.left_node, context))
        if res.error:
            return res

        right = res.register(self.visit(node.right_node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_PLUS:
            result, error = left.addition(right)
        elif node.op_token.type == TOKEN_MINUS:
            result, error = left.subtraction(right)
        elif node.op_token.type == TOKEN_MUL:
            result, error = left.multiplication(right)
        elif node.op_token.type == TOKEN_DIV:
            result, error = left.division(right)
        elif node.op_token.type == TOKEN_POWER:
            result, error = left.power(right)

        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_BinaryNegationNode(self, node, context):
        res = RunTimeResult()
        number = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_MINUS:
            number, error = number.multiplication(Number(-1))
            if error:
                return res.failure(error)

        return res.success(number.set_pos(node.pos_start, node.pos_end))
