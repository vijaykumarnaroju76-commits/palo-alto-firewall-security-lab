#!/usr/bin/env python3
"""Verify relative markdown links resolve to real files.

Scans every .md file in the repo for markdown links `[text](target)`.
External links (http/https/mailto) are skipped — this only checks that
relative links between files in this repo actually point somewhere,
without depending on flaky network calls in CI.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def is_external(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "#"))


def resolve(md_file: Path, target: str) -> Path:
    # Strip any in-page anchor (path#section) before resolving the file part.
    path_part = target.split("#", 1)[0]
    if not path_part:
        return md_file  # pure anchor within the same file
    return (md_file.parent / path_part).resolve()


def main() -> int:
    failures = []
    for md_file in sorted(REPO_ROOT.rglob("*.md")):
        if ".git" in md_file.parts:
            continue
        text = md_file.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if not target or is_external(target):
                continue
            resolved = resolve(md_file, target)
            if not resolved.exists():
                failures.append(
                    f"{md_file.relative_to(REPO_ROOT)}: broken link -> {target}"
                )

    if failures:
        print(f"Found {len(failures)} broken internal link(s):\n")
        for f in failures:
            print(f"  {f}")
        return 1

    print("All internal markdown links resolve correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
