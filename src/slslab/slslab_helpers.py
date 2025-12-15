import json
import re
from pathlib import Path
from typing import Any

_LIST_TOKEN = "__LIST__"


def _extract_lists(obj, store):
    if isinstance(obj, (list, tuple)):
        key = f"{_LIST_TOKEN}{len(store)}"
        store.append(json.dumps(obj, separators=(",", ": ")))
        return key
    elif isinstance(obj, dict):
        return {k: _extract_lists(v, store) for k, v in obj.items()}
    return obj


def save_instance_as_json(instance: Any, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    lists = []
    replaced = _extract_lists(instance, lists)

    text = json.dumps(
        replaced,
        indent=4,
        ensure_ascii=False,
    )

    for i, compact in enumerate(lists):
        text = re.sub(
            f"\"{_LIST_TOKEN}{i}\"",
            compact,
            text,
        )

    path.write_text(text, encoding="utf-8")

def save_instance_as_json_old(instance, path: Path):
    # Ensure the parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the instance as JSON
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            instance,
            f,
            ensure_ascii=False,
            indent=4,
        )

def unpack_str_tuple(str_tuple: str) -> tuple:
    x,y = map(int, str_tuple.strip("()").split(","))
    return (x,y)


def format_str_tuple(str_tuple: str) -> str:
    x,y = map(int, str_tuple.strip("()").split(","))
    return f"{x}_{y}"