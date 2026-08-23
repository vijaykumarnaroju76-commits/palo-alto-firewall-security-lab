# Evidence

Supporting artifacts referenced from each incident writeup in
[`incident-command-center/`](../incident-command-center/): sanitized log
excerpts, session-table comparisons, and structured validation records.

## This is synthetic, sanitized evidence

Every log line, session entry, and IP address in this directory is
**fabricated for this portfolio project** to illustrate the diagnostic
pattern described in the corresponding incident. None of it is captured
from a live production system, and none of it contains real customer,
partner, or employee data.

To make that unambiguous rather than just asserted, every address used
anywhere in this repository comes from an IANA-reserved documentation
range that is guaranteed never to route on the real internet:

| Range | RFC | Used for |
|-------|-----|----------|
| `10.0.0.0/8` | RFC 1918 | Internal (trust/dmz) hosts |
| `172.16.0.0/12` | RFC 1918 | Partner-side internal subnet in VPN scenarios |
| `192.0.2.0/24` | RFC 5737 (TEST-NET-1) | "Public" example addresses where needed |
| `198.51.100.0/24` | RFC 5737 (TEST-NET-2) | Secondary ISP / redundant path examples |
| `203.0.113.0/24` | RFC 5737 (TEST-NET-3) | Primary published/public IPs |

Hostnames, ticket IDs, and personnel are likewise fictional.

## Layout

- `sanitized-traffic-logs/` — plain-text excerpts of traffic/system log
  output, formatted the way `Monitor > Logs` or CLI `show` commands
  present them, trimmed to the fields relevant to each incident.
- `session-analysis/` — before/after session-table comparisons for
  incidents where the session state itself (not a single log line) is the
  key evidence.
- `validation/` — one JSON record per incident capturing the post-fix
  validation checks and their results, in a structured form suitable for
  scripted checking (see the CI workflow, which validates these files'
  syntax on every push).
