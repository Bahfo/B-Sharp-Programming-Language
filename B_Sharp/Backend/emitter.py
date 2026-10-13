class DBackendError(Exception):
    pass


def escape_d_string(s: str) -> str:
    out = s.replace("\\", "\\\\")
    out = out.replace('"', '\\"')
    out = out.replace("\n", "\\n")
    out = out.replace("\t", "\\t")
    out = out.replace("\r", "\\r")
    return f'"{out}"'


class DLanguageEmitter:
    """
    Base emitter from B-Sharp to the D Programming Language.
    """

    def emit(self, root) -> str:
        if type(root).__name__ != "StatementsNode":
            raise DBackendError(f"Unsupported {type(root).__name__}")

        body = self.visit_StatementsNode(root)
        return f"import std.stdio; \nvoid main()\n{{\n{body}}}\n"

    def visit(self, node) -> str:
        name = f"visit_{type(node).__name__}"

        fn = getattr(self, name, None)
        if fn is None:
            raise DBackendError(f"Unsupported {type(node).__name__}")
        return fn(node)

    def visit_StatementsNode(self, node) -> str:
        lines = ""
        for stmt in node.statement_nodes:
            lines += self.visit(stmt)

        return lines

    def visit_CallNode(self, node) -> str:
        callee = node.node_to_call.name.value

        if callee != "__writeln":
            raise DBackendError(f"unsupported call {callee}")

        if len(node.arg_nodes) != 1:
            raise DBackendError("Function '__writeln' requires one argument.")

        arg = node.arg_nodes[0]

        if type(arg).__name__ != "StringNode":
            raise DBackendError(f"unsupported arg {type(arg).__name__}")

        dstr = self.visit_StringNode(arg)
        return f"    writeln({dstr});\n"

    def visit_StringNode(self, node) -> str:
        return escape_d_string(node.token.value)
