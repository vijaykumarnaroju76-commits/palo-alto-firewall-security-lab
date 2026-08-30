# INC-004 — Session Table Before/After Comparison

Synthetic data for portfolio demonstration only. See
[`../README.md`](../README.md) for the IP-range convention used throughout
this repository.

## During the incident: same flow, split across two interfaces

Outbound (client → partner API) packets and inbound (partner API → client)
packets for the **same logical connection** were observed arriving on
different firewall interfaces — the signature of asymmetric routing.

### Outbound leg — captured on `untrust` (ISP-A, 203.0.113.0/28)

| time | src | sport | dst | dport | egress-if | nat-src |
|------|-----|-------|-----|-------|-----------|---------|
| 09:12:01.114 | 10.0.1.77 | 54211 | 192.0.2.44 | 443 | ethernet1/3 (untrust) | 203.0.113.10 |

### Return leg — captured on `untrust2` (ISP-B, 198.51.100.0/28), same 5-tuple

| time | src | sport | dst | dport | ingress-if | matched-session |
|------|-----|-------|-----|-------|------------|-----------------|
| 09:12:01.298 | 192.0.2.44 | 443 | 203.0.113.10 | 54211 | ethernet1/4 (untrust2) | **none — dropped (asymmetric path)** |

The SYN-ACK for a session that egressed via ISP-A arrived back via ISP-B.
PAN-OS has no session record on `untrust2` for this 5-tuple (the session
was created against `untrust`), so the packet does not match and is
dropped — correct stateful behavior, given the routing that produced it.

### Drop counter, same window

```
> show counter global filter delta yes severity drop
```

| counter | delta |
|---------|-------|
| flow_tcp_non_syn | 0 |
| session_discard_asymmetric_path | 214 |

## After the fix: PBF pins the flow to a single path

### Outbound leg — `untrust` (ISP-A)

| time | src | sport | dst | dport | egress-if | nat-src |
|------|-----|-------|-----|-------|-----------|---------|
| 11:40:02.001 | 10.0.1.77 | 55810 | 192.0.2.44 | 443 | ethernet1/3 (untrust) | 203.0.113.10 |

### Return leg — now also `untrust` (ISP-A), matching the session

| time | src | sport | dst | dport | ingress-if | matched-session |
|------|-----|-------|-----|-------|------------|-----------------|
| 11:40:02.183 | 192.0.2.44 | 443 | 203.0.113.10 | 55810 | ethernet1/3 (untrust) | 1104822 (ACTIVE) |

### Drop counter, 2-hour soak post-fix

| counter | delta |
|---------|-------|
| session_discard_asymmetric_path | 0 |

Synthetic load test: 480 requests to the partner API over the soak window,
0 failures (compared to ~25% failure rate observed pre-fix).
