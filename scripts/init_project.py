from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


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

    contract_dir.mkdir(parents=True, exist_ok=True)
    (contract_dir / "events").mkdir(exist_ok=True)
    (contract_dir / "decisions").mkdir(exist_ok=True)
    shutil.copyfile(plugin_root / "templates" / "project.yaml", contract)
    text = contract.read_text(encoding="utf-8")
    text = text.replace("project: example-project", f"project: {root.name}")
    text = text.replace("domain: neutral", f"domain: {args.domain}")
    domain_text = domain_source.read_text(encoding="utf-8")
    authority_match = re.search(r"(?m)^\s+default:\s*([^#\r\n]+)", domain_text)
    if authority_match:
        text = text.replace("final_decision: project-owner", f"final_decision: {authority_match.group(1).strip()}")
    contract.write_text(text, encoding="utf-8")
    shutil.copyfile(domain_source, contract_dir / "domain.yaml")
    print(f"INITIALIZED {contract_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
