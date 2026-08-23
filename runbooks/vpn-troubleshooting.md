# VPN Troubleshooting Guide

## Issue: VPN Tunnel Not Establishing

### Symptoms
- VPN status shows "Down"
- Phase 1 negotiation fails
- Unable to ping remote subnet
- VPN logs show connection errors

### Diagnosis Steps

**Step 1: Check VPN Status**
```
Monitor > Logs > System
Filter: vpn
Show: last 50 entries
```

**Step 2: Verify Gateway Connectivity**
```
Device > Diagnostics > Ping
Host: [Remote-VPN-Gateway-IP]
Expected: Success
```

**Step 3: Check IKE Phase 1**
```
Monitor > VPN > IPSec > Gateways
Look for:
- Gateway Status: Up/Down
- Phase 1 State: MM1, MM2, etc.
- Last Error: [if any]
```

**Step 4: Check IPSec Tunnel Status**
```
Monitor > VPN > IPSec > Tunnels
Look for:
- Tunnel State: Active/Down
- Encrypt/Decrypt packets
- Errors: [if any]
```

**Step 5: Review NAT Rules**
```
Policies > NAT > [All NAT Rules]
Check:
- Order of rules
- Source/Dest addresses
- Potential conflicts
```

### Root Cause: Incorrect NAT Rule Ordering

**Problem:**
NAT rules were positioned AFTER generic rules, causing VPN traffic to be NAT-translated before being evaluated for VPN bypass.

**Impact:**
- VPN packets modified by NAT
- Tunnel negotiation fails
- Remote gateway rejects packets
- Tunnel stays down

### Solution

**Step 1: Create Bypass-NAT Rule**
```
Policies > NAT > Add (at TOP of list)

Name: VPN-Bypass-NAT
From Zone: trust
To Zone: untrust
Source Address: [local-subnet]
Destination Address: [remote-subnet]
Service: any
Translation Type: None (bypass)
Move to position: 1
Enable: yes
Commit
```

**Step 2: Verify Rule Order**
```
Policies > NAT
Order should be:
1. VPN-Bypass-NAT (no translation)
2. Internal-to-Internet-SNAT (translate)
3. [Other rules]
```

**Step 3: Reset VPN Tunnel**
```
Monitor > VPN > IPSec > Tunnels
Select tunnel > Clear IKE SA
Wait 10 seconds for renegotiation
```

**Step 4: Verify Tunnel Status**
```
Monitor > VPN > IPSec > Tunnels
Expected:
- Tunnel State: Active
- Encrypt/Decrypt packets > 0
- No errors
```

**Step 5: Test Connectivity**
```
Device > Diagnostics > Ping
Host: [remote-subnet-host]
Expected: Success
```

### Verification

✅ VPN Tunnel Status: Active
✅ Ping to remote subnet: Successful
✅ Bidirectional traffic: Confirmed
✅ NAT bypass verified: Yes
✅ Tunnel stable: Yes (tested 30 min)

## Prevention

### Best Practices

1. **NAT Rule Ordering**
   - Place bypass rules first
   - Review order monthly
   - Document all rules

2. **VPN Configuration**
   - Test immediately after setup
   - Monitor tunnel health
   - Alert on tunnel down

3. **Testing**
   - Verify bidirectional traffic
   - Test failover scenarios
   - Monitor long-term stability

### Monitoring Setup

**Enable VPN Logging**
```
Device > Setup > Logging
VPN Events: Enable
Log Level: informational

Policies > Security > [VPN Policy]
Logging Tab:
- Log at Session Start: yes
- Log at Session End: yes
- Log Session Summary: yes
```

**Create Alerts**
```
Device > Alert Rules > Add

Name: VPN-Tunnel-Down
Event Type: VPN
Trigger: Tunnel Down
Action: Email to admin@lab.local
```

## Common VPN Issues

### Issue 1: Phase 1 Fails
**Cause:** IKE negotiation mismatch
**Solution:** 
- Verify IKE proposals match
- Check pre-shared key
- Verify encryption algorithms

### Issue 2: Phase 2 Fails
**Cause:** IPSec transform mismatch
**Solution:**
- Match IPSec crypto profiles
- Verify DH groups
- Check ESP protocols

### Issue 3: Slow Throughput
**Cause:** Policy mismatch or logging overhead
**Solution:**
- Review security policies
- Disable verbose logging
- Enable hardware acceleration

### Issue 4: Intermittent Disconnects
**Cause:** Session timeout or NAT issues
**Solution:**
- Increase DPD timeout
- Configure keepalives
- Verify NAT rules

## Commands Reference

### View VPN Status
```
> show vpn ipsec status
> show vpn flow name [tunnel-name]
> show vpn gateway [gateway-name]
```

### Clear VPN Session
```
> clear vpn ipsec sa gateway [gateway-name]
> clear vpn ipsec sa tunnel [tunnel-name]
```

### Debug VPN
```
> debug ike on
> debug crypto on
> debug vpn on
```

### Monitor VPN Packets
```
> show session all filter application vpn
> show counter global filter delta yes
```

## Lab Results

✅ VPN tunnel established successfully
✅ Bidirectional traffic flowing
✅ NAT rules properly ordered
✅ Bypass rules verified
✅ Tunnel stable and monitored
✅ Performance baseline established

---

**Troubleshooting Complete** - VPN operational and stable
