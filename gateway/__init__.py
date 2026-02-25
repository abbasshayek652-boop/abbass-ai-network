from __future__ import annotations

import importlib.util
import pathlib

_root_path = pathlib.Path(__file__).resolve().parent.parent / "gateway.py"
_spec = importlib.util.spec_from_file_location("_gateway_root", _root_path)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)  # type: ignore[arg-type]
for name in dir(_module):
    if name.startswith("_"):
        continue
    globals()[name] = getattr(_module, name)
