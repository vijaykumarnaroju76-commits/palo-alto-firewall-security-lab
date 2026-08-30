# INC-005 — Active/Passive HA Failover Causes Partial Connectivity Loss

## Scenario Type

Modeled Palo Alto Networks VM-Series active/passive HA incident.

This scenario demonstrates the troubleshooting and validation method that would be used during an HA failover event. It does not claim execution against a production HA pair.

## Impact

The primary firewall becomes unavailable and the passive peer transitions to active.

The HA state transition succeeds, but some applications remain unreachable after failover.

The firewall has recovered, but end-to-end service has not.

## Symptom

- Passive firewall transitions to active.
- Management access to the new active firewall works.
- Some outbound traffic succeeds.
- Published applications and selected sessions fail.
- Security and NAT policies appear unchanged.
- The issue begins immediately after failover.

## Initial Hypotheses

1. HA failover did not complete correctly.
2. Configuration was not synchronized between peers.
3. Interfaces on the new active firewall remained down.
4. Routing was missing after failover.
5. NAT or security policy differed between peers.
6. Session state was not synchronized.
7. Upstream network devices retained stale Layer-2 forwarding information.

## Investigation

### 1. Verify HA State

Confirm exactly one peer is active.

Checks:

```text
show high-availability state
show high-availability all
```

Modeled result:

```text
PA-VM-02: active
PA-VM-01: unavailable
```

The HA role transition completed successfully.

### 2. Verify Configuration Synchronization

Confirm the peers were synchronized before failure.

Modeled result:

```text
Configuration synchronized: yes
```

Configuration drift is ruled out.

### 3. Verify Interfaces

Check dataplane interfaces:

```text
show interface all
```

Modeled result:

```text
ethernet1/1  up
ethernet1/2  up
ethernet1/3  up
```

Interface state is healthy.

### 4. Verify Routing

Validate the route and next hop:

```text
show routing route
test routing fib-lookup virtual-router default ip 203.0.113.10
```

The destination resolves through the expected next hop. Routing is ruled out.

### 5. Verify NAT and Security Policy

Check expected rule matches:

```text
show rule-hit-count vsys vsys1 rule-base nat
show rule-hit-count vsys vsys1 rule-base security
```

Expected NAT and security rules are present and receiving hits. Policy is ruled out.

### 6. Inspect Sessions

Check new sessions on the active peer:

```text
show session all
```

Sessions reach the firewall, but affected application traffic does not complete.

### 7. Expand Beyond the Firewall

HA state, interfaces, routing, NAT, security policy, and session processing are functioning.

The new active peer assumes the shared forwarding identity, but the upstream device does not refresh its Layer-2 neighbor/forwarding entry from the failover gratuitous ARP update. Traffic therefore continues toward the previous forwarding path.

## Root Cause

The Palo Alto HA transition completed successfully, but the surrounding network did not reconverge immediately to the new active dataplane path.

The upstream device failed to learn or propagate the gratuitous ARP update generated during failover, leaving stale Layer-2 forwarding information for the previous active path.

A successful HA role transition does not by itself prove application recovery. End-to-end forwarding must also be validated.

## Fix

Refresh the affected upstream Layer-2 neighbor state so forwarding points to the new active firewall.

In a production design, manual clearing should be a recovery measure, not the normal HA mechanism. The preferred design is to ensure gratuitous ARP and neighbor updates generated during failover are accepted and propagated correctly by adjacent network devices.

## Validation

Post-failover validation must confirm:

- exactly one active firewall
- configuration synchronization is healthy
- dataplane interfaces are up
- expected routes are installed
- next-hop resolution is correct
- expected NAT rules match
- expected security rules match
- new sessions establish
- upstream Layer-2 forwarding has converged
- representative applications are reachable

The failover is successful only when both the HA role transition and end-to-end service recovery are verified.

## Evidence

Evidence for this modeled incident includes:

- HA state checks
- configuration synchronization checks
- interface-state checks
- route and FIB lookup validation
- NAT and security rule-hit validation
- session inspection
- Layer-2 convergence analysis
- structured post-fix validation JSON

All command output and addresses in this scenario are sanitized or synthetic documentation examples.

## Prevention

1. Test HA failover during controlled maintenance windows.
2. Validate upstream and downstream network behavior during failover.
3. Verify gratuitous ARP and Layer-2 convergence behavior.
4. Include application testing in HA acceptance criteria.
5. Maintain a pre/post-failover validation checklist.
6. Monitor firewall role transition and service recovery as separate events.
7. Treat an active firewall state as necessary but not sufficient evidence of successful recovery.
