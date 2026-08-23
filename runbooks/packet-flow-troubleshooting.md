# PAN-OS Packet Flow Troubleshooting

This is the methodology behind the Incident Command Center flow in the
[top-level README](../README.md). Every incident in this repository is an
instance of walking this sequence and finding which stage disagreed with
what the operator expected.

## The single-pass flow, in troubleshooting order

PAN-OS evaluates a new session in this order. Knowing the order matters
because a symptom at the "traffic is blocked" layer can have its actual
cause several stages earlier or later than where you'd naturally start
looking.

```
1. Ingress (zone/interface)
2. Session lookup       — existing session? if yes, fast-path, skip to 8
3. Zone protection / DoS checks
4. NAT policy lookup     — determines destination NAT (if any) BEFORE routing
5. Route lookup          — uses the POST-NAT destination for DNAT'd traffic
6. Security policy lookup — zones + address objects + App-ID (initial guess) + User-ID
7. Source NAT applied, session installed
8. Content-ID / App-ID refinement as more packets arrive
   → App-ID can RECLASSIFY mid-session; if it does, policy is re-evaluated
9. Forwarding / egress
```

The two stages that most often surprise people coming from other
firewall platforms:

- **NAT is evaluated before routing**, so a DNAT rule changes what the route
  lookup even sees. If you're chasing a routing symptom, check whether NAT
  quietly redirected the destination first.
- **App-ID is not final at step 6.** The first few packets get a
  provisional classification (often based on port), and the policy match
  at step 6 uses that. As Content-ID inspects more of the flow, App-ID can
  change its answer — and PAN-OS re-checks the session against policy when
  it does. A session that was allowed on packet 1 can be denied on packet
  40 if the real application turns out to be something the rule doesn't
  permit. This is exactly what happened in
  [INC-002](../incident-command-center/INC-002-security-policy-deny.md).

## Where to look, mapped to the flow

| Stage | Command | What you're checking |
|-------|---------|----------------------|
| Session lookup | `show session all filter destination <ip> source <ip>` | Does a session exist? What zone/interface is it pinned to? |
| Session detail | `show session id <id>` | App-ID (`c2s`/`s2c` application), NAT translation applied, ingress/egress interface |
| NAT match (dry run) | `test nat-policy-match from <zone> to <zone> source <ip> destination <ip> protocol <p> destination-port <port>` | Which NAT rule *would* match, before you commit anything |
| Route lookup | `test routing fib-lookup virtual-router <vr> ip <dest-ip>` | Which interface/next-hop this destination resolves to right now |
| Security policy match (dry run) | `test security-policy-match from <zone> to <zone> source <ip> destination <ip> application <app> protocol <p> destination-port <port>` | Which security rule matches for a given (possibly hypothetical) App-ID |
| Rule hit counters | `show rule-hit-count rule-base security vsys vsys1`, `... rule-base nat ...` | Is traffic hitting the rule you think it is, or a neighbor above/below it? |
| Drop counters | `show counter global filter delta yes severity drop` | Aggregate drop reasons (session setup fail, policy deny, zone protection, asymmetric path, etc.) — good first stop when you don't yet know which stage to blame |
| Live packet flow | `debug dataplane packet-diag set filter` + `debug dataplane packet-diag set capture` | Ground truth: what the ASIC/dataplane actually did with a specific flow |

## A general triage sequence

1. **Reproduce and capture the 5-tuple** (source IP/port, destination
   IP/port, protocol) of a failing flow from the user report or app logs.
2. **Traffic log first**: `Monitor > Logs > Traffic` filtered to that
   5-tuple. The `Session End Reason` and `Action` columns usually narrow
   the problem to one or two stages immediately (`policy-deny` → step 6;
   `aged-out`/`tcp-rst-from-server` → look past the firewall; no log entry
   at all → check zone protection / DoS / interface-level drops before
   assuming policy).
3. **Session lookup** — if the session exists, inspect it directly
   (`show session id`) rather than guessing from logs.
4. **Dry-run the policy stages** (`test nat-policy-match`,
   `test security-policy-match`, `test routing fib-lookup`) with the same
   5-tuple to see what *should* happen, and compare to what the traffic
   log says *did* happen. A mismatch between the two is the finding.
5. **Only reach for packet capture / `debug flow basic`** once the dry-run
   tests don't explain the symptom — it's the highest-fidelity tool but
   also the slowest to read.
6. **Check counters, not just one session** — `show counter global` and
   the rule-hit-count tables tell you whether this is one flow's bad luck
   or a systemic pattern (which changes the fix from "adjust one rule" to
   "reorder the rule base" or "add PBF").

## Cross-references

- NAT-specific ordering issues → [`policies/nat-policy-matrix.md`](../policies/nat-policy-matrix.md)
- Security policy / App-ID rule layout → [`policies/security-policy-matrix.md`](../policies/security-policy-matrix.md)
- VPN-specific flow (Phase 1 vs Phase 2) → [`runbooks/vpn-troubleshooting.md`](vpn-troubleshooting.md)
- Routing symmetry and stateful session tracking → [INC-004](../incident-command-center/INC-004-asymmetric-routing.md)
