# B_Sharp/ASTNodes/parser.py

from B_Sharp.tokens import *
from B_Sharp.errors import *
from B_Sharp.ASTNodes.instances import *
from B_Sharp.ASTNodes.nodes import *


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
        self.current_token = None
        self.forward()

    def forward(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        return self.current_token

    ################################################################
    # Grammar Rules
    ################################################################

    def factor(self):
        res = ParserResults()
        token = self.current_token

        # Unary operations (+x, -x)
        if token.type in (TOKEN_PLUS, TOKEN_MINUS):
            res.register(self.forward())
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(BinaryNegationNode(token, factor))

        # Numbers
        elif token.type in (TOKEN_INT, TOKEN_FLOAT):
            res.register(self.forward())
            return res.success(NumberNode(token))

        # Literal `none`
        elif token.type == TOKEN_KEYWORD and token.value == "none":
            res.register(self.forward())
            return res.success(NoneNode(token))

        # Variable access (reading a variable)
        elif token.type == TOKEN_IDENTIFIER:
            res.register(self.forward())
            return res.success(VariableAccessNode(token))

        # Parenthesized expressions
        elif token.type == TOKEN_LPAREN:
            res.register(self.forward())
            expression = res.register(self.expression())
            if res.error:
                return res

            if self.current_token.type == TOKEN_RPAREN:
                res.register(self.forward())
                return res.success(expression)
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected ')' at end of expression.",
                    )
                )

        return res.failure(
            B_SharpSyntaxError(
                token.pos_start, token.pos_end, "Expected number, variable, or '('"
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

    def binary_operation(self, function, operations):
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

    ################################################################
    # Variable Parsing Rules
    ################################################################

    def var_decl(self):
        """Parses variable declarations:
        `var x : Number = 10`
        `const y = 12`
        `var x, y, z : Number = 15`
        """
        res = ParserResults()
        is_const = self.current_token.value == "const"
        start_tok = self.current_token
        res.register(self.forward())  # Consume 'var' or 'const'

        # Must have at least one identifier
        if self.current_token.type != TOKEN_IDENTIFIER:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected variable identifier name after 'var' or 'const'.",
                )
            )

        names = [self.current_token]
        res.register(self.forward())

        # Collect comma-separated variable names (e.g. var x, y, z)
        while self.current_token.type == TOKEN_COMMA:
            res.register(self.forward())
            if self.current_token.type != TOKEN_IDENTIFIER:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected identifier name after ','.",
                    )
                )
            names.append(self.current_token)
            res.register(self.forward())

        # Optional type declaration `: Type`
        type_tok = None
        if self.current_token.type == TOKEN_COLON:
            res.register(self.forward())
            if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                type_tok = self.current_token
                res.register(self.forward())
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected type identifier after ':'.",
                    )
                )

            # Unknown type names are a syntax error, not silent weak typing.
            if TYPE_MAP.get(type_tok.value.lower()) is None:
                return res.failure(
                    B_SharpSyntaxError(
                        type_tok.pos_start,
                        type_tok.pos_end,
                        f"Unknown data type '{type_tok.value}'. "
                        f"Valid types: number, boolean, complex, string, empty.",
                    )
                )

        # Value assignment `= value`
        value_node = None
        if self.current_token.type == TOKEN_EQUAL:
            res.register(self.forward())

            # Support chained declarations (e.g., var x = var y = 15)
            if (
                self.current_token.type == TOKEN_KEYWORD
                and self.current_token.value in ("var", "const")
            ):
                value_node = res.register(self.var_decl())
            else:
                value_node = res.register(self.expression())

            if res.error:
                return res

            # Check for invalid syntax: comma on RHS during initialization (e.g. var x, y = 14, none)
            if self.current_token.type == TOKEN_COMMA:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Multiple initializers in assignment are not supported.",
                    )
                )

        # Syntax Error Guard: const without value or without explicit type annotation
        if is_const and type_tok is None and value_node is None:
            return res.failure(
                B_SharpSyntaxError(
                    start_tok.pos_start,
                    self.current_token.pos_end,
                    "Uninitialized 'const' declaration requires a value or type.",
                )
            )

        # Return single or multi node
        if len(names) == 1:
            return res.success(
                VariableAssignNode(
                    names[0], value_node, is_const=is_const, type_define=type_tok
                )
            )
        else:
            return res.success(
                MultiVariableAssignNode(
                    names, value_node, is_const=is_const, type_define=type_tok
                )
            )

    def statement(self):
        """Top-level parser entry for statements"""
        res = ParserResults()

        # Variable Declaration (var / const)
        if self.current_token.type == TOKEN_KEYWORD and self.current_token.value in (
            "var",
            "const",
        ):
            return self.var_decl()

        # Variable Reassignment (x = value)
        if self.current_token.type == TOKEN_IDENTIFIER and self.token_index + 1 < len(
            self.tokens
        ):
            if self.tokens[self.token_index + 1].type == TOKEN_EQUAL:
                name_tok = self.current_token
                res.register(self.forward())  # Consume name
                res.register(self.forward())  # Consume '='
                value_node = res.register(self.expression())
                if res.error:
                    return res
                return res.success(VariableReassignNode(name_tok, value_node))

        # Default: Standard Expression
        return self.expression()

    def parser(self):
        res = self.statement()
        if not res.error and self.current_token.type != TOKEN_EOF:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Unexpected token or invalid syntax.",
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

    def visit_NoneNode(self, node, context):
        return RunTimeResult().success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
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

    def visit_VariableAccessNode(self, node, context):
        result = RunTimeResult()
        var_name = node.name.value
        value, error = context.variables.set_pos(node.pos_start, node.pos_end).get(
            var_name
        )

        if error:
            return result.failure(error)
        return result.success(value)

    def visit_VariableAssignNode(self, node, context):
        res = RunTimeResult()
        var_name = node.name.value

        if node.value:
            value = res.register(self.visit(node.value, context))
            if res.error:
                return res
        else:
            value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)

        data_type_class = None
        if node.data_type:
            data_type_class = TYPE_MAP.get(node.data_type.value.lower())

        val, error = context.variables.set_pos(node.pos_start, node.pos_end).define(
            name=var_name,
            data_type=data_type_class,
            value=value,
            is_const=node.is_const,
        )

        if error:
            return res.failure(error)
        return res.success(val)

    def visit_MultiVariableAssignNode(self, node, context):
        res = RunTimeResult()

        if node.value:
            value = res.register(self.visit(node.value, context))
            if res.error:
                return res
        else:
            value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)

        data_type_class = None
        if node.data_type:
            data_type_class = TYPE_MAP.get(node.data_type.value.lower())

        last_val = value
        for name_tok in node.names:
            var_name = name_tok.value
            val, error = context.variables.set_pos(
                name_tok.pos_start, name_tok.pos_end
            ).define(
                name=var_name,
                data_type=data_type_class,
                value=value,
                is_const=node.is_const,
            )
            if error:
                return res.failure(error)
            last_val = val

        return res.success(last_val)

    def visit_VariableReassignNode(self, node, context):
        res = RunTimeResult()
        var_name = node.name.value

        value = res.register(self.visit(node.value, context))
        if res.error:
            return res

        val, error = context.variables.set_pos(node.pos_start, node.pos_end).assign(
            name=var_name, value=value
        )

        if error:
            return res.failure(error)
        return res.success(val)
