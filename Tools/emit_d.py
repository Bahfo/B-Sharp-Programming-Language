import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from B_Sharp.frontend import parse_source
from B_Sharp.Backend.emitter import DLanguageEmitter, DBackendError

src_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/bsharp_dlab/gen_app.d"
with open(src_path, encoding="utf-8-sig") as f:
    src = f.read()
res = parse_source(src_path, src)
if res.has_error:
    print(res.error)
    sys.exit(1)
try:
    dcode = DLanguageEmitter().emit(res.ast_root)
except DBackendError as e:
    print(f"BACKEND-ERROR: {e}")
    sys.exit(2)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(dcode)
print(f"wrote {out_path}")
print("--- generated D ---")
print(dcode)
