"""Read the documented JSON tree format."""

from __future__ import annotations

import json
from pathlib import Path

from .model import Branch, Chance, Decision, Node, Terminal, evaluate


def _fields(payload: object, required: set[str], optional: set[str], path: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    missing = required - payload.keys()
    extra = payload.keys() - required - optional
    if missing:
        raise ValueError(f"{path} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{path} unknown fields: {', '.join(sorted(extra))}")


def _node(payload, path: str) -> Node:
    _fields(payload, {"type", "label"}, {"value", "branches"}, path)
    kind = payload["type"]
    if kind == "terminal":
        _fields(payload, {"type", "label", "value"}, set(), path)
        return Terminal(payload["label"], payload["value"])
    if kind not in ("decision", "chance"):
        raise ValueError(f"{path} type must be 'decision', 'chance', or 'terminal'")
    _fields(payload, {"type", "label", "branches"}, set(), path)
    if not isinstance(payload["branches"], list):
        raise ValueError(f"{path} branches must be a JSON array")

    branches = []
    for index, edge in enumerate(payload["branches"]):
        edge_path = f"{path}.branches[{index}]"
        required = {"child", "probability"} if kind == "chance" else {"child"}
        _fields(edge, required, {"label", "value"}, edge_path)
        branches.append(Branch(
            _node(edge["child"], f"{edge_path}.child"),
            probability=edge.get("probability"),
            value=edge.get("value", 0),
            label=edge.get("label", ""),
        ))
    return (Chance if kind == "chance" else Decision)(payload["label"], tuple(branches))


def load_json(path: str | Path) -> Node:
    """Read and validate a UTF-8 JSON file and return its root node."""
    with Path(path).open(encoding="utf-8") as source:
        root = _node(json.load(source), "root")
    evaluate(root)
    return root
