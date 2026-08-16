import sys

from B_Sharp.tokens import *
from B_Sharp.errors import *
from B_Sharp.ASTNodes.instances import *
from B_Sharp.ASTNodes.nodes import *


class ParserResults:
    def __init__(self):
        self.error = None
        self.node = None
        self.forward_count = 0

    def register(self, res):
        if isinstance(res, ParserResults):
            if res.error:
                self.error = res.error
            return res.node
        return res

    def register_forward(self):
        self.forward_count += 1

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        if not self.error or self.forward_count == 0:
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
    # Precedence (lowest to highest):
    #   expression  → and | or
    #   comparison  → == != < > <= >=
    #   term        → + -
    #   factor      → * /
    #   unary       → + - not
    #   power       → ^
    #   atom        → INT FLOAT BOOLEAN IDENTIFIER none (expr)
    ################################################################

    def atom(self):
        res = ParserResults()
        tok = self.current_token

        # Prefix ++x or --x
        if tok.type in (TOKEN_INC, TOKEN_DEC):
            return self.increment_or_decrement()

        # Identifier: Var access OR Postfix x++ / x--
        elif tok.type == TOKEN_IDENTIFIER:
            var_tok = tok
            res.register_forward()
            self.forward()

            if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
                op_tok = self.current_token
                res.register_forward()
                self.forward()
                return res.success(IncrementNode(var_tok, op_tok, is_postfix=True))

            return res.success(VariableAccessNode(var_tok))

        elif tok.type in (TOKEN_INT, TOKEN_FLOAT):
            res.register_forward()
            self.forward()
            return res.success(NumberNode(tok))

        elif tok.type == TOKEN_STRING:
            res.register_forward()
            self.forward()
            return res.success(StringNode(tok))

        elif tok.type == TOKEN_LPAREN:
            res.register_forward()
            self.forward()
            expr = res.register(self.expression())
            if res.error:
                return res
            if self.current_token.type == TOKEN_RPAREN:
                res.register_forward()
                self.forward()
                return res.success(expr)
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected ')'",
                )
            )

        elif tok.type == TOKEN_KEYWORD and tok.value in ("true", "false"):
            res.register_forward()
            self.forward()
            return res.success(BooleanNode(tok))

        elif tok.type == TOKEN_KEYWORD and tok.value == "none":
            res.register_forward()
            self.forward()
            return res.success(NoneNode(tok))

        elif tok.type == TOKEN_KEYWORD and tok.value == "if":
            return self.if_expression()

        return res.failure(
            B_SharpSyntaxError(
                tok.pos_start,
                tok.pos_end,
                f"Expected int, float, identifier, '+', '-', '(', or keyword, got '{tok}'",
            )
        )

    def if_expression(self):
        res = ParserResults()
        cases = []
        else_case = None

        if not self.current_token.matches(TOKEN_KEYWORD, "if"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'if'",
                )
            )

        res.register_forward()
        self.forward()

        condition = res.register(self.expression())
        if res.error:
            return res

        # Check for block '{' or keyword 'then'
        if self.current_token.type == TOKEN_LCURLY:
            expr = res.register(self.block())
            if res.error:
                return res
            cases.append((condition, expr))
        elif self.current_token.matches(TOKEN_KEYWORD, "then"):
            res.register_forward()
            self.forward()
            expr = res.register(self.statement())
            if res.error:
                return res
            cases.append((condition, expr))
        else:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'then' or '{' after if condition.",
                )
            )

        # Handle 'elif' clauses
        while self.current_token.matches(TOKEN_KEYWORD, "elif"):
            res.register_forward()
            self.forward()

            condition = res.register(self.expression())
            if res.error:
                return res

            if self.current_token.type == TOKEN_LCURLY:
                expr = res.register(self.block())
                if res.error:
                    return res
                cases.append((condition, expr))
            elif self.current_token.matches(TOKEN_KEYWORD, "then"):
                res.register_forward()
                self.forward()
                expr = res.register(self.statement())
                if res.error:
                    return res
                cases.append((condition, expr))
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected 'then' or '{' after elif condition.",
                    )
                )

        # Handle 'else' clause
        if self.current_token.matches(TOKEN_KEYWORD, "else"):
            res.register_forward()
            self.forward()

            if self.current_token.type == TOKEN_LCURLY:
                else_case = res.register(self.block())
                if res.error:
                    return res
            elif self.current_token.matches(TOKEN_KEYWORD, "then"):
                res.register_forward()
                self.forward()
                else_case = res.register(self.statement())
                if res.error:
                    return res
            else:
                else_case = res.register(self.statement())
                if res.error:
                    return res

        return res.success(IfNode(cases, else_case))

    def power(self):
        res = ParserResults()
        left = res.register(self.call())
        if res.error:
            return res

        if self.current_token.type == TOKEN_POWER:
            op_token = self.current_token
            res.register(self.forward())
            right = res.register(self.unary())
            if res.error:
                return res
            left = BinaryOpNode(left, op_token, right)

        return res.success(left)

    def unary(self):
        res = ParserResults()
        token = self.current_token

        if token.type in (TOKEN_PLUS, TOKEN_MINUS):
            res.register(self.forward())
            operand = res.register(self.unary())
            if res.error:
                return res
            return res.success(UnaryOpNode(token, operand))

        if token.type == TOKEN_KEYWORD and token.value == "not":
            res.register(self.forward())
            operand = res.register(self.unary())
            if res.error:
                return res
            return res.success(UnaryOpNode(token, operand))

        return self.power()

    def factor(self):
        return self.binary_operation(self.unary, (TOKEN_MUL, TOKEN_DIV, TOKEN_IDIV))

    def term(self):
        return self.binary_operation(self.factor, (TOKEN_PLUS, TOKEN_MINUS))

    def comparison(self):
        return self.binary_operation(
            self.term,
            (TOKEN_EE, TOKEN_NOT_E, TOKEN_LT, TOKEN_GT, TOKEN_LTE, TOKEN_GTE),
        )

    def and_expression(self):
        return self.binary_operation(self.comparison, ("and",))

    def or_expression(self):
        return self.binary_operation(self.and_expression, ("or",))

    def expression(self):
        return self.or_expression()

    def binary_operation(self, function, operations):
        res = ParserResults()
        left = res.register(function())
        if res.error:
            return res

        while self.current_token.type in operations or (
            self.current_token.type == TOKEN_KEYWORD
            and self.current_token.value in operations
        ):
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
        res.register(self.forward())

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

            if TYPE_MAP.get(type_tok.value.lower()) is None:
                return res.failure(
                    B_SharpSyntaxError(
                        type_tok.pos_start,
                        type_tok.pos_end,
                        f"Unknown data type '{type_tok.value}'. "
                        f"Valid types: number, boolean, complex, string, empty.",
                    )
                )

        value_node = None
        if self.current_token.type == TOKEN_EQUAL:
            res.register(self.forward())

            if (
                self.current_token.type == TOKEN_KEYWORD
                and self.current_token.value in ("var", "const")
            ):
                value_node = res.register(self.var_decl())
            else:
                value_node = res.register(self.expression())

            if res.error:
                return res

            if self.current_token.type == TOKEN_COMMA:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Multiple initializers in assignment are not supported.",
                    )
                )

        if is_const and type_tok is None and value_node is None:
            return res.failure(
                B_SharpSyntaxError(
                    start_tok.pos_start,
                    self.current_token.pos_end,
                    "Uninitialized 'const' declaration requires a value or type.",
                )
            )

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
        res = ParserResults()

        if self.current_token.type == TOKEN_KEYWORD:
            if self.current_token.value in ("var", "const"):
                return self.var_decl()
            elif self.current_token.value == "fn":
                return self.fn_def()
            elif self.current_token.value == "return":
                return self.return_statement()
            elif self.current_token.value == "if":
                return self.if_expression()
            elif self.current_token.value == "while":
                return self.while_expression()
            elif self.current_token.value == "for":
                return self.for_expression()

        # Prefix ++i / --i
        if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
            return self.increment_or_decrement()

        # Check for identifier actions: assignment or postfix i++ / i--
        if self.current_token.type == TOKEN_IDENTIFIER and self.token_index + 1 < len(
            self.tokens
        ):
            next_tok = self.tokens[self.token_index + 1]

            if next_tok.type == TOKEN_EQUAL:
                name_tok = self.current_token
                res.register(self.forward())
                res.register(self.forward())
                value_node = res.register(self.expression())
                if res.error:
                    return res
                return res.success(VariableReassignNode(name_tok, value_node))

        return self.expression()

    def statements(self):
        res = ParserResults()
        statement_list = []

        while self.current_token.type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
            res.register_forward()
            self.forward()

        if self.current_token.type in (TOKEN_EOF, TOKEN_RCURLY):
            return res.success(StatementsNode([]))

        stmt = res.register(self.statement())
        if res.error:
            return res
        statement_list.append(stmt)

        while True:
            newline_count = 0
            while self.current_token.type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
                res.register_forward()
                self.forward()
                newline_count += 1

            if self.current_token.type in (TOKEN_EOF, TOKEN_RCURLY):
                break

            if newline_count == 0:
                # A closing brace terminates a block statement, so the next
                # statement may begin on the same line ('} stmt;').
                previous_is_rcurly = (
                    self.token_index > 0
                    and self.tokens[self.token_index - 1].type == TOKEN_RCURLY
                )
                if not previous_is_rcurly:
                    break

            stmt = res.register(self.statement())
            if res.error:
                return res
            statement_list.append(stmt)

        return res.success(StatementsNode(statement_list))

    def parser(self):
        res = self.statements()
        if not res.error and self.current_token.type != TOKEN_EOF:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Unexpected token or invalid syntax.",
                )
            )
        return res

    def block(self):
        res = ParserResults()

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '{'",
                )
            )

        lcurly_pos = self.current_token.pos_start
        res.register_forward()
        self.forward()

        statements_node = res.register(self.statements())
        if res.error:
            return res

        if self.current_token.type != TOKEN_RCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '}'",
                )
            )

        rcurly_pos = self.current_token.pos_end
        if not statements_node.statement_nodes:
            statements_node.pos_start = lcurly_pos
            statements_node.pos_end = rcurly_pos

        res.register_forward()
        self.forward()

        return res.success(statements_node)

    def increment_or_decrement(self):
        res = ParserResults()

        # Prefix ++i or --i
        if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
            op_tok = self.current_token
            res.register_forward()
            self.forward()

            if self.current_token.type != TOKEN_IDENTIFIER:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected variable identifier after '++' or '--'.",
                    )
                )

            var_tok = self.current_token
            res.register_forward()
            self.forward()
            return res.success(IncrementNode(var_tok, op_tok, is_postfix=False))

        return res.failure(
            B_SharpSyntaxError(
                self.current_token.pos_start,
                self.current_token.pos_end,
                "Invalid increment/decrement expression.",
            )
        )

    def while_expression(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "while"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'while'",
                )
            )

        res.register_forward()
        self.forward()

        condition = res.register(self.expression())
        if res.error:
            return res

        if self.current_token.type == TOKEN_LCURLY:
            body = res.register(self.block())
        elif self.current_token.matches(TOKEN_KEYWORD, "then"):
            res.register_forward()
            self.forward()
            body = res.register(self.statement())
        else:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '{' or 'then' after while condition.",
                )
            )

        if res.error:
            return res

        return res.success(WhileNode(condition, body))

    def for_expression(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "for"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'for'",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '(' after 'for'.",
                )
            )

        res.register_forward()
        self.forward()

        # 1. Initializer: var i = 0 or i = 0
        init_node = res.register(self.statement())
        if res.error:
            return res

        if self.current_token.type != TOKEN_SEMICOLON:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected ';' after for loop initializer.",
                )
            )

        res.register_forward()
        self.forward()

        # 2. Condition: i < 10
        condition_node = res.register(self.expression())
        if res.error:
            return res

        if self.current_token.type != TOKEN_SEMICOLON:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected ';' after for loop condition.",
                )
            )

        res.register_forward()
        self.forward()

        # 3. Update expression: i++ / ++i / i = i + 1
        update_node = res.register(self.statement())
        if res.error:
            return res

        if self.current_token.type != TOKEN_RPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected ')' after for loop header.",
                )
            )

        res.register_forward()
        self.forward()

        # 4. Body: { ... } or then statement
        if self.current_token.type == TOKEN_LCURLY:
            body_node = res.register(self.block())
        elif self.current_token.matches(TOKEN_KEYWORD, "then"):
            res.register_forward()
            self.forward()
            body_node = res.register(self.statement())
        else:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '{' or 'then' after for loop expression.",
                )
            )

        if res.error:
            return res

        return res.success(ForNode(init_node, condition_node, update_node, body_node))

    def call(self):
        res = ParserResults()
        atom = res.register(self.atom())
        if res.error:
            return res

        if self.current_token.type == TOKEN_LPAREN:
            return self.finish_call(atom)

        return res.success(atom)

    def finish_call(self, node_to_call):
        res = ParserResults()
        arg_nodes = []

        res.register_forward()
        self.forward()  # skip '('

        if self.current_token.type == TOKEN_RPAREN:
            rparen_pos = self.current_token.pos_end
            res.register_forward()
            self.forward()  # skip ')'
            return res.success(CallNode(node_to_call, arg_nodes, pos_end=rparen_pos))

        arg_nodes.append(res.register(self.expression()))
        if res.error:
            return res

        while self.current_token.type == TOKEN_COMMA:
            res.register_forward()
            self.forward()

            arg_nodes.append(res.register(self.expression()))
            if res.error:
                return res

        if self.current_token.type != TOKEN_RPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected ',' or ')'",
                )
            )

        rparen_pos = self.current_token.pos_end
        res.register_forward()
        self.forward()
        return res.success(CallNode(node_to_call, arg_nodes, pos_end=rparen_pos))

    def fn_def(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "fn"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'fn'",
                )
            )

        res.register_forward()
        self.forward()

        # Name casting rule: anonymous functions are invalid
        if self.current_token.type != TOKEN_IDENTIFIER:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected function name identifier after 'fn'. Anonymous functions are not allowed.",
                )
            )

        var_name_tok = self.current_token
        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '(' after function name.",
                )
            )

        res.register_forward()
        self.forward()
        arg_nodes = []
        seen_param_names = set()

        if self.current_token.type == TOKEN_RPAREN:
            res.register_forward()
            self.forward()
        else:
            if self.current_token.type != TOKEN_IDENTIFIER:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected parameter name identifier.",
                    )
                )

            param_name = self.current_token
            res.register_forward()
            self.forward()

            param_type = None
            if self.current_token.type == TOKEN_COLON:
                res.register_forward()
                self.forward()
                if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                    param_type = self.current_token
                    res.register_forward()
                    self.forward()
                    if TYPE_MAP.get(param_type.value.lower()) is None:
                        return res.failure(
                            B_SharpSyntaxError(
                                param_type.pos_start,
                                param_type.pos_end,
                                f"Unknown data type '{param_type.value}'.",
                            )
                        )
                else:
                    return res.failure(
                        B_SharpSyntaxError(
                            self.current_token.pos_start,
                            self.current_token.pos_end,
                            "Expected type identifier after ':'.",
                        )
                    )

            arg_nodes.append((param_name, param_type))
            if param_name.value in seen_param_names:
                return res.failure(
                    B_SharpSyntaxError(
                        param_name.pos_start,
                        param_name.pos_end,
                        f"Duplicate parameter name '{param_name.value}' in function '{var_name_tok.value}'.",
                    )
                )
            seen_param_names.add(param_name.value)

            while self.current_token.type == TOKEN_COMMA:
                res.register_forward()
                self.forward()

                if self.current_token.type != TOKEN_IDENTIFIER:
                    return res.failure(
                        B_SharpSyntaxError(
                            self.current_token.pos_start,
                            self.current_token.pos_end,
                            "Expected parameter name identifier after ','.",
                        )
                    )

                param_name = self.current_token
                res.register_forward()
                self.forward()

                param_type = None
                if self.current_token.type == TOKEN_COLON:
                    res.register_forward()
                    self.forward()
                    if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                        param_type = self.current_token
                        res.register_forward()
                        self.forward()
                        if TYPE_MAP.get(param_type.value.lower()) is None:
                            return res.failure(
                                B_SharpSyntaxError(
                                    param_type.pos_start,
                                    param_type.pos_end,
                                    f"Unknown data type '{param_type.value}'.",
                                )
                            )
                    else:
                        return res.failure(
                            B_SharpSyntaxError(
                                self.current_token.pos_start,
                                self.current_token.pos_end,
                                "Expected type identifier after ':'.",
                            )
                        )

                arg_nodes.append((param_name, param_type))
                if param_name.value in seen_param_names:
                    return res.failure(
                        B_SharpSyntaxError(
                            param_name.pos_start,
                            param_name.pos_end,
                            f"Duplicate parameter name '{param_name.value}' in function '{var_name_tok.value}'.",
                        )
                    )
                seen_param_names.add(param_name.value)

            if self.current_token.type != TOKEN_RPAREN:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected ',' or ')' in parameter list.",
                    )
                )

            res.register_forward()
            self.forward()

        return_type_tok = None
        if self.current_token.type == TOKEN_ARROW:
            res.register_forward()
            self.forward()

            if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                return_type_tok = self.current_token
                res.register_forward()
                self.forward()
                if TYPE_MAP.get(return_type_tok.value.lower()) is None:
                    return res.failure(
                        B_SharpSyntaxError(
                            return_type_tok.pos_start,
                            return_type_tok.pos_end,
                            f"Unknown return type '{return_type_tok.value}'.",
                        )
                    )
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected return type identifier after '->'.",
                    )
                )

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '{' to start function body block.",
                )
            )

        body_node = res.register(self.block())
        if res.error:
            return res

        return res.success(
            FunctionDefNode(var_name_tok, arg_nodes, return_type_tok, body_node)
        )

    def return_statement(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "return"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'return'",
                )
            )

        start_pos = self.current_token.pos_start.copy()
        end_pos = self.current_token.pos_end.copy()

        res.register_forward()
        self.forward()

        if self.current_token.type in (
            TOKEN_NEWLINE,
            TOKEN_SEMICOLON,
            TOKEN_RCURLY,
            TOKEN_EOF,
        ):
            return res.success(ReturnNode(None, start_pos, end_pos))

        expr = res.register(self.expression())
        if res.error:
            return res

        return res.success(ReturnNode(expr, start_pos, expr.pos_end))


class RunTimeResult:
    def __init__(self):
        self.error = None
        self.value = None
        self.func_return_value = None

    def register(self, res):
        if isinstance(res, RunTimeResult):
            if res.error:
                self.error = res.error
            if res.func_return_value is not None:
                self.func_return_value = res.func_return_value
            return res.value
        return res

    def success(self, value):
        self.value = value
        return self

    def success_return(self, value):
        self.func_return_value = value
        return self

    def failure(self, error):
        self.error = error
        return self


class Interpreter:
    def __init__(self, max_call_depth=500):
        self.max_call_depth = max_call_depth
        self.current_call_depth = 0
        if sys.getrecursionlimit() < 10000:
            sys.setrecursionlimit(10000)

    def _inside_function(self, context):
        current = context
        while current is not None:
            if getattr(current, "in_function", False):
                return True
            current = current.parent
        return False

    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")

    ################################################################
    # Visitors
    ################################################################

    def visit_NumberNode(self, node, context):
        return RunTimeResult().success(
            Number(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_BooleanNode(self, node, context):
        value = node.token.value == "true"
        return RunTimeResult().success(
            Boolean(value).set_context(context).set_pos(node.pos_start, node.pos_end)
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

        # 'and'/'or' short-circuit: the right operand is only evaluated when
        # the result can still change.
        if node.op_token.type == TOKEN_KEYWORD and node.op_token.value in (
            "and",
            "or",
        ):
            return self.visit_short_circuit(node, left, res, context)

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
        elif node.op_token.type == TOKEN_IDIV:
            result, error = left.integer_division(right)
        elif node.op_token.type == TOKEN_POWER:
            result, error = left.power(right)
        elif node.op_token.type == TOKEN_EE:
            result, error = left.is_equal(right)
        elif node.op_token.type == TOKEN_NOT_E:
            result, error = left.not_equal(right)
        elif node.op_token.type == TOKEN_LT:
            result, error = left.less_than(right)
        elif node.op_token.type == TOKEN_GT:
            result, error = left.greater_than(right)
        elif node.op_token.type == TOKEN_LTE:
            result, error = left.less_than_equal(right)
        elif node.op_token.type == TOKEN_GTE:
            result, error = left.greater_than_equal(right)
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                f"Unknown binary operator '{node.op_token.value or node.op_token.type}'.",
            )

        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_short_circuit(self, node, left, res, context):
        is_and = node.op_token.value == "and"

        if isinstance(left, Boolean):
            if is_and:
                if left.value:
                    right = res.register(self.visit(node.right_node, context))
                    if res.error:
                        return res
                    result, error = left.and_(right)
                else:
                    result, error = Boolean(False), None
            else:
                if left.value:
                    result, error = Boolean(True), None
                else:
                    right = res.register(self.visit(node.right_node, context))
                    if res.error:
                        return res
                    result, error = left.or_(right)
        else:
            result, error = left.and_(left) if is_and else left.or_(left)

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RunTimeResult()
        operand = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_MINUS:
            result, error = operand.multiplication(Number(-1))
        elif node.op_token.type == TOKEN_PLUS:
            result, error = operand, None
        elif node.op_token.type == TOKEN_KEYWORD and node.op_token.value == "not":
            result, error = operand.not_()
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                f"Unknown unary operator '{node.op_token.value}'.",
            )

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_BinaryNegationNode(self, node, context):
        res = RunTimeResult()
        operand = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_MINUS:
            result, error = operand.multiplication(Number(-1))
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                f"Unknown binary negation operator '{node.op_token.value}'.",
            )

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

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

    def visit_IfNode(self, node, context):
        res = RunTimeResult()

        for condition, expression in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.error:
                return res

            if condition_value.true_():
                branch_context = Context("<if>", context, node.pos_start)
                expression_value = res.register(self.visit(expression, branch_context))
                if res.error:
                    return res
                if res.func_return_value is not None:
                    return res
                return res.success(expression_value)

        if node.else_case:
            branch_context = Context("<if>", context, node.pos_start)
            else_value = res.register(self.visit(node.else_case, branch_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res
            return res.success(else_value)

        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_StatementsNode(self, node, context):
        res = RunTimeResult()
        last_value = Empty().set_context(context)

        for stmt in node.statement_nodes:
            value = res.register(self.visit(stmt, context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res
            last_value = value

        return res.success(last_value)

    def visit_StringNode(self, node, context):
        return RunTimeResult().success(
            String(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_IncrementNode(self, node, context):
        res = RunTimeResult()

        var_name = node.var_name_tok.value
        val, error = context.variables.set_pos(node.pos_start, node.pos_end).get(
            var_name
        )

        if error:
            return res.failure(error)

        if not isinstance(val, Number):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Increment/decrement operations are only supported on Number types.",
                )
            )

        old_num = val.value
        new_num = old_num + 1 if node.op_tok.type == TOKEN_INC else old_num - 1
        new_val = (
            Number(new_num).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

        _, assign_err = context.variables.set_pos(node.pos_start, node.pos_end).assign(
            var_name, new_val
        )
        if assign_err:
            return res.failure(assign_err)

        return res.success(
            Number(old_num if node.is_postfix else new_num)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_WhileNode(self, node, context):
        res = RunTimeResult()
        elements = []

        while True:
            cond_val = res.register(self.visit(node.condition_node, context))
            if res.error:
                return res

            if not cond_val.true_():
                break

            body_context = Context("<while>", context, node.pos_start)
            val = res.register(self.visit(node.body_node, body_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res

            elements.append(val)

        return res.success(
            elements[-1] if len(elements) > 0 else Empty().set_context(context)
        )

    def visit_ForNode(self, node, context):
        res = RunTimeResult()
        elements = []

        loop_context = Context("<for>", context, node.pos_start)
        res.register(self.visit(node.init_node, loop_context))
        if res.error:
            return res

        while True:
            cond_val = res.register(self.visit(node.condition_node, loop_context))
            if res.error:
                return res

            if not cond_val.true_():
                break

            body_context = Context("<for>", loop_context, node.pos_start)
            val = res.register(self.visit(node.body_node, body_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res

            elements.append(val)

            res.register(self.visit(node.update_node, loop_context))
            if res.error:
                return res

        return res.success(
            elements[-1] if len(elements) > 0 else Empty().set_context(context)
        )

    def visit_FunctionDefNode(self, node, context):
        res = RunTimeResult()

        func_name = node.var_name_tok.value
        body_node = node.body_node
        arg_nodes = node.arg_nodes
        return_type_tok = node.return_type_tok

        func_value = Function(
            name=func_name,
            body_node=body_node,
            arg_nodes=arg_nodes,
            return_type_tok=return_type_tok,
            parent_context=context,
        ).set_pos(node.pos_start, node.pos_end)

        val, error = context.variables.set_pos(node.pos_start, node.pos_end).define(
            name=func_name,
            data_type=Function,
            value=func_value,
            is_const=False,
        )

        if error:
            return res.failure(error)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RunTimeResult()

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.error:
            return res

        if not isinstance(value_to_call, Function):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'{node.node_to_call}' is not a function.",
                )
            )

        args = []
        for arg_node in node.arg_nodes:
            arg_val = res.register(self.visit(arg_node, context))
            if res.error:
                return res
            args.append(arg_val)

        if self.current_call_depth >= self.max_call_depth:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Maximum call depth exceeded (recursion too deep).",
                )
            )

        self.current_call_depth += 1
        try:
            return_value = res.register(
                value_to_call.execute(
                    args, self, call_pos_start=node.pos_start, call_pos_end=node.pos_end
                )
            )
        finally:
            self.current_call_depth -= 1

        if res.error:
            return res

        return res.success(return_value)

    def visit_ReturnNode(self, node, context):
        res = RunTimeResult()

        if not self._inside_function(context):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot use 'return' outside of a function.",
                )
            )

        if node.node_to_return:
            return_val = res.register(self.visit(node.node_to_return, context))
            if res.error:
                return res
        else:
            return_val = (
                Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        return res.success_return(return_val)
