# GlobalProtect and User-ID Troubleshooting

Use this runbook when a GlobalProtect user shows connected but cannot reach an expected internal application.

## Troubleshooting Order

1. Confirm portal and gateway authentication.
2. Confirm the GlobalProtect tunnel is established.
3. Confirm the client received the expected tunnel IP.
4. Confirm routing toward the internal destination.
5. Confirm internal DNS resolution.
6. Confirm the tunnel IP has the expected User-ID mapping.
7. Correlate the Source User field in traffic logs.
8. Confirm the intended identity-based security rule matches.
9. Validate application reachability.

A connected VPN status does not prove that application authorization succeeded.

## 1. Gateway and User State

Example checks:

    show global-protect-gateway current-user
    show global-protect-gateway statistics

Confirm the expected user, gateway, connection state, and tunnel IP.

## 2. Routing and DNS

Confirm that the internal application resolves to the expected private address and that the firewall has a valid route toward that destination.

Example route check:

    test routing fib-lookup virtual-router default ip 10.0.20.50

If routing and DNS are correct, continue to identity validation rather than assuming the VPN tunnel is the problem.

## 3. User-ID Mapping

Inspect the IP-to-user mapping table:

    show user ip-user-mapping all

The GlobalProtect tunnel IP should map to the authenticated user.

If the tunnel is established but the tunnel IP has no corresponding user mapping, identity-based security rules may not match.

## 4. Traffic Logs and Security Policy

Review the affected session in Monitor > Logs > Traffic and correlate:

- Source IP
- Source User
- Source and destination zones
- Application
- Matched security rule
- Action

If Source User is unknown while the intended allow rule requires a user or directory group, the session can fall through to a later deny rule.

This separates a healthy GlobalProtect tunnel from failed application authorization.

## 5. Recovery Validation

After correcting the identity-mapping problem, verify:

- GlobalProtect remains connected.
- The tunnel IP maps to the authenticated user.
- Traffic logs show the expected Source User.
- The intended identity-based security rule matches.
- The session action is allow.
- The internal application is reachable.

Do not close the incident based only on tunnel status. Validate end-to-end application access.
