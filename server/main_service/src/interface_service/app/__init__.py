from __future__ import annotations

import sys
from pathlib import Path

_SERVER_DIR = str(Path(__file__).resolve().parents[4])
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)
