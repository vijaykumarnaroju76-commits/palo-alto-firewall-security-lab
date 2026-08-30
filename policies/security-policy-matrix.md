# Security Policy Matrix

Reference rule base for the lab topology used throughout this repository. Zones,
subnets, and object names here are the shared baseline that the incidents in
[`incident-command-center/`](../incident-command-center/) and the runbooks in
[`runbooks/`](../runbooks/) refer back to, so a rule name or object mentioned in
an incident writeup can be looked up here.

All addresses use IANA-reserved documentation ranges (RFC 1918 for internal
space, RFC 5737 `192.0.2.0/24` / `198.51.100.0/24` / `203.0.113.0/24` for
anything facing the internet) — see [`evidence/README.md`](../evidence/README.md)
for the sanitization convention used across the repo.

## Zones and subnets

| Zone | Interface | Subnet | Purpose |
|------|-----------|--------|---------|
| `trust` | ethernet1/1 | 10.0.1.0/24 | Internal workstations/servers |
| `trust` (extended) | ethernet1/1.4 | 10.0.4.0/24 | New department segment added post-launch (see INC-003) |
| `dmz` | ethernet1/2 | 10.0.2.0/24 | Published services |
| `untrust` | ethernet1/3 | 203.0.113.0/28 | Primary ISP (ISP-A) |
| `untrust2` | ethernet1/4 | 198.51.100.0/28 | Redundant ISP (ISP-B), added for INC-004 |
| `vpn` (via `tunnel.1`) | tunnel.1 | 172.16.50.0/24 (remote) | Partner site-to-site IPsec |

## Address objects

| Object | Value | Notes |
|--------|-------|-------|
| `Internal-Subnet` | 10.0.1.0/24 | Trust zone hosts |
| `New-Dept-Subnet` | 10.0.4.0/24 | Added after INC-003 postmortem |
| `DMZ-Subnet` | 10.0.2.0/24 | DMZ zone |
| `Web-Server` | 10.0.2.10/32 | Legacy published web server |
| `NewApp-Server` | 10.0.2.20/32 | New app published in INC-001 |
| `Inventory-API-Server` | 10.0.2.30/32 | Internal API service, INC-002 |
| `Public-IP-Pool` | 203.0.113.0/24 | **Overly broad** — root contributor to INC-001, narrowed post-fix |
| `Public-IP-WebServer` | 203.0.113.50/32 | Narrowed replacement for the legacy DNAT target |
| `Public-IP-NewApp` | 203.0.113.51/32 | Dedicated public IP for the new app |
| `Partner-Remote-Subnet` | 172.16.50.0/24 | Partner-side protected network across the IPsec tunnel |

## Security rule base (top to bottom, first-match order)

| # | Name | From → To | Source | Destination | Application | Service | Action | Log | Notes |
|---|------|-----------|--------|-------------|-------------|---------|--------|-----|-------|
| 1 | `Allow-Internet-to-WebServer` | untrust → dmz | any | Public-IP-WebServer | web-browsing, ssl | tcp/80, tcp/443 | Allow | Yes | Original public destination address with post-DNAT `dmz` zone |
| 2 | `Allow-Internet-to-NewApp` | untrust → dmz | any | Public-IP-NewApp | web-browsing, ssl | tcp/443 | Allow | Yes | Added for INC-001 fix; requires the narrowed NAT object above |
| 3 | `Allow-Trust-to-Inventory-API` | trust → dmz | Internal-Subnet | Inventory-API-Server | inventory-api (custom App-ID) | tcp/8443 | Allow | Yes | App changed from generic `ssl` to a registered custom app after INC-002 |
| 4 | `Allow-Internal-to-DMZ` | trust → dmz | Internal-Subnet | any | any | any | Allow | Yes | Broad legacy rule; candidate for tightening (see `change-review-checklist.md`) |
| 5 | `Allow-Trust-to-Partner-VPN` | trust → vpn | Internal-Subnet, New-Dept-Subnet | Partner-Remote-Subnet | any | any | Allow | Yes | `New-Dept-Subnet` added after INC-003; must stay in lock-step with the tunnel's proxy-ID |
| 6 | `Allow-Outbound-Web` | trust → untrust, untrust2 | Internal-Subnet | any | web-browsing, ssl, dns | any | Allow | Yes | Matches on both ISP zones; see INC-004 for why that matters |
| 7 | `Deny-Unknown-Apps` | any → any | any | any | unknown-tcp, unknown-udp, incomplete | any | Deny | Yes | Explicit deny so unclassified traffic is visible in logs rather than silently swallowed by rule 8 |
| 8 | `Deny-All` | any → any | any | any | any | any | Deny | Yes | Default deny, logged |

## Reading this table during an incident

- Palo Alto security policy is **first-match, top-to-bottom** — a broader rule
  higher in the list can shadow a more specific rule below it even when both
  would technically match. Always check rule order, not just rule content.
- The `Application` column is evaluated against **App-ID's classification**,
  not the destination port. A rule scoped to `ssl` will not match traffic
  App-ID reclassifies as `unknown-tcp` mid-session — see
  [`INC-002`](../incident-command-center/INC-002-security-policy-deny.md).
- `Deny-Unknown-Apps` (rule 7) exists specifically so that App-ID
  misclassification shows up as a distinct, loggable deny reason instead of
  disappearing into the generic default-deny at the bottom.
