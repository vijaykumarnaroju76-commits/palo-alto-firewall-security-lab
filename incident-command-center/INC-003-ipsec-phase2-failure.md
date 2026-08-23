# INC-003 — IPsec Phase 2 Failure After Crypto Hardening Change

| | |
|---|---|
| **Severity** | Sev-1 (site-to-site VPN to partner fully down, business traffic blocked) |
| **Systems** | IPsec VPN tunnel to partner site, IPsec Crypto Profile |
| **Duration** | ~25 minutes to root cause, ~2 hours to coordinated fix (partner-dependent) |
| **Status** | Resolved |

## Impact

The site-to-site IPsec tunnel to the partner network (172.16.50.0/24) went
down immediately following a scheduled security-hardening change and did
not recover on its own. All traffic depending on the tunnel was blocked
for the duration.

## Symptom

- Tunnel interface (`tunnel.1`) showed administratively up, but no traffic
  passed in either direction.
- `Monitor > VPN > IPSec Tunnels` showed the tunnel state as down.
- System logs showed repeated negotiation attempts, all failing.
- The change that preceded the outage was a planned update to the local
  IPsec Crypto Profile — upgrading ESP encryption/authentication from
  AES-128/SHA1 to AES-256/SHA256 as part of a compliance-driven hardening
  pass, applied only to this firewall.

## Hypotheses considered

1. ~~Peer gateway unreachable~~ — ruled out immediately; `ping` to the
   partner's public gateway IP succeeded, and Phase 1 negotiation attempts
   were visible in the logs (meaning the peers could talk).
2. ~~Pre-shared key or IKE proposal broken by the change~~ — ruled out;
   the hardening change only touched the IPsec (Phase 2) crypto profile,
   not the IKE (Phase 1) crypto profile, and Phase 1 SA was confirmed up.
3. **ESP transform mismatch introduced by the one-sided hardening change**
   — pursued once Phase 1 was confirmed healthy, since that isolates the
   problem to Phase 2 negotiation specifically.

## Investigation

```
> show vpn ike-sa gateway <partner-gateway>
```
Phase 1 SA: **up**. This immediately ruled out peer reachability, PSK, and
IKE proposal mismatch — the two sides can authenticate and negotiate a
management channel just fine.

```
> show vpn ipsec-sa
```
Phase 2 SA: **not established**.

```
Monitor > Logs > System, filter: subtype eq vpn AND eventid eq ike-nego-p2-fail
```
Repeated `Received Notify: NO-PROPOSAL-CHOSEN during Quick Mode` entries —
the specific signature of a Phase 2 transform mismatch, distinct from a
Phase 1 failure, and distinct from a proxy-ID mismatch (which fails
differently, after a proposal is agreed, on traffic selector matching).

Cross-checked the local IPsec Crypto Profile against the change record:
confirmed it had been updated from `aes-128-cbc` / `sha1` to
`aes-256-cbc` / `sha256` earlier the same day. Contacted the partner's
network team to confirm their side — their IPsec crypto profile still
proposed `aes-128-cbc` / `sha1`, unchanged. The two sides no longer had any
overlapping ESP proposal, so Quick Mode had nothing to agree on.

## Evidence

- Sanitized system log excerpt showing Phase 1 up / Phase 2
  `NO-PROPOSAL-CHOSEN`:
  [`evidence/sanitized-traffic-logs/inc-003-ike-log.log`](../evidence/sanitized-traffic-logs/inc-003-ike-log.log)
- Structured validation record:
  [`evidence/validation/inc-003-validation.json`](../evidence/validation/inc-003-validation.json)

## Root cause

**A one-sided IPsec crypto-hardening change.** The local IPsec Crypto
Profile's ESP encryption/authentication algorithms were upgraded without
coordinating the same change with the partner's network team in the same
window. Phase 1 (governed by a separate, unchanged IKE crypto profile)
continued to succeed, which is why the tunnel looked "almost up" rather
than obviously broken — a purely Phase-1-based check would have missed
this entirely.

This was a **process gap, not a technical misconfiguration** — the new
crypto profile itself was correct and was in fact the more secure choice;
it simply wasn't deployed in coordination with the peer that also needed
to change.

## Fix

- Reverting the hardening change was considered and **rejected** — it
  would restore connectivity but abandon a legitimate, already-approved
  security improvement, and would need to be redone later anyway.
- Instead: scheduled a short joint change window with the partner's
  network team. During the window, the local IPsec Crypto Profile was
  temporarily set to accept **both** the new (`aes-256-cbc`/`sha256`) and
  legacy (`aes-128-cbc`/`sha1`) proposals, giving the partner room to cut
  over without a hard synchronization requirement. The partner updated
  their profile to `aes-256-cbc`/`sha256` during the same window.
- Once the partner confirmed their change, the legacy proposal was removed
  from the local profile, leaving only `aes-256-cbc`/`sha256` on both
  ends.

```
Network > IPSec Crypto > <profile>
ESP Encryption: aes-256-cbc  (temporarily: aes-256-cbc, aes-128-cbc)
ESP Authentication: sha256   (temporarily: sha256, sha1)
```

## Validation

```
> show vpn ike-sa gateway <partner-gateway>
> show vpn ipsec-sa
```
Both Phase 1 and Phase 2 SA up. Encrypt/decrypt packet counters
incrementing on `show vpn flow name <tunnel-name>`.

Functional test: sustained ping and application traffic across the tunnel
to a partner-side test host, confirmed stable for 30 minutes post-cutover.
No further `NO-PROPOSAL-CHOSEN` entries in the system log after the
partner's change landed.

## Prevention

- Added a dual-ended coordination requirement to
  [`policies/change-review-checklist.md`](../policies/change-review-checklist.md):
  any IPsec crypto profile or proxy-ID change must be scheduled in the
  same window as the peer administrator's matching change — no
  unilateral crypto profile edits on a live tunnel.
- Documented the "accept both old and new proposals during cutover"
  pattern in
  [`runbooks/vpn-troubleshooting.md`](../runbooks/vpn-troubleshooting.md)
  as the standard approach for future crypto migrations, so the next
  hardening pass doesn't require rediscovering it under outage pressure.
- Noted for future audits: Phase 1 being up is **not** sufficient evidence
  a tunnel is healthy — both phases must be checked independently, every
  time.
