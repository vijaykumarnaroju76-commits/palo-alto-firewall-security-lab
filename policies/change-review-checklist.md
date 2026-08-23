# Firewall Change Review Checklist

Every incident in this repository traces back to a change that shipped
without one of these checks. The checklist exists to make that class of
mistake structurally harder to make, not to slow changes down for their own
sake — most items take under two minutes.

Use [`pre-post-change-validation.md`](../runbooks/pre-post-change-validation.md)
for the baseline-capture and rollback mechanics referenced below.

## Before requesting a change window

- [ ] **State the intended traffic in one sentence**: source, destination,
      application, and direction. If you can't, the rule you're about to
      write is too broad.
- [ ] **Object scope check** — does the address/service object you're about
      to use already exist and is it scoped to exactly what you need, or is
      it a shared "pool" object other rules also depend on? Reusing a broad
      object is how [INC-001](../incident-command-center/INC-001-nat-rule-shadowing.md)
      happened.
- [ ] **App-ID reality check** — if the traffic is anything other than
      standard HTTP/HTTPS/DNS, confirm with the application owner what
      App-ID actually classifies it as (`show session id <id>` on a test
      session, or `test security-policy-match` and `test nat-policy-match`
      dry-runs), not what port it happens to run on. Don't write a rule
      against an assumed application — see
      [INC-002](../incident-command-center/INC-002-security-policy-deny.md).
- [ ] **VPN dual-ended coordination** — any change to an IPsec crypto
      profile, proxy-ID, or protected subnet must be scheduled with the
      peer administrator in the same change window. A one-sided change is
      the root cause of [INC-003](../incident-command-center/INC-003-ipsec-phase2-failure.md).
- [ ] **Routing symmetry check** — does this change add a new egress path
      (second ISP, new static route, ECMP, ACI/SDN peering)? If yes, confirm
      how return traffic gets back through the *same* interface it left
      through, and pair it with NAT/PBF as needed. See
      [INC-004](../incident-command-center/INC-004-asymmetric-routing.md).
      Do not disable asymmetric-path protection to work around this —
      that protection is a stateful security control, not a bug.

## Immediately before commit

- [ ] Capture baseline: rule hit counts, session count, relevant route
      table entries (`pre-post-change-validation.md` → Baseline Capture).
- [ ] Rule order review — for both the security and NAT rule bases, confirm
      the new/changed rule sits where a more specific rule is above any
      broader rule it could otherwise be shadowed by.
- [ ] Peer review by a second engineer for anything touching NAT order,
      VPN crypto/proxy-ID, or default/DMZ security rules.
- [ ] Rollback plan written down before commit, not improvised after
      (see `pre-post-change-validation.md` → Rollback Procedure).

## Immediately after commit

- [ ] Targeted functional test of the exact traffic the change was meant
      to enable (not just "commit succeeded").
- [ ] Traffic/threat log review filtered to the affected source/destination
      for the first 10–15 minutes.
- [ ] Rule hit counters incrementing on the *intended* rule, not a
      neighboring one.
- [ ] For VPN changes: confirm Phase 1 **and** Phase 2 SA are both up
      (`show vpn ike-sa gateway <gw>`, `show vpn ipsec-sa`), not just tunnel
      interface status.
- [ ] For routing/NAT changes: packet capture or session table check
      confirming the return path uses the same zone/interface as egress.

## Sign-off

- [ ] Change ticket updated with: what changed, baseline evidence, post-change
      evidence, and rollback step (even if unused).
- [ ] If this change class caused a past incident, cross-link the incident
      ID in the ticket so the pattern is traceable.
