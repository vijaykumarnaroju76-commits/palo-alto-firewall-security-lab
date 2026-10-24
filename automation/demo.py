#!/usr/bin/env python3
"""Inject failures into copies of synthetic records without changing evidence files."""
import copy
import json
from pathlib import Path

from validate_incidents import validate


def main():
    directory = Path(__file__).resolve().parents[1] / "evidence/validation"
    paths = sorted(directory.glob("inc-*-validation.json"))
    if len(paths) != 6:
        print("Expected the six bundled incident records")
        return 1
    correct = True
    print("SYNTHETIC OFFLINE DEMO: no firewall connections or configuration changes")
    for path in paths:
        original = json.loads(path.read_text())
        broken = copy.deepcopy(original)
        if "checks" in broken:
            broken["checks"][0]["result"] = "fail"
            # Intentionally leave overall_result=pass to detect contradiction.
        else:
            broken["post_fix"]["application_reachability"] = "fail"
        for label, record, expected in [("baseline", original, True),
                                        ("injected failure", broken, False),
                                        ("recovery", original, True)]:
            errors, recovered = validate(record)
            passed = not errors and recovered
            correct &= passed == expected
            print(f"{original['incident_id']} {label}: {'PASS' if passed else 'FAIL'} "
                  f"(expected {'PASS' if expected else 'FAIL'})")
    return 0 if correct else 1


if __name__ == "__main__":
    raise SystemExit(main())
