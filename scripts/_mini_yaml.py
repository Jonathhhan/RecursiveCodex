"""Dependency-free parser for the conservative YAML subset used by this plugin."""

from __future__ import annotations

import json
from pathlib import Path


def load(path: str | Path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    lines = [
        (len(raw) - len(raw.lstrip(" ")), raw.strip())
        for raw in text.splitlines()
        if raw.strip() and not raw.lstrip().startswith("#")
    ]
    if not lines:
        return {}
    value, index = _block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError(f"could not parse line {index + 1}: {lines[index][1]}")
    return value


def _block(lines, index: int, indent: int):
    is_list = lines[index][1].startswith("- ")
    result = [] if is_list else {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"unexpected indentation: {content}")
        if is_list:
            if not content.startswith("- "):
                break
            item_text = content[2:].strip()
            index += 1
            if not item_text:
                if index >= len(lines) or lines[index][0] <= indent:
                    result.append(None)
                else:
                    item, index = _block(lines, index, lines[index][0])
                    result.append(item)
            elif ":" in item_text:
                key, raw_value = item_text.split(":", 1)
                item = {key.strip(): _scalar(raw_value.strip()) if raw_value.strip() else None}
                if index < len(lines) and lines[index][0] > indent:
                    continuation, index = _block(lines, index, lines[index][0])
                    if not isinstance(continuation, dict):
                        raise ValueError(f"mapping continuation expected after: {item_text}")
                    item.update(continuation)
                result.append(item)
            else:
                result.append(_scalar(item_text))
        else:
            if content.startswith("- ") or ":" not in content:
                break
            key, raw_value = content.split(":", 1)
            key = key.strip()
            value_text = raw_value.strip()
            index += 1
            if value_text:
                result[key] = _scalar(value_text)
            elif index < len(lines) and lines[index][0] > indent:
                result[key], index = _block(lines, index, lines[index][0])
            else:
                result[key] = None
    return result, index


def _scalar(value: str):
    if value in {"null", "~"}:
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") or value.startswith("{"):
        return json.loads(value)
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value
