# Palo Alto Firewall — Incident Response & Security Operations Lab

A Palo Alto Networks VM-Series lab built around a different question than
"can I configure a firewall": **when something breaks in production, how do
you find out why, prove the fix worked, and stop it from happening again?**

This is not an architecture showcase. There's no diagram of racks and zones
up front — that's one paragraph in [Lab Environment](#lab-environment)
below. The rest of the repository is organized around **incidents**: real
operational failure patterns on a Palo Alto firewall, each one investigated
from symptom to root cause to validated fix.

## Incident Command Center

Every incident here follows the same diagnostic path — because on a
PAN-OS firewall, that path *is* the architecture. NAT is evaluated before
routing. Security policy depends on an App-ID classification that can
change mid-session. A tunnel that's "up" might only be half up. Walking
this sequence in order is what actually finds the root cause, not
guessing from the symptom.

```
        SYMPTOM
   "Application unreachable / degraded"
              │
              ▼
     ┌─────────────────┐
     │   Traffic Logs   │  Monitor > Logs > Traffic — allow/deny, session end reason
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │  Session Lookup  │  show session all / show session id — does a session exist?
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │   Route Lookup   │  test routing fib-lookup — where does this destination resolve?
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │    NAT Policy    │  show rule-hit-count (nat) — which rule matched, in what order?
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │ Security Policy  │  App-ID classification, zone match, rule-hit-count (security)
     │    + App-ID      │
     └────────┬─────────┘
              ▼
     ┌─────────────────┐
     │  VPN / IPsec     │  show vpn ike-sa / show vpn ipsec-sa — Phase 1 vs Phase 2
     └────────┬─────────┘
              ▼
        ROOT CAUSE
              │
              ▼
     FIX  →  VALIDATE  →  DOCUMENT  →  PREVENT
```

Full methodology behind this diagram:
[`runbooks/packet-flow-troubleshooting.md`](runbooks/packet-flow-troubleshooting.md).

## Incident index

Each incident follows the same structure:
**Impact → Symptom → Hypotheses → Investigation → Evidence → Root Cause →
Fix → Validation → Prevention** — including the hypotheses that turned out
to be wrong, because ruling things out is most of the actual work.

| ID | Incident | Stage of the flow it lives in | Root cause category |
|----|----------|-------------------------------|----------------------|
| [INC-001](incident-command-center/INC-001-nat-rule-shadowing.md) | NAT rule shadowing / incorrect NAT precedence | NAT Policy | Overly broad address object shadowing a specific rule |
| [INC-002](incident-command-center/INC-002-security-policy-deny.md) | Security policy deny / App-ID reclassification | Security Policy + App-ID | Rule scoped to an assumed App-ID that didn't match App-ID's actual classification |
| [INC-003](incident-command-center/INC-003-ipsec-phase2-failure.md) | IPsec Phase 2 failure after crypto hardening | VPN / IPsec | One-sided crypto profile change, uncoordinated with the peer |
| [INC-004](incident-command-center/INC-004-asymmetric-routing.md) | Asymmetric routing / session drop after redundant ISP rollout | Route Lookup + stateful session tracking | New egress path added without pinning symmetric return traffic |

More incidents get added here only when they exercise a genuinely different
failure mode — the goal is four to seven incidents worth reading closely,
not a long list of shallow ones.

## Repository structure

```
palo-alto-firewall-security-lab/
├── README.md
├── incident-command-center/     Full incident writeups (the core of this repo)
├── policies/                    Security & NAT rule-base reference, change checklist
├── runbooks/                    Packet-flow methodology, VPN troubleshooting,
│                                 pre/post-change validation
├── evidence/                    Sanitized logs, session analysis, structured
│                                 validation records the incidents cite
├── docs/                        Lab environment setup guide
└── .github/workflows/           CI: markdown lint, internal link check, JSON/YAML validation
```

- **[`policies/security-policy-matrix.md`](policies/security-policy-matrix.md)**
  and **[`policies/nat-policy-matrix.md`](policies/nat-policy-matrix.md)** —
  the actual rule base referenced throughout the incidents, including the
  "before" state that caused INC-001, kept as a reference for what
  shadowing looks like.
- **[`policies/change-review-checklist.md`](policies/change-review-checklist.md)**
  — the checklist that exists because every incident here traces back to a
  change that skipped one of its items.
- **[`runbooks/`](runbooks/)** — the reusable diagnostic procedures:
  packet-flow triage, IPsec Phase 1/Phase 2 troubleshooting, and
  pre/post-change validation mechanics.
- **[`evidence/`](evidence/)** — sanitized traffic logs, session-table
  comparisons, and structured validation JSON per incident. All synthetic;
  see [`evidence/README.md`](evidence/README.md) for the IP-addressing
  convention that keeps it that way verifiably (RFC 1918 / RFC 5737
  documentation ranges only).

## Lab environment

**Firewall:** Palo Alto Networks VM-Series, deployed on VMware/KVM.
**Zones:** `trust` (10.0.1.0/24 internal), `dmz` (10.0.2.0/24 published
services), `untrust` + `untrust2` (dual ISP egress, see INC-004), plus a
site-to-site IPsec tunnel to a partner network. Full deployment steps in
[`docs/setup-guide.md`](docs/setup-guide.md). The zone/subnet/object
definitions actually used by the policies and incidents in this repo are
tracked in [`policies/security-policy-matrix.md`](policies/security-policy-matrix.md),
not restated here, so there's one source of truth instead of two documents
drifting apart.

## Status

This is an active, in-progress portfolio project — incidents and runbooks
are added as they're written and validated, not claimed in advance. Each
incident file states what was actually checked; nothing here should be
read as a claim about a live production deployment or a vendor
certification unless explicitly stated in that file.

## Companion projects

Part of a three-project set demonstrating different layers of network
engineering: infrastructure design (hybrid architecture / IaC), operational
automation (Netmiko/Ansible), and — this repository — security operations,
troubleshooting, and controlled firewall change management.

## Author

**Vijay Kumar Naroju**
GitHub: [@vijaykumarnaroju76-commits](https://github.com/vijaykumarnaroju76-commits)
