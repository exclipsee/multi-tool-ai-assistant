import json
from pathlib import Path
from typing import Any

def load_json(path: Path, default: Any = None):
    """Load JSON from `path` if the file exists, otherwise return `default` or {}."""
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def save_json(path: Path, data: Any):
    """Write JSON to `path`. Returns True on success, False on error."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False
