# Palo Alto Active/Passive HA Failover Validation

Use this checklist during planned HA testing or incident investigation.

## Pre-Failover

- Confirm current active/passive roles.
- Confirm configuration synchronization.
- Confirm HA control and data links.
- Record interface state.
- Record routing table and next-hop state.
- Record security and NAT rule-hit counters.
- Capture representative application reachability.
- Record relevant sessions.

## During Failover

- Confirm peer state transition.
- Record transition timing.
- Verify dataplane interfaces become operational.
- Confirm routing remains available.
- Check for new sessions on the active peer.
- Observe upstream and downstream Layer-2 convergence.

## Post-Failover

- Confirm exactly one active peer.
- Confirm expected routes and next hops.
- Confirm security policy matches.
- Confirm NAT policy matches.
- Confirm representative sessions establish.
- Validate application reachability.
- Confirm upstream Layer-2 forwarding has converged.
- Record evidence.

## Success Criteria

A failover is successful only when both conditions are true:

1. The HA role transition completed correctly.
2. End-to-end application traffic recovered successfully.

An active firewall state by itself is not sufficient proof of service recovery.
