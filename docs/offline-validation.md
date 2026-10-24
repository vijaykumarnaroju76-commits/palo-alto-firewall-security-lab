# Offline incident validation

Run from the repository root with Python 3.9 or newer. No packages, credentials,
network connections, or firewall licenses are required for these checks.

```bash
python3 automation/validate_incidents.py
python3 automation/demo.py
python3 -m unittest discover -s tests -v
```

## What the commands do

- The validator reads the six JSON records in `evidence/validation/` and writes
  `output/incident-report.md`. Exit 0 means records are valid and all declared
  recovery checks pass. Exit 1 means malformed evidence or unverified recovery.
- The demo copies each record in memory, injects a failed check, and verifies that
  validation rejects it. It then rechecks the original record as recovery.
  It never changes the evidence files. `FAIL (expected FAIL)` means detection
  worked. The demo exits 0 only when all 18 outcomes match expectations.
- The regression suite checks invalid input, inconsistent summaries, empty checks,
  duplicate check names, missing fields, failed recovery, and CLI behavior.

## Supported evidence formats

INC-001 through INC-004 use a nonempty `checks` array with named commands,
expectations, and pass/fail results. `overall_result` must agree with those results.
`synthetic_data` must be true.

INC-005 and INC-006 use nonempty `pre_fix` and `post_fix` objects containing named
pass/fail results. Pre-fix failures are legitimate incident evidence. Recovery is
verified only when every recorded post-fix result passes. These records must carry
`evidence_type: modeled_synthetic_validation`, a scenario, root cause, scope note,
and boolean rollback field. The two stages may use different check names, as in
the existing HA record.

Both formats require an incident ID matching the filename. Unknown results and
ambiguous mixed formats are rejected. Extra metadata fields are permitted.

## Limits

This validates the structure and consistency of declared results. It does not
execute the recorded commands, parse PAN-OS output, compare `observed` values to
free-text expectations, prove a root cause, or verify real recovery. A structurally
valid record can still contain an incorrect human assertion. The demo is an
evidence-validation exercise, not a firewall or packet-flow simulator.

The validator is intended for this repository's synthetic examples. Do not relabel
real captures synthetic to make them pass. Live evidence needs a separate provenance
and validation workflow. Use the existing setup guide and incident runbooks when
running an actual lab, then capture sanitized before/after outputs and independent
application tests.

To inspect another directory of synthetic records:

```bash
python3 automation/validate_incidents.py --input-dir /path/to/records --report /path/to/report.md
```
