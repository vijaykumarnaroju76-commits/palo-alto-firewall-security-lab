#!/usr/bin/env python3
"""Validate synthetic incident records, not live PAN-OS behavior."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(record):
    """Return (record errors, recovery result). Never infer missing checks passed."""
    errors = []
    if not isinstance(record, dict):
        return ["record must be an object"], False
    if not isinstance(record.get("incident_id"), str) or not re.fullmatch(r"INC-\d{3}", record["incident_id"]):
        errors.append("incident_id must match INC-001 format")
    checklist = "checks" in record
    staged = "pre_fix" in record or "post_fix" in record
    if checklist == staged:
        return errors + ["choose exactly one format: checks or pre_fix/post_fix"], False
    if checklist:
        if record.get("synthetic_data") is not True:
            errors.append("synthetic_data must be true for these example records")
        if not nonempty(record.get("title")):
            errors.append("title is required")
        checks = record["checks"]
        if not isinstance(checks, list) or not checks:
            return errors + ["checks must be a nonempty list"], False
        names, results = set(), []
        for i, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append(f"check {i}: must be an object")
                continue
            for field in ("name", "command", "expected"):
                if not nonempty(check.get(field)):
                    errors.append(f"check {i}: {field} is required")
            name = check.get("name")
            if isinstance(name, str):
                if name in names:
                    errors.append(f"check {i}: duplicate name")
                names.add(name)
            result = check.get("result")
            if result not in ("pass", "fail"):
                errors.append(f"check {i}: result must be pass or fail")
            results.append(result)
        recovered = len(results) == len(checks) and all(r == "pass" for r in results)
        expected = "pass" if recovered else "fail"
        if record.get("overall_result") != expected:
            errors.append(f"overall_result must be {expected}")
    else:
        if record.get("evidence_type") != "modeled_synthetic_validation":
            errors.append("evidence_type must identify modeled synthetic validation")
        for field in ("scenario", "root_cause", "scope_note"):
            if not nonempty(record.get(field)):
                errors.append(f"{field} is required")
        if type(record.get("rollback_required")) is not bool:
            errors.append("rollback_required must be boolean")
        for stage in ("pre_fix", "post_fix"):
            checks = record.get(stage)
            if not isinstance(checks, dict) or not checks:
                errors.append(f"{stage} must be a nonempty object")
                continue
            if any(not nonempty(k) or v not in ("pass", "fail") for k, v in checks.items()):
                errors.append(f"{stage}: named checks must be pass or fail")
        post = record.get("post_fix")
        recovered = isinstance(post, dict) and bool(post) and all(v == "pass" for v in post.values())
    return errors, recovered and not errors


def audit(directory):
    rows = []
    files = sorted(directory.glob("inc-*-validation.json"))
    if not files:
        return [("INPUT", ["no incident records found"], False)]
    seen = set()
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors, recovered = validate(record)
            incident = record.get("incident_id") if isinstance(record, dict) else None
            expected_id = path.name.removesuffix("-validation.json").upper()
            if incident != expected_id:
                errors.append("incident_id does not match filename")
            if isinstance(incident, str):
                if incident in seen:
                    errors.append("duplicate incident_id")
                seen.add(incident)
            rows.append((path.name, errors, recovered and not errors))
        except (OSError, ValueError) as exc:
            rows.append((path.name, [f"cannot read JSON: {exc}"], False))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "evidence/validation")
    parser.add_argument("--report", type=Path, default=ROOT / "output/incident-report.md")
    args = parser.parse_args()
    rows = audit(args.input_dir)
    lines = ["# Incident evidence validation", "",
             "SYNTHETIC records only. This checks structure and declared results; it does not test a firewall.", "",
             "| Record | Structure | Recorded recovery |", "| --- | --- | --- |"]
    passed = True
    for name, errors, recovered in rows:
        passed &= not errors and recovered
        status = "INVALID" if errors else "VALID"
        recovery = "PASS" if recovered else "NOT VERIFIED"
        lines.append(f"| {name} | {status} | {recovery} |")
        print(f"{name}: {status}; recovery {recovery}")
        for error in errors:
            print(f"  {error}")
    lines += ["", f"Overall: {'PASS' if passed else 'FAIL'}", ""]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
