from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


def _yaml_scalar(value: str) -> str:
    """Return a JSON string, which is also a valid YAML scalar."""
    return json.dumps(value, ensure_ascii=False)


def _replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"template invariant failed: expected one occurrence of {old!r}, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a Recursive Codex project contract.")
    parser.add_argument("project_root")
    parser.add_argument("--domain", default="neutral")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    plugin_root = Path(__file__).resolve().parents[1]
    root = Path(args.project_root).resolve()
    contract_dir = root / ".recursive-codex"
    contract = contract_dir / "project.yaml"
    if contract.exists() and not args.force:
        raise SystemExit(f"project contract already exists: {contract}")

    domain_source = plugin_root / "domains" / f"{args.domain}.yaml"
    if not domain_source.is_file():
        available = ", ".join(path.stem for path in sorted((plugin_root / "domains").glob("*.yaml")))
        raise SystemExit(f"unknown domain {args.domain!r}; available: {available}")

    template = (plugin_root / "templates" / "project.yaml").read_text(encoding="utf-8")
    domain_text = domain_source.read_text(encoding="utf-8")
    authority_match = re.search(r"(?m)^\s+default:\s*([^#\r\n]+)", domain_text)
    if not authority_match:
        raise SystemExit(f"domain profile has no authority.default: {domain_source}")
    authority = authority_match.group(1).strip().strip('"\'')

    text = _replace_once(template, "project: example-project", f"project: {_yaml_scalar(root.name)}")
    text = _replace_once(text, "domain: neutral", f"domain: {_yaml_scalar(args.domain)}")
    text = _replace_once(
        text,
        "final_decision: project-owner",
        f"final_decision: {_yaml_scalar(authority)}",
    )

    contract_dir.mkdir(parents=True, exist_ok=True)
    (contract_dir / "events").mkdir(exist_ok=True)
    (contract_dir / "decisions").mkdir(exist_ok=True)
    contract.write_text(text, encoding="utf-8")
    shutil.copyfile(domain_source, contract_dir / "domain.yaml")
    print(f"INITIALIZED {contract_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
