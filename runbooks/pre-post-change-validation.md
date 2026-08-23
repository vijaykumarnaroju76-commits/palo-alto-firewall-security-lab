# Pre/Post-Change Validation Runbook

The mechanics behind the "before commit" and "after commit" items in
[`policies/change-review-checklist.md`](../policies/change-review-checklist.md).
The goal is a change record that proves the fix worked — not just that the
commit succeeded — and a rollback path that doesn't have to be improvised
during an outage.

## Baseline capture (before commit)

Run and save the output of each of these, scoped to the rules/objects the
change touches:

```
# Rule hit counts — so you can tell post-change whether traffic is hitting
# the rule you intended, an unintended neighbor, or nothing at all
> show rule-hit-count rule-base security vsys vsys1
> show rule-hit-count rule-base nat vsys vsys1

# Session baseline — total and filtered to the affected source/destination
> show session info
> show session all filter destination <ip>

# Routing baseline — relevant for any change touching zones, interfaces,
# or redundant paths
> show routing route
> test routing fib-lookup virtual-router <vr> ip <dest-ip>

# VPN baseline, if the change touches a tunnel
> show vpn ike-sa gateway <gateway-name>
> show vpn ipsec-sa

# Config snapshot — always, regardless of change size
> save config to pre-change-<ticket-id>.xml
```

Paste the relevant subset into the change ticket. "I checked it before"
without saved output is not verifiable during a postmortem.

## Making the change

- Stage the change in the candidate config, review the diff
  (`Config Audit` in the GUI, or `show config diff` on CLI) before
  committing — don't eyeball the rule list alone.
- Commit with a description that names the ticket/incident ID, not a
  generic "policy update".
- For anything touching NAT order, VPN, or default/DMZ security rules,
  have a second engineer review the diff before commit (per the checklist).

## Post-change validation

```
# Targeted functional test first — the specific traffic the change exists
# to enable/restrict
> test security-policy-match from <zone> to <zone> source <ip> destination <ip> application <app> protocol <p> destination-port <port>
> test nat-policy-match from <zone> to <zone> source <ip> destination <ip> protocol <p> destination-port <port>

# Confirm the intended rule is the one actually taking hits, not a neighbor
> show rule-hit-count rule-base security vsys vsys1
> show rule-hit-count rule-base nat vsys vsys1
# — diff against the pre-change capture; only the intended rule's counter
#   should have moved

# Traffic/threat log review, filtered to the affected source/destination,
# for at least the first 10-15 minutes after commit
Monitor > Logs > Traffic
Monitor > Logs > Threat

# VPN-specific: confirm BOTH phases, not just tunnel interface status
> show vpn ike-sa gateway <gateway-name>
> show vpn ipsec-sa

# Routing/NAT-specific: confirm return traffic uses the same zone/interface
# it egressed through
> show session all filter destination <ip>
```

A change is "validated," not just "committed," once you can point to
evidence the intended traffic now behaves as expected **and** nothing else
regressed (spot-check one or two adjacent rules' hit counts didn't change
unexpectedly).

## Rollback procedure

Decide this before commit, not after something breaks:

```
# Fastest path — revert to the saved pre-change snapshot
> load config from pre-change-<ticket-id>.xml
> commit

# Or, for a single rule/object change, revert just that change in the
# candidate config and re-commit rather than a full config load
```

- Rollback is not an admission of failure — treat "roll back, investigate
  offline, retry in the next window" as a first-class valid outcome for
  any change that doesn't validate cleanly.
- If a change is rolled back, the ticket still gets the post-change
  evidence section filled in (what failed, what the logs showed) — that's
  what turns a rollback into a usable incident record instead of a dead
  end.

## Cross-references

- What to check before requesting the change window:
  [`policies/change-review-checklist.md`](../policies/change-review-checklist.md)
- Diagnostic commands for narrowing down *why* something didn't validate:
  [`packet-flow-troubleshooting.md`](packet-flow-troubleshooting.md)
