import json
from pathlib import Path
from typing import Any

def load_json(path: Path, default: Any = None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def save_json(path: Path, data: Any):
    try:
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False
