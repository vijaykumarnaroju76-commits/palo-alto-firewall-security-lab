# INC-006 — GlobalProtect Connected but Internal Applications Unreachable

## Scenario Type

Modeled Palo Alto Networks GlobalProtect remote-access incident.

This scenario demonstrates how to troubleshoot a user who successfully authenticates and shows a connected GlobalProtect tunnel but cannot reach internal applications. It does not claim execution against a production remote-access environment.

## Impact

A remote user successfully connects to the GlobalProtect gateway and receives a tunnel IP address.

Internet access remains available, but internal applications are unreachable.

The VPN appears healthy from the user's perspective, yet application traffic does not match the intended access policy.

## Symptom

- GlobalProtect status shows connected.
- User authentication succeeds.
- A tunnel IP is assigned.
- Internal DNS may resolve correctly.
- Internal application traffic is denied.
- Other users may remain unaffected.
- The issue is specific to policy enforcement after tunnel establishment.

## Initial Hypotheses

1. Portal or gateway authentication failed.
2. The client did not receive a valid tunnel IP.
3. Split-tunnel routes are missing.
4. Internal DNS is incorrect.
5. The expected User-ID mapping is missing.
6. Security policy is matching the wrong user or source.
7. The application is unavailable independently of GlobalProtect.

## Investigation

### 1. Verify Portal and Gateway Session

Confirm that authentication and gateway establishment completed successfully.

Example checks:

```text
show global-protect-gateway current-user
show global-protect-gateway statistics
```

Modeled result:

```text
User: user1@example.com
Gateway: gp-gateway
Status: connected
Tunnel IP: 10.20.30.25
```

Authentication and tunnel establishment are ruled out.

### 2. Verify Tunnel IP Assignment

Confirm that the user received an address from the expected GlobalProtect client pool.

The assigned address is valid and does not overlap an internal subnet.

Tunnel address assignment is ruled out.

### 3. Verify Internal Route Selection

Check that traffic for the internal application is sent through the GlobalProtect tunnel and that the firewall has a valid route toward the destination.

Example firewall lookup:

```text
test routing fib-lookup virtual-router default ip 10.0.20.50
```

The destination resolves through the expected internal next hop.

Routing is ruled out.

### 4. Verify DNS Resolution

The client resolves the internal application name to the expected private address.

Modeled result:

```text
app.internal.example -> 10.0.20.50
```

DNS is ruled out.

### 5. Verify User-ID Mapping

Check whether the tunnel IP is mapped to the authenticated user:

```text
show user ip-user-mapping all
```

Expected:

```text
10.20.30.25 -> user1@example.com
```

Observed modeled result:

```text
10.20.30.25 -> unknown
```

The GlobalProtect tunnel is established, but the expected IP-to-user mapping is missing.

### 6. Correlate Traffic Logs and Security Policy

Review traffic logs for the affected source IP.

The session reaches the firewall from the GlobalProtect zone, but the Source User field is empty or unknown.

The intended allow rule requires the authenticated user or directory group. Because the User-ID mapping is absent, that rule does not match and the session falls to a broader deny rule.

This explains why the VPN can show connected while application access still fails.

## Root Cause

GlobalProtect authentication and tunnel establishment succeeded, but the firewall did not have the expected User-ID mapping between the assigned tunnel IP and the authenticated user.

The security policy protecting the internal application was identity-based. With the source user unresolved, the intended allow rule could not match, so traffic was denied by the subsequent rule.

The key operational lesson is:

> A connected GlobalProtect tunnel proves remote-access establishment, not authorization to every internal application.

Authentication, IP assignment, routing, identity mapping, and security-policy evaluation must be validated separately.

## Fix

Restore the expected IP-to-user mapping for the affected GlobalProtect client and verify that the firewall identifies the source user correctly.

Validate that GlobalProtect authentication information is being learned by User-ID and that the assigned tunnel IP maps to the authenticated user.

After the mapping is restored, re-evaluate the affected traffic against the intended identity-based security rule.


## Validation

Post-fix validation must confirm:

- GlobalProtect remains connected.
- The client retains the expected tunnel IP address.
- Internal DNS resolution remains correct.
- The route to the internal application is correct.
- The tunnel IP maps to the authenticated user.
- Traffic logs show the expected Source User.
- The intended identity-based security policy matches.
- The session is allowed.
- The internal application is reachable.

A successful VPN connection and successful application access are treated as separate validation points.


## Evidence

Evidence for this modeled incident includes:

- GlobalProtect gateway and connected-user state.
- Tunnel IP assignment validation.
- Internal route lookup validation.
- Internal DNS resolution validation.
- User-ID IP-to-user mapping inspection.
- Traffic-log correlation for the affected source IP.
- Security-policy match analysis before and after identity restoration.
- Structured post-fix validation JSON.

All usernames, IP addresses, application names, and command outputs in this scenario are sanitized or synthetic documentation examples.


## Prevention

1. Monitor GlobalProtect sessions that do not have a corresponding User-ID mapping.
2. Validate User-ID health during remote-access changes.
3. Include identity-based security-policy checks in GlobalProtect acceptance testing.
4. Correlate gateway authentication events with IP-to-user mappings.
5. Test representative internal applications after portal, gateway, authentication, or policy changes.
6. Document expected fallback behavior when user identity cannot be resolved.
7. Treat tunnel establishment, identity resolution, policy authorization, and application reachability as separate health checks.
