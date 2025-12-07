from pathlib import Path
import json

def save_instance_as_json(instance, path: Path):
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


def format_str_tuple(str_tuple: str) -> tuple:
    x,y = map(int, str_tuple.strip("()").split(","))
    return f"{x}_{y}"