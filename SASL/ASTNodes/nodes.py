class NumberNode:
    def __init__(self, token):
        self.token = token
        self.pos_start = token.pos_start
        self.pos_end = token.pos_end

    def __repr__(self):
        return f"{self.token}"


class BinaryOpNode:
    def __init__(self, left_node, op_token, right_node):
        self.left_node = left_node
        self.op_token = op_token
        self.right_node = right_node
        self.pos_start = left_node.pos_start
        self.pos_end = right_node.pos_end

    def __repr__(self):
        return f"({self.left_node} : {self.op_token} : {self.right_node})"


class BinaryNegationNode:
    def __init__(self, op_token, node):
        self.op_token = op_token
        self.node = node
        self.pos_start = op_token.pos_start
        self.pos_end = node.pos_end

    def __repr__(self):
        return f"{self.op_token} : {self.node}"


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
        return f"{kind} {self.name.value}{type_str} = {self.value_node}"


class MultiVariableAssignNode:
    def __init__(self, names: list, value=None, is_const=False, type_define=False):
        self.names = names
        self.value = value
        self.is_const = "const" if is_const == True else "var"
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
