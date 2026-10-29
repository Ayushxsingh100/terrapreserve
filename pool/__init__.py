"""D3: the TerraPreserve real-world pool builder. Standard library and sources/* only; never imports DAIL (D3-02)."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _sub in ("sources", "sources/terrads", "sources/terragoat"):
    _path = str(_ROOT / _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
