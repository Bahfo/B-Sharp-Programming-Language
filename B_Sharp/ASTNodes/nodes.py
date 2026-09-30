import math


class NumberNode:
    def __init__(self, token):
        self.token = token
        self.pos_start = token.pos_start
        self.pos_end = token.pos_end

    def __repr__(self):
        return f"{self.token}"


class BooleanNode:
    def __init__(self, token):
        self.token = token
        self.pos_start = token.pos_start
        self.pos_end = token.pos_end

    def __repr__(self):
        return f"{self.token.value}"


class UnaryOpNode:
    def __init__(self, op_token, node):
        self.op_token = op_token
        self.node = node
        self.pos_start = op_token.pos_start
        self.pos_end = node.pos_end

    def __repr__(self):
        return f"({self.op_token} : {self.node})"


class BinaryOpNode:
    def __init__(self, left_node, op_token, right_node):
        self.left_node = left_node
        self.op_token = op_token
        self.right_node = right_node
        self.pos_start = left_node.pos_start
        self.pos_end = right_node.pos_end

    def __repr__(self):
        return f"({self.left_node} : {self.op_token} : {self.right_node})"


class VariableAssignNode:
    def __init__(self, name, value=None, is_const=False, type_define=False):
        self.name = name
        self.value = value
        self.is_const = is_const
        self.data_type = type_define

        self.pos_start = name.pos_start
        self.pos_end = (
            value.pos_end
            if value
            else (type_define.pos_end if self.data_type else name.pos_end)
        )

    def __repr__(self):
        kind = "const" if self.is_const else "var"
        type_str = f" : {self.data_type.value}" if self.data_type else ""
        return f"{kind} {self.name.value}{type_str} = {self.value}"


class MultiVariableAssignNode:
    def __init__(self, names: list, value=None, is_const=False, type_define=False):
        self.names = names
        self.value = value
        self.is_const = is_const
        self.data_type = type_define

        self.pos_start = names[0].pos_start
        self.pos_end = (
            value.pos_end
            if value
            else (type_define.pos_end if type_define else names[-1].pos_end)
        )

    def __repr__(self):
        names = ", ".join(tok.value for tok in self.names)
        kind = "const" if self.is_const else "var"
        type_str = f" : {self.data_type.value}" if self.data_type else ""
        return f"{kind} [{names}]{type_str} = {self.value}"


class VariableReassignNode:
    def __init__(self, name, value):
        self.name = name
        self.value = value

        self.pos_start = name.pos_start
        self.pos_end = value.pos_end

    def __repr__(self):
        return f"{self.name.value} = {self.value}"


class VariableAccessNode:
    def __init__(self, name):
        self.name = name

        self.pos_start = name.pos_start
        self.pos_end = name.pos_end

    def __repr__(self):
        return f"{self.name.value}"


class NoneNode:
    """Node for literal `none` keyword value"""

    def __init__(self, token):
        self.tok = token

        self.pos_start = token.pos_start
        self.pos_end = token.pos_end

    def __repr__(self):
        return "none"


class ListNode:
    """Node for a list."""

    def __init__(self, list_of_expressions, pos_start, pos_end):
        self.list_of_expressions = list_of_expressions
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"{self.list_of_expressions}"


class TupleNode:
    """Node for a tuple literal `(a, b, c)`."""

    def __init__(self, tuple_of_expressions, pos_start, pos_end):
        self.tuple_of_expressions = tuple_of_expressions
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"Tuple ({self.tuple_of_expressions})"


class IfNode:
    def __init__(self, cases, else_case):
        self.cases = cases
        self.else_case = else_case

        self.pos_start = self.cases[0][0].pos_start
        last_case = self.cases[len(self.cases) - 1][1]
        if self.else_case is not None and self.else_case.pos_end is not None:
            self.pos_end = self.else_case.pos_end
        elif last_case.pos_end is not None:
            self.pos_end = last_case.pos_end
        else:
            self.pos_end = self.pos_start


class StatementsNode:
    def __init__(self, statement_nodes, pos_start=None, pos_end=None):
        self.statement_nodes = statement_nodes
        if statement_nodes:
            self.pos_start = statement_nodes[0].pos_start
            self.pos_end = statement_nodes[-1].pos_end
        else:
            self.pos_start = pos_start
            self.pos_end = pos_end

    def __repr__(self):
        return f"Statements ({self.statement_nodes})"


class StringNode:
    def __init__(self, token):
        self.token = token
        self.pos_start = token.pos_start
        self.pos_end = token.pos_end

    def __repr__(self):
        return f"{self.token}"


class IncrementNode:
    def __init__(self, var_name_tok, op_tok, is_postfix=True):
        self.var_name_tok = var_name_tok
        self.op_tok = op_tok
        self.is_postfix = is_postfix

        self.pos_start = var_name_tok.pos_start if is_postfix else op_tok.pos_start
        self.pos_end = op_tok.pos_end if is_postfix else var_name_tok.pos_end

    def __repr__(self):
        return (
            f"{self.var_name_tok.value}{self.op_tok.value}"
            if self.is_postfix
            else f"{self.op_tok.value}{self.var_name_tok.value}"
        )


class WhileNode:
    def __init__(self, condition_node, body_node):
        self.condition_node = condition_node
        self.body_node = body_node

        self.pos_start = condition_node.pos_start
        self.pos_end = body_node.pos_end

    def __repr__(self):
        return f"while ({self.condition_node}) {self.body_node}"


class DoNode:
    def __init__(self, body_node, condition_node, pos_start, pos_end):
        self.body_node = body_node
        self.condition_node = condition_node
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"do {self.body_node} while ({self.condition_node})"


class ForNode:
    def __init__(self, init_node, condition_node, update_node, body_node):
        self.init_node = init_node
        self.condition_node = condition_node
        self.update_node = update_node
        self.body_node = body_node

        self.pos_start = init_node.pos_start
        self.pos_end = body_node.pos_end

    def __repr__(self):
        return f"for ({self.init_node}; {self.condition_node}; {self.update_node}) {self.body_node}"


class FunctionDefNode:
    def __init__(self, var_name_tok, arg_nodes, return_type_tok, body_node):
        self.var_name_tok = var_name_tok
        self.arg_nodes = arg_nodes
        self.return_type_tok = return_type_tok
        self.body_node = body_node

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.body_node.pos_end

    def __repr__(self):
        return f"fn {self.var_name_tok.value}({self.arg_nodes}) -> {self.return_type_tok} {self.body_node}"


class CallNode:
    def __init__(self, node_to_call, arg_nodes, arg_names=None, pos_end=None):
        self.node_to_call = node_to_call
        self.arg_nodes = arg_nodes
        # Parallel to arg_nodes: the `name` token of a `name = value`
        # argument, or None when the argument is positional.
        self.arg_names = arg_names if arg_names is not None else [None] * len(arg_nodes)

        self.pos_start = self.node_to_call.pos_start
        self.pos_end = (
            pos_end
            if pos_end
            else (
                self.arg_nodes[-1].pos_end
                if len(self.arg_nodes) > 0
                else self.node_to_call.pos_end
            )
        )

    def __repr__(self):
        return f"{self.node_to_call}({self.arg_nodes})"


class ReturnNode:
    def __init__(self, node_to_return, pos_start, pos_end):
        self.node_to_return = node_to_return
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"return {self.node_to_return}"


class PropertyAccessNode:
    def __init__(self, node, property_name_tok):
        self.node = node  # the object being accessed
        self.property_name_token = property_name_tok  # TOKEN_IDENTIFIER
        self.pos_start = node.pos_start
        self.pos_end = property_name_tok.pos_end


class IndexAccessNode:
    def __init__(self, node, index_node):
        self.node = node  # the list/array/string being indexed
        self.index_node = index_node  # expression node for the index
        self.pos_start = node.pos_start
        self.pos_end = self.index_node.pos_end


class SliceNode:
    def __init__(self, node, start_node, end_node, pos_end):
        self.node = node
        self.start_node = start_node
        self.end_node = end_node
        self.pos_start = node.pos_start
        self.pos_end = pos_end


class IndexAssignNode:
    def __init__(self, target, value_node):
        self.target = target  # IndexAccessNode (may be nested)
        self.value_node = value_node
        self.pos_start = target.pos_start
        self.pos_end = value_node.pos_end


class MethodCallNode:
    def __init__(self, object_node, method_name_tok, arg_nodes, pos_end=None):
        self.object_node = object_node
        self.method_name_tok = method_name_tok
        self.arg_nodes = arg_nodes
        self.pos_start = object_node.pos_start
        self.pos_end = pos_end or (
            arg_nodes[-1].pos_end if arg_nodes else method_name_tok.pos_end
        )


class ImportNode:
    def __init__(self, module_to_import, symbols, pos_start, pos_end=None):
        self.module_to_import = module_to_import
        self.pos_start = pos_start
        self.symbols = symbols
        self.pos_end = pos_end


class NaNNode:
    def __init__(self, pos_start, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end


class InfinityNode:
    def __init__(self, pos_start, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end


class BreakNode:
    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return "break"


class ContinueNode:
    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return "continue"


class PassNode:
    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return "pass"


class CatchNode:
    def __init__(
        self, pos_start, pos_end, body_node, exception=None, exception_var=None
    ):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.exception = exception
        self.exception_var = exception_var
        self.body_node = body_node

    def __repr__(self):
        if self.exception_var:
            return f"catch({self.exception} {self.exception_var}) {{{self.body_node}}}"
        return f"catch({self.exception}) {{{self.body_node}}}"


class TryCatchNode:
    def __init__(self, pos_start, pos_end, try_body, catch_nodes):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.try_body = try_body
        self.catch_nodes = catch_nodes  # list of CatchNode, at least one required

    def __repr__(self):
        catches = " ".join(str(c) for c in self.catch_nodes)
        return f"try {self.try_body} {catches}"


class StructDefNode:
    def __init__(self, name, member_nodes, pos_end):
        self.name = name
        self.member_nodes = member_nodes
        self.pos_start = name.pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"struct {self.name.value} {{ {self.member_nodes} }}"


class PropertyAssignNode:
    def __init__(self, target, property_name, value):
        self.target = target
        self.property_name = property_name
        self.value = value
        self.pos_start = target.pos_start
        self.pos_end = value.pos_end

    def __repr__(self):
        return f"{self.target}.{self.property_name} = {self.value}"
