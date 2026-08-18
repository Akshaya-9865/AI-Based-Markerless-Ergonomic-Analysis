import os
import json
from typing import Dict, Any
from datetime import datetime

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def write_json(path: str, data: Dict[str, Any]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
