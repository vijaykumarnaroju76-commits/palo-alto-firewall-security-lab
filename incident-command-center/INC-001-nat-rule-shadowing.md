# INC-001 — NAT Rule Shadowing / Incorrect NAT Precedence

| | |
|---|---|
| **Severity** | Sev-2 (new service unreachable, no existing service impacted) |
| **Systems** | DMZ web tier, NAT policy |
| **Duration** | ~40 minutes from report to fix, +30 min monitoring |
| **Status** | Resolved |

## Impact

A newly published internal application (`NewApp-Server`, 10.0.2.20) was
unreachable from the internet on its dedicated public IP immediately after
go-live. Every connection to the new app's public IP instead landed on the
**legacy web server** — users saw the old site's content, and the app team
initially reported it as "wrong page returned," not "site down," which
shaped the early hypotheses.

## Symptom

- External requests to `https://203.0.113.51` (the new app's public IP)
  returned content from the legacy web server (10.0.2.10) instead of the
  new app (10.0.2.20).
- No errors in the new app's own logs — because no traffic was ever
  reaching it.
- The DNAT rule for the new app (`Internet-to-NewApp-DNAT`) had been
  committed successfully with no config warnings.

## Hypotheses considered

1. ~~DNS pointing to the wrong IP~~ — ruled out; `dig` confirmed the public
   DNS record resolved to 203.0.113.51 as expected.
2. ~~New app server itself misconfigured / wrong vhost~~ — ruled out; a
   direct test from inside the DMZ to 10.0.2.20 returned the correct
   content.
3. ~~Security policy denying the new app's traffic~~ — ruled out early;
   traffic logs showed sessions being **allowed**, just against the wrong
   destination.
4. **NAT rule not matching as expected** — pursued next, based on the
   "traffic reaches *a* server, just the wrong one" pattern, which points
   at translation, not routing or DNS.

## Investigation

```
> show session all filter destination 203.0.113.51
```
Sessions showed a NAT translation to `10.0.2.10` (the legacy server) for
traffic destined to `203.0.113.51` — the new app's IP was being translated
to the *old* server's internal address. That narrowed the problem to NAT
rule matching, not DNS or security policy.

```
> show rule-hit-count rule-base nat vsys vsys1
```
- `Internet-to-WebServer-DNAT` (rule 2, pre-fix): hit count climbing,
  including for the new app's destination IP.
- `Internet-to-NewApp-DNAT` (rule 3, pre-fix): hit count **stuck at 0**
  since the rule was created.

That is the signature of shadowing: a specific rule with zero hits while a
broader rule above it absorbs its traffic.

```
> show nat-rule-base
```
Confirmed the destination object on `Internet-to-WebServer-DNAT` was
`Public-IP-Pool`, defined as `203.0.113.0/24` — a legacy object originally
scoped broadly "for future public IPs," not the single host it was
actually protecting. `203.0.113.51` falls inside that /24, so the rule
matched it, and being higher in the rule list, it won.

## Evidence

- Sanitized rule-hit-count and NAT rule-base excerpts:
  [`evidence/sanitized-traffic-logs/inc-001-traffic-log.log`](../evidence/sanitized-traffic-logs/inc-001-traffic-log.log)
- Structured validation record:
  [`evidence/validation/inc-001-validation.json`](../evidence/validation/inc-001-validation.json)

## Root cause

**NAT rule shadowing caused by an overly broad, reused address object.**
`Internet-to-WebServer-DNAT` used a `/24` destination object
(`Public-IP-Pool`) instead of the single host it actually needed, and sat
above `Internet-to-NewApp-DNAT` in the rule list. Because NAT policy matching is
first-match, top-to-bottom, the broad rule always matched before the
specific one had a chance to. This was not a bug in the new rule — it was
a pre-existing latent risk in the old rule that only surfaced once a new
public IP was added inside its range.

## Fix

1. Narrowed the legacy rule's destination object from `Public-IP-Pool`
   (203.0.113.0/24) to `Public-IP-WebServer` (203.0.113.50/32) — the
   single host it was ever meant to cover.
2. Left `Internet-to-NewApp-DNAT` using its already-correct
   `Public-IP-NewApp` (203.0.113.51/32) object.
3. Confirmed no other rule referenced `Public-IP-Pool` before removing the
   object entirely (`Objects > Addresses`, unused-object check).
4. Committed with a description referencing this incident ID.

See [`policies/nat-policy-matrix.md`](../policies/nat-policy-matrix.md)
for the corrected rule base.

## Validation

```
> show session all filter destination 203.0.113.51
```
Translation now resolves to `10.0.2.20` (the new app) as expected.

```
> show rule-hit-count rule-base nat vsys vsys1
```
`Internet-to-NewApp-DNAT` hit count now incrementing;
`Internet-to-WebServer-DNAT` hit count no longer increments for the new
app's destination IP.

External functional test against `https://203.0.113.51` returned the new
app's content. Legacy site on `https://203.0.113.50` re-verified unaffected
by the narrowing.

## Prevention

- Added a rule-order and object-scope check to
  [`policies/change-review-checklist.md`](../policies/change-review-checklist.md):
  no new DNAT rule ships without confirming its destination object doesn't
  overlap an existing rule positioned above it.
- Flagged `/24`-or-broader address objects used in single-host DNAT rules
  as a standing cleanup item — "for future use" scoping on a NAT object is
  a latent shadowing risk, not a convenience.
- Post-change validation now explicitly checks rule-hit-count deltas on
  the intended rule *and* its neighbors, not just "does it work" — this is
  what would have caught a shadowing issue even without a functional
  symptom (see [`pre-post-change-validation.md`](../runbooks/pre-post-change-validation.md)).
