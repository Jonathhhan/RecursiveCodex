#!/usr/bin/env python3
"""Generate a deterministic, bounded possibility hyperspace from declared dimensions."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


def _dimensions(spec: dict) -> list[dict]:
    dimensions = spec.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("dimensions must be a non-empty list")
    seen: set[str] = set()
    for dimension in dimensions:
        name = dimension.get("id")
        options = dimension.get("options")
        if not isinstance(name, str) or not name or name in seen:
            raise ValueError("dimension ids must be unique non-empty strings")
        if not isinstance(options, list) or not options:
            raise ValueError(f"dimension {name!r} must declare options")
        option_ids = [option.get("id") for option in options]
        if any(not isinstance(item, str) or not item for item in option_ids):
            raise ValueError(f"dimension {name!r} has an invalid option id")
        if len(set(option_ids)) != len(option_ids):
            raise ValueError(f"dimension {name!r} has duplicate option ids")
        seen.add(name)
    return dimensions


def _rule_parts(exclusion: dict) -> tuple[dict[str, str], dict[str, str]]:
    if "when" not in exclusion and "unless" not in exclusion:
        return exclusion, {}
    if set(exclusion) != {"when", "unless"}:
        raise ValueError("conditional exclusions must contain only 'when' and 'unless'")
    when = exclusion["when"]
    unless = exclusion["unless"]
    if not isinstance(when, dict) or not when:
        raise ValueError("conditional exclusion 'when' must be a non-empty mapping")
    if not isinstance(unless, dict) or not unless:
        raise ValueError("conditional exclusion 'unless' must be a non-empty mapping")
    return when, unless


def _exclusions(spec: dict, dimensions: list[dict]) -> list[dict]:
    exclusions = spec.get("exclusions", [])
    if not isinstance(exclusions, list):
        raise ValueError("exclusions must be a list")
    available = {
        dimension["id"]: {option["id"] for option in dimension["options"]}
        for dimension in dimensions
    }
    for exclusion in exclusions:
        if not isinstance(exclusion, dict) or not exclusion:
            raise ValueError("each exclusion must be a non-empty mapping")
        when, unless = _rule_parts(exclusion)
        for dimension_id, option_id in {**when, **unless}.items():
            if dimension_id not in available:
                raise ValueError(f"exclusion references unknown dimension {dimension_id!r}")
            if option_id not in available[dimension_id]:
                raise ValueError(
                    f"exclusion references unknown option {option_id!r} "
                    f"for dimension {dimension_id!r}"
                )
    return exclusions


def _is_excluded(choices: dict[str, str], exclusions: list[dict]) -> bool:
    for exclusion in exclusions:
        when, unless = _rule_parts(exclusion)
        referenced = set(when) | set(unless)
        if not referenced.issubset(choices):
            continue
        when_matches = all(choices[key] == value for key, value in when.items())
        unless_matches = bool(unless) and all(
            choices[key] == value for key, value in unless.items()
        )
        if when_matches and not unless_matches:
            return True
    return False


def _state(choices: dict[str, str], score: float) -> dict:
    signature = "|".join(f"{key}={choices[key]}" for key in choices)
    return {"id": signature or "origin", "choices": choices, "score": score}


def generate(spec: dict, strategy: str = "frontier", max_nodes: int = 64) -> dict:
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    dimensions = _dimensions(spec)
    exclusions = _exclusions(spec, dimensions)
    if strategy not in {"frontier", "exhaustive"}:
        raise ValueError("strategy must be 'frontier' or 'exhaustive'")

    total = 1
    for dimension in dimensions:
        total *= len(dimension["options"])
    if strategy == "exhaustive" and total > max_nodes:
        raise ValueError(f"complete space requires {total} nodes; budget is {max_nodes}")

    frontier = [_state({}, 0.0)]
    iterations = []
    for index, dimension in enumerate(dimensions, start=1):
        candidates = []
        for parent in frontier:
            for option in dimension["options"]:
                choices = dict(parent["choices"])
                choices[dimension["id"]] = option["id"]
                candidates.append(_state(choices, parent["score"] + float(option.get("score", 0))))
        generated = len(candidates)
        candidates = [node for node in candidates if not _is_excluded(node["choices"], exclusions)]
        candidates.sort(key=lambda node: (-node["score"], node["id"]))
        frontier = candidates if strategy == "exhaustive" else candidates[:max_nodes]
        iterations.append({
            "iteration": index,
            "dimension": dimension["id"],
            "generated": generated,
            "excluded": generated - len(candidates),
            "retained": len(frontier),
            "states": frontier,
        })

    return {
        "schema_version": 1,
        "strategy": strategy,
        "dimensions": [dimension["id"] for dimension in dimensions],
        "theoretical_size": total,
        "exclusions": exclusions,
        "budget": max_nodes,
        "iterations": iterations,
        "possibilities": frontier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--strategy", choices=("frontier", "exhaustive"), default="frontier")
    parser.add_argument("--max-nodes", type=int, default=64)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = generate(json.loads(args.spec.read_text(encoding="utf-8")), args.strategy, args.max_nodes)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
