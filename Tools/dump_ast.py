import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from B_Sharp.frontend import parse_source
from B_Sharp.Backend.emitter import DLanguageEmitter, DBackendError


def dump(node, indent=0):
    pad = "  " * indent
    if node is None:
        print(f"{pad}None")
        return

    if isinstance(node, list):
        print(f"{pad}list[{len(node)}]:")
        for x in node:
            dump(x, indent + 1)

        return

    t = type(node).__name__
    if hasattr(node, "value") and isinstance(getattr(node, "value"), str):
        print(f"{pad}{t} value={node.value!r}")
        return
    print(f"{pad}{t}")

    for k in (
        "statement_nodes",
        "list_of_expressions",
        "tuple_of_expressions",
        "arg_nodes",
        "body_node",
        "node_to_call",
        "value",
        "node",
    ):
        if hasattr(node, k):
            v = getattr(node, k)
            print(f"{pad} .{k}:")
            dump(v, indent + 1)

    if hasattr(node, "token"):
        tok = node.token
        print(f"{pad}  token type={tok.type} value={getattr(tok,'value',None)!r}")
    if t == "CallNode" and hasattr(node, "node_to_call"):
        pass


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bsharp_dlab/hello.bsharp"
    with open(path, encoding="utf-8-sig") as f:
        src = f.read()
    res = parse_source(path, src)
    if res.has_error:
        print(res.error)
        sys.exit(1)
    print(f"root: {type(res.ast_root).__name__}")
    print(f"repr: {res.ast_root!r}")
    print("--- tree ---")
    dump(res.ast_root)

    try:
        dcode = DLanguageEmitter().emit(res.ast_root)
    except DBackendError as e:
        print(f"BACKEND-ERROR: {e}")
        sys.exit(2)
    out_path = os.path.join(REPO_ROOT, "codegen.d")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(dcode)
    print(f"--- wrote {out_path} ---")
    print(dcode)
