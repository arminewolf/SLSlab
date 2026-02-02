import json
import re
from pathlib import Path
from typing import Any

_LIST_TOKEN = "__LIST__"


def _extract_lists(obj, store):
    """
    Recursively traverse a Python object and replace every list or tuple
    with a unique placeholder string, while storing a compact JSON
    representation of each encountered list.

    This function performs a depth-first walk over dictionaries and
    sequences:

    - When a list or tuple is encountered, it is:
        1. Serialized immediately using `json.dumps` with compact
           separators (no indentation or line breaks).
        2. Appended to `store`, preserving encounter order.
        3. Replaced in the returned structure by a placeholder string
           of the form f"{_LIST_TOKEN}{index}", where `index` corresponds
           to its position in `store`.

    - When a dictionary is encountered, its values are processed
      recursively and a new dictionary with the same keys is returned.

    - All other values (numbers, strings, booleans, None, etc.) are
      returned unchanged.

    The placeholder index acts as the identity of the list: the N-th
    placeholder always refers to the N-th compact list stored in `store`.
    This positional contract is relied upon later to restore the lists
    after pretty-printing the surrounding JSON structure.

    Parameters
    ----------
    obj : Any
        The object (or sub-object) to process.
    store : list[str]
        A list used to collect compact JSON strings for each encountered
        list or tuple, in encounter order.

    Returns
    -------
    Any
        A copy of `obj` where all lists and tuples have been replaced
        by placeholder strings.
    """
    if isinstance(obj, (list, tuple)):
        key = f"{_LIST_TOKEN}{len(store)}"
        store.append(json.dumps(obj, separators=(",", ": ")))
        return key
    elif isinstance(obj, dict):
        return {k: _extract_lists(v, store) for k, v in obj.items()}
    return obj


def save_instance_as_json(instance: Any, path: Path):
    """
    Save an object to a JSON file while preserving a neat, human-readable
    structure: dictionaries are pretty-printed across multiple lines,
    while lists are kept compact on a single line.

    This function works around a limitation of Python's standard JSON
    encoder, which applies a single global formatting policy. With
    `indent` enabled, all lists are expanded vertically, even small ones.
    There is no built-in way to format dictionaries and lists differently
    in a single serialization pass.

    To achieve per-type formatting, the function performs a two-phase
    serialization:

    1. **Extraction phase**
       All lists and tuples are temporarily replaced by unique placeholder
       strings using `_extract_lists`. Each list is serialized separately
       into a compact, single-line JSON string and stored in encounter
       order.

       At this point, the JSON encoder only sees dictionaries and scalar
       values, so it can format the structure cleanly and predictably.

    2. **Pretty-print phase**
       The modified object (with placeholders instead of lists) is
       serialized using `json.dumps(indent=4)`, producing a neatly
       indented JSON structure.

    3. **Restoration phase**
       Each quoted placeholder string (e.g. "__LIST__0") in the resulting
       JSON text is replaced with its corresponding compact list string
       (e.g. "[1,2,3]") using positional indexing. Because this replacement
       happens *after* formatting, the surrounding indentation is
       preserved and lists remain inline.

    The key idea is that lists are treated as atomic values during
    formatting, rather than being formatted by the JSON encoder itself.
    This avoids vertical list expansion and results in a cleaner, more
    scannable JSON file.

    Parameters
    ----------
    instance : Any
        The object to serialize. It must be JSON-serializable.
    path : Path
        Destination path of the JSON file. Parent directories are created
        automatically if they do not exist.
    """
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