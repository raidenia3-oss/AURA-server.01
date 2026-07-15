"""Load automation targets from targets.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

_TARGETS_FILE = Path(__file__).resolve().parent / "targets.json"


def load_targets() -> List[dict]:
    """Return the list of configured automation targets."""
    if not _TARGETS_FILE.exists():
        return []
    try:
        with open(_TARGETS_FILE, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.values())
    return []
