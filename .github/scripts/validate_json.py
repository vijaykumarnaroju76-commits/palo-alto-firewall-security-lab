#!/usr/bin/env python3
"""Validate every .json file in the repo parses as well-formed JSON."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures = []
    json_files = sorted(REPO_ROOT.rglob("*.json"))
    for f in json_files:
        if ".git" in f.parts:
            continue
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{f.relative_to(REPO_ROOT)}: {exc}")

    if failures:
        print(f"Found {len(failures)} invalid JSON file(s):\n")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"All {len(json_files)} JSON file(s) are well-formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
