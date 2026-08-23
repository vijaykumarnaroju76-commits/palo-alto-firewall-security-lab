# NAT Policy Matrix

NAT rules are evaluated **top-to-bottom, first match wins** — exactly like
security policy, but it is easy to forget because NAT rules are usually
written and reviewed in isolation from the security rule base. Rule order
here is not cosmetic; it is the actual cause of
[INC-001](../incident-command-center/INC-001-nat-rule-shadowing.md).

## Current rule base (post INC-001 fix)

| # | Name | From → To | Source | Destination | Service | Translation | Notes |
|---|------|-----------|--------|-------------|---------|-------------|-------|
| 1 | `VPN-Bypass-NAT` | trust → vpn | Internal-Subnet, New-Dept-Subnet | Partner-Remote-Subnet | any | None (no translation) | Must stay above every generic outbound NAT rule or VPN traffic gets translated before the security engine ever considers it a tunnel candidate |
| 2 | `Internet-to-WebServer-DNAT` | untrust → dmz | any | Public-IP-WebServer (203.0.113.50/32) | tcp/80, tcp/443 | Destination → 10.0.2.10 | Narrowed from the old `Public-IP-Pool` object after INC-001 |
| 3 | `Internet-to-NewApp-DNAT` | untrust → dmz | any | Public-IP-NewApp (203.0.113.51/32) | tcp/443 | Destination → 10.0.2.20 | The rule that was silently shadowed pre-fix; now matches because its destination object no longer overlaps rule 2 |
| 4 | `Internal-to-Internet-SNAT` | trust → untrust | Internal-Subnet | any | any | Source → dynamic-ip-and-port, 203.0.113.10 | Primary ISP egress |
| 5 | `Internal-to-Internet-SNAT-ISP2` | trust → untrust2 | Internal-Subnet | any | any | Source → dynamic-ip-and-port, 198.51.100.10 | Secondary ISP egress added for redundancy; see [INC-004](../incident-command-center/INC-004-asymmetric-routing.md) for why this rule alone isn't sufficient for symmetric return traffic |

## Rule base as it existed during INC-001 (for reference — do not restore)

| # | Name | Destination object | Problem |
|---|------|--------------------|---------|
| 2 | `Internet-to-WebServer-DNAT` | `Public-IP-Pool` = 203.0.113.0/24 | Matched **any** address in the /24, including the new app's IP, because it was both broader and higher in the list than rule 3 |
| 3 | `Internet-to-NewApp-DNAT` | `Public-IP-NewApp` = 203.0.113.51/32 | Correct and specific, but unreachable — rule 2 always matched first |

This is kept here deliberately as a "what shadowing looks like" reference —
see the checklist item in
[`change-review-checklist.md`](change-review-checklist.md) that exists
specifically to catch this pattern before it ships again.

## Verifying NAT rule order and hits

```
> show running nat-policy-flow
> show nat-rule-base
> show rule-hit-count rule-base nat vsys vsys1
```

A newly added, more-specific rule with a hit count stuck at `0` while an
older, broader rule's counter keeps climbing for the same destination is the
signature of shadowing — check that first before assuming the rule is
misconfigured.

## Rule-ordering principles enforced here

1. **Specific before general.** Bypass and single-host rules go above
   subnet- or pool-scoped rules.
2. **No overlapping destination objects across DNAT rules** for different
   published services. If two objects can both match the same public IP,
   only the higher rule will ever fire.
3. **VPN bypass NAT is always rule #1** for any zone pair that also carries
   tunnel traffic — see
   [`runbooks/vpn-troubleshooting.md`](../runbooks/vpn-troubleshooting.md).
