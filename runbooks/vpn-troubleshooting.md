# IPsec VPN Troubleshooting Runbook

IPsec on PAN-OS negotiates in two independent stages — **Phase 1 (IKE SA)**
and **Phase 2 (IPsec SA)** — governed by two separate crypto profiles. They
fail for different reasons and the fix is different depending on which one
is down. Conflating them is the single most common way VPN troubleshooting
goes in circles.

| | Phase 1 (IKE) | Phase 2 (IPsec) |
|---|---|---|
| Establishes | The management channel between peers | The actual tunnel that carries data |
| Governed by | IKE Crypto Profile | IPsec Crypto Profile |
| Common failure | Pre-shared key / certificate mismatch, IKE proposal mismatch, peer unreachable | ESP transform (encryption/auth) mismatch, proxy-ID / traffic selector mismatch |
| Check with | `show vpn ike-sa gateway <gateway>` | `show vpn ipsec-sa` |

Symptom overlap is real: both present as "tunnel is down" to an end user.
Always check Phase 1 and Phase 2 status **separately** before diagnosing
further — a Phase 1 SA that's up rules out an entire category of causes
(peer reachability, PSK, IKE proposal) and narrows the problem to Phase 2
transform or selector mismatch, or vice versa.

## Step 1: Establish which phase is actually failing

```
> show vpn ike-sa gateway <gateway-name>
> show vpn ipsec-sa
> show vpn flow name <tunnel-name>
```

- Phase 1 down, Phase 2 never attempted → peer reachability, PSK/cert, or
  IKE proposal problem. Continue at **Step 2**.
- Phase 1 up, Phase 2 down or flapping → transform or proxy-ID mismatch on
  the IPsec crypto profile or protected-subnet definitions. Continue at
  **Step 3**. This is the [INC-003](../incident-command-center/INC-003-ipsec-phase2-failure.md)
  pattern.
- Both up but no traffic passes → not a VPN negotiation problem at all —
  check NAT rule order (Step 4) and the security policy for the `vpn` zone.

## Step 2: Phase 1 (IKE) failure

```
Monitor > Logs > System, filter: subtype eq vpn
> debug ike stat
```

Check, in order:
1. **Reachability** — `ping` (via the correct source interface) to the
   peer's public gateway IP. If this fails, it's routing/firewall/ISP, not
   VPN configuration.
2. **IKE proposal match** — encryption, hash, DH group, and IKE version
   must match exactly on both peers. A single differing parameter causes a
   silent proposal rejection, not a helpful error.
3. **Pre-shared key or certificate** — confirm out of band with the peer
   administrator; a mismatched PSK fails without a specific log line on
   either side.

## Step 3: Phase 2 (IPsec) failure — transform or proxy-ID mismatch

```
Monitor > Logs > System, filter: subtype eq vpn AND ( eventid eq ike-nego-p2-fail )
> show vpn ipsec-sa tunnel <tunnel-name>
```

Look for `NO-PROPOSAL-CHOSEN` or `Quick Mode` failure notifications in the
system log — that specific message means Phase 1 succeeded (they can talk)
but the two sides couldn't agree on Phase 2 parameters.

Two distinct root causes produce the same symptom:

- **ESP transform mismatch** — the local IPsec Crypto Profile
  (encryption/authentication algorithms) doesn't match what the peer
  proposes. This is what happens when one side's crypto profile is changed
  as a hardening step (e.g. AES-128/SHA1 → AES-256/SHA256) without the peer
  making the same change in the same window. See
  [INC-003](../incident-command-center/INC-003-ipsec-phase2-failure.md) for
  the full writeup — the fix is coordinated cutover, not reverting the
  hardening.
- **Proxy-ID / traffic selector mismatch** — the local and remote
  "protected subnet" definitions on the two peers don't mirror each other.
  Common trigger: a new subnet is added on one side (see `New-Dept-Subnet`
  in [`policies/nat-policy-matrix.md`](../policies/nat-policy-matrix.md))
  and the tunnel's proxy-ID isn't updated to match, or isn't updated on
  the peer's device at the same time.

```
Network > IPSec Tunnels > <tunnel> > Proxy IDs
Confirm Local/Remote match exactly what the peer has configured — including
subnet mask, not just network address.
```

## Step 4: Both phases up, but traffic still doesn't pass

This is a NAT problem, not a VPN problem. VPN-destined traffic must hit a
**bypass NAT rule** (no translation) before any generic outbound SNAT rule,
or the packets get translated before the firewall recognizes them as tunnel
traffic — the tunnel negotiates fine but useful data never crosses it.

```
Policies > NAT
Order should be:
1. VPN-Bypass-NAT (no translation) — must be above any general SNAT rule
   for the same source zone
2. Internal-to-Internet-SNAT (translate)
3. [other rules]
```

See [`policies/nat-policy-matrix.md`](../policies/nat-policy-matrix.md) for
the exact rule this repo uses, and
[INC-001](../incident-command-center/INC-001-nat-rule-shadowing.md) for how
rule shadowing breaks this same mechanism for non-VPN traffic.

## Useful commands, by task

```
# Status
> show vpn ike-sa gateway <gateway-name>
> show vpn ipsec-sa
> show vpn flow name <tunnel-name>

# Force renegotiation (use during a coordinated change window, not blindly)
> clear vpn ike-sa gateway <gateway-name>
> clear vpn ipsec-sa tunnel <tunnel-name>

# Debug (short-lived, disable when done — verbose)
> debug ike on
> debug ike stat
> debug crypto on

# Session/traffic once tunnel is up
> show session all filter application ipsec
> show counter global filter delta yes
```

## Prevention

1. **Never change an IPsec crypto profile unilaterally.** Treat it as a
   two-party contract — schedule the change with the peer administrator in
   the same window, and consider temporarily accepting both the old and
   new proposal during cutover to avoid a hard outage.
2. **Any subnet change behind a tunnel is a proxy-ID change.** Add it to
   the [change review checklist](../policies/change-review-checklist.md)
   for that tunnel, on both ends, before the subnet goes live.
3. **Keep bypass-NAT above generic SNAT** for every zone pair that also
   carries tunnel traffic, and verify it after any NAT rule reordering.
4. **Enable VPN system logging and alert on tunnel-down**, not just on
   negotiation failure — a tunnel that silently drops after establishing is
   a different failure mode (DPD/keepalive tuning) than one that never
   comes up.
