# INC-002 — Security Policy Deny / App-ID Reclassification

| | |
|---|---|
| **Severity** | Sev-2 (internal integration degraded, majority of calls failing) |
| **Systems** | Trust → DMZ security policy, App-ID |
| **Duration** | ~1 hour to root cause, fix same change window |
| **Status** | Resolved |

## Impact

The internal inventory application's integration with the DMZ-hosted
`Inventory-API-Server` (10.0.2.30, custom protocol on tcp/8443) began
failing for most requests within minutes of the API service being
deployed. A minority of connection attempts succeeded; most were reset
mid-connection.

## Symptom

- Application team reported "some calls work, most get reset."
- No pattern by source host or time of day — looked random from the
  application side.
- The security rule intended to permit this traffic
  (`Allow-Trust-to-Inventory-API`) had been committed and, per its rule
  hit counter, **was** taking hits — so the traffic wasn't being blocked
  outright by a missing rule.

## Hypotheses considered

1. ~~Wrong zone mapping~~ — checked first since it's the most common
   integration-day mistake. Ruled out: both trust and dmz zone
   assignments on the relevant interfaces were correct, and the rule's
   `from`/`to` zones matched.
2. ~~Backend service instability~~ — ruled out with the app team; the API
   process itself showed no restarts or errors during the failure window,
   and successful requests returned normal responses.
3. ~~Session timeout / idle timeout too aggressive~~ — considered because
   of the "mid-connection reset" pattern, but reset timing didn't
   correlate with any configured timeout value.
4. **App-ID classifying the traffic differently than the rule expects** —
   pursued after noticing the rule was written against application `ssl`
   (the team's assumption, since the traffic runs on tcp/8443), and
   traffic logs showed the application field for many sessions
   was **not** `ssl`.

## Investigation

```
Monitor > Logs > Traffic, filter: ( addr.dst in 10.0.2.30 )
```
Traffic log showed two distinct patterns for sessions to the same
destination and port:
- Sessions logged with `Application = ssl`, `Action = allow` — the
  minority that "worked."
- Sessions logged with `Application = unknown-tcp`, `Action = deny`,
  `Rule = Deny-Unknown-Apps` — the majority that reset.

Both patterns hit the same destination, same port, same source subnet.
The differentiator was App-ID's classification, not anything network-level.

```
> show session id <session-id>
```
On a session pulled mid-failure, the session detail showed the
application field had **changed** between session start and the point of
the reset — consistent with PAN-OS's documented behavior of issuing a
provisional App-ID on early packets and refining it as Content-ID
inspects more of the payload, then re-checking the session against
security policy when the classification changes (see
[`runbooks/packet-flow-troubleshooting.md`](../runbooks/packet-flow-troubleshooting.md)
for why this is expected architecture, not a bug).

Root cause of the *reclassification*: the internal API protocol
negotiates a TLS-like handshake on 8443 (which is why some early packets
provisionally classify as `ssl`), but the actual application payload
after the handshake isn't standard TLS — it's a proprietary framing the
app team built. App-ID has no signature for it, so once enough payload is
inspected, it settles on `unknown-tcp`. `Allow-Trust-to-Inventory-API` at
the time only permitted `ssl`, so any session that got reclassified away
from `ssl` fell through to `Deny-Unknown-Apps`.

## Evidence

- Sanitized traffic log showing the two application-classification
  patterns:
  [`evidence/sanitized-traffic-logs/inc-002-traffic-log.log`](../evidence/sanitized-traffic-logs/inc-002-traffic-log.log)
- Structured validation record:
  [`evidence/validation/inc-002-validation.json`](../evidence/validation/inc-002-validation.json)

## Root cause

**Security rule scoped to an assumed App-ID (`ssl`) that did not match
App-ID's actual, final classification (`unknown-tcp`) of the internal
API's non-standard protocol.** App-ID reclassifying mid-session triggered
a policy re-evaluation that most sessions failed, because the rule never
accounted for the traffic being anything other than the port-based
assumption the app team started with.

## Fix

Two options were weighed:

- **(Rejected)** Add `unknown-tcp` broadly to `Deny-Unknown-Apps`'s
  exception list or to an existing broad allow rule. Rejected because it
  would permit *any* unclassified traffic on that path, not just this
  API — an unacceptable widening of the attack surface for a narrow
  integration need.
- **(Chosen)** Register a custom App-ID application (`inventory-api`)
  matching the protocol's actual signature, and scope
  `Allow-Trust-to-Inventory-API` to that custom app explicitly instead of
  `ssl`.

```
Objects > Applications > Add
Name: inventory-api
Category: business-systems
Signature: [context: appid, pattern matching the protocol's post-handshake frame header]

Policies > Security > Allow-Trust-to-Inventory-API
Application: inventory-api   (replacing: ssl)
```

Committed with a description referencing this incident ID.

## Validation

```
Monitor > Logs > Traffic, filter: ( addr.dst in 10.0.2.30 )
```
All sessions now classify as `inventory-api`, `Action = allow`,
`Session End Reason = tcp-fin` (clean close) instead of a mix of
`ssl`/`unknown-tcp` with resets.

```
> show rule-hit-count rule-base security vsys vsys1
```
`Allow-Trust-to-Inventory-API` hit count increments for 100% of traffic to
10.0.2.30 over a 30-minute soak; `Deny-Unknown-Apps` no longer takes hits
for that destination.

Application team confirmed zero failed calls over the following hour of
production traffic.

## Prevention

- Added an App-ID verification step to
  [`policies/change-review-checklist.md`](../policies/change-review-checklist.md):
  any non-standard-port or custom-protocol integration must have its
  App-ID classification confirmed (dry-run session or test traffic) before
  the security rule is written — not assumed from the port number.
- Documented `inventory-api` as a registered custom application in
  [`policies/security-policy-matrix.md`](../policies/security-policy-matrix.md)
  so future rules referencing this service use the same signature instead
  of re-guessing.
- Kept `Deny-Unknown-Apps` as an explicit, logged rule (rather than
  letting unknown traffic fall into the generic default-deny) specifically
  because it made this incident's cause visible in the traffic log instead
  of an undifferentiated drop.
