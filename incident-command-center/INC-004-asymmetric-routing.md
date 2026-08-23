# INC-004 — Asymmetric Routing / Session Drop After Redundant ISP Rollout

| | |
|---|---|
| **Severity** | Sev-2 (intermittent outbound failures to one partner API, subset of sessions) |
| **Systems** | Routing (dual ISP egress), NAT, stateful session table |
| **Duration** | ~1.5 hours to root cause (intermittent symptom slowed triage), fix same day |
| **Status** | Resolved |

## Impact

Shortly after a second ISP (`untrust2`, 198.51.100.0/28) was added for
outbound redundancy, internal hosts began experiencing **intermittent**
connection failures to one specific external partner API. Most traffic was
unaffected; the failures were sporadic and didn't correlate with load or
time of day, which made this look at first like a flaky external
dependency rather than an internal routing change.

## Symptom

- Application team reported connection timeouts to the partner API,
  roughly 1 in 4 attempts, no consistent pattern by source host.
- No corresponding errors from the partner side when asked to check their
  logs — from their perspective, some connections simply never completed
  the handshake.
- Symptom onset correlated in time with the redundant-ISP change, but the
  change had already been running successfully for general internet
  traffic for several days before this surfaced, which delayed the
  connection to that change.

## Hypotheses considered

1. ~~Partner API instability~~ — the first and most natural assumption
   given "intermittent, no pattern." Weakened once the partner confirmed
   no server-side errors or restarts during the failure windows.
2. ~~Security policy intermittently blocking~~ — checked because
   intermittent deny-then-allow behavior sometimes indicates a policy
   ordering or App-ID reclassification issue (compare
   [INC-002](INC-002-security-policy-deny.md)). Ruled out: traffic logs
   showed **no deny entries at all** for the failing attempts — they
   simply never completed, which points earlier in the flow than policy
   evaluation.
3. **Asymmetric routing after the dual-ISP change** — pursued once "no
   deny logged, but no response either" suggested packets were being
   silently dropped at a stage before policy logging, which for a
   stateful firewall usually means session-state mismatch, not a rule
   decision.

## Investigation

```
> show counter global filter delta yes severity drop
```
A non-zero and climbing counter for asymmetric-path session drops,
correlating in time with the failure reports — PAN-OS's stateful
inspection rejects packets that arrive on a different zone/interface than
the one the matching session was established on, by design, as a security
control against session hijacking and spoofing.

```
> show routing route
```
Confirmed both `untrust` (203.0.113.0/28, ISP-A) and `untrust2`
(198.51.100.0/28, ISP-B) were installed as equal-preference default
routes — the redundant-ISP change had added a second default route without
any mechanism to keep a given flow's outbound and return path on the same
interface.

```
> show session all filter destination <partner-api-ip>
```
On a session captured mid-failure: outbound (client-to-server) packets
showed egress via `untrust` (ISP-A), source-translated by
`Internal-to-Internet-SNAT` to the ISP-A public address. A packet capture
on `untrust2` during the same window showed return traffic for that same
flow's source/destination pair arriving on **ISP-B** instead — because the
partner's own upstream routing didn't always send return traffic back over
the same path the request had (a routing symmetry assumption that no
longer held once two independent egress paths existed). The firewall
correctly identified this as not matching any known session on that
interface and dropped it.

## Evidence

- Sanitized session-table before/after comparison:
  [`evidence/session-analysis/inc-004-session-table-before-after.md`](../evidence/session-analysis/inc-004-session-table-before-after.md)
- Structured validation record:
  [`evidence/validation/inc-004-validation.json`](../evidence/validation/inc-004-validation.json)

## Root cause

**The redundant-ISP rollout introduced equal-cost dual egress paths without
any mechanism to keep a flow's SNAT translation and its return path
aligned to the same ISP.** Some flows egressing via ISP-A had their return
traffic arrive via ISP-B (a function of the partner's own routing, outside
this network's control), and PAN-OS's stateful session tracking correctly
rejected that traffic as not matching the session it was established
under. This is the firewall's asymmetric-path protection working as
designed — the actual defect was architectural: adding a second egress
path without pinning flows to a deterministic, symmetric path.

**Explicitly not the fix considered:** disabling the asymmetric-path
protection (`Zone Protection > session setup > reject non-syn-tcp` /
asymmetric-path handling) to "let it through." That control exists to
prevent a real class of session-spoofing attack; turning it off to paper
over a self-inflicted routing symmetry problem would trade a known,
narrow outage for an open-ended security gap. The fix had to be routing,
not tolerance.

## Fix

Implemented Policy-Based Forwarding (PBF) so that once a flow's egress
interface is chosen, its SNAT translation is pinned to match — guaranteeing
a given flow's outbound path is deterministic instead of subject to
ECMP/route-preference tie-breaking, and giving the partner's return
routing a single, consistent public source IP to route back to per path:

```
Network > Policy-Based Forwarding > Add
Name: Pin-Egress-Path
Source Zone: trust
Destination: <partner-api-subnet>
Egress Interface: ethernet0/4 (untrust / ISP-A)
Enforce Symmetric Return: yes
```

Paired with the existing `Internal-to-Internet-SNAT` rule (already scoped
to ISP-A's public address) so the chosen egress interface and the SNAT
pool always agree for this destination.

## Validation

```
> show session all filter destination <partner-api-ip>
```
All sessions to the partner API now show consistent ingress/egress
interface (`untrust`/ISP-A) for both directions.

Packet capture on `untrust2` confirmed no further traffic for this
destination pair arrives on the secondary ISP.

```
> show counter global filter delta yes severity drop
```
Asymmetric-path drop counter returned to baseline (zero delta) over a
2-hour soak test with continuous synthetic requests to the partner API —
zero failures, compared to the ~25% failure rate observed during the
incident.

## Prevention

- Added a routing-symmetry check to
  [`policies/change-review-checklist.md`](../policies/change-review-checklist.md):
  any change introducing a new egress path (second ISP, new static route,
  ECMP) must be paired with an explicit plan for symmetric return —
  PBF and/or SNAT-pool alignment — before being considered complete, not
  retrofitted after the first affected destination surfaces.
- Documented this incident as the canonical reference for why the
  asymmetric-path drop counter is a security control, not a bug to work
  around — future engineers hitting this counter should read this incident
  before considering disabling the protection.
- Noted that "intermittent, no correlation with load" combined with "no
  deny logged" is a useful triage signal pointing at session-state/routing
  layers rather than policy — captured in
  [`runbooks/packet-flow-troubleshooting.md`](../runbooks/packet-flow-troubleshooting.md).
