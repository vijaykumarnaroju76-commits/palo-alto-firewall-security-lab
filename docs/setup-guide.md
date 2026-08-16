# Palo Alto Firewall Lab - Setup Guide

## Prerequisites

- VMware ESXi/vSphere or KVM hypervisor
- Palo Alto VM-Series OVA file
- Minimum 4 vCPU, 8GB RAM for VM
- Network connectivity (5+ VLANs)
- Management workstation with web browser

## Phase 1: VM Deployment

### Step 1: Upload OVA to Hypervisor
1. Login to vSphere
2. Right-click datacenter → Deploy OVF Template
3. Select Palo Alto VM-Series OVA
4. Follow deployment wizard
5. Configure 4 vCPU, 8GB RAM
6. Attach network adapters to VLANs

### Step 2: Initial Boot
1. Power on VM
2. Wait for boot completion (3-5 minutes)
3. Login via console (admin/admin)
4. Change default password

### Step 3: Network Configuration
```
Configure IP:
eth0/1: 192.168.1.1/24 (Management)
eth0/2: 10.0.1.1/24 (Trust Zone)
eth0/3: 10.0.2.1/24 (DMZ)
eth0/4: 10.0.3.1/24 (Untrust)
```

### Step 4: Web UI Access
1. Open browser: https://192.168.1.1
2. Login: admin/[new-password]
3. Accept license
4. Complete setup wizard

## Phase 2: Initial Configuration

### Hostname & Domain
```
device > setup > hostname: palo-alto-lab
device > setup > domain: lab.local
```

### Admin Accounts
```
device > administrators > Add admin user
- Username: labadmin
- Password: [strong-password]
- Role: superuser
```

### NTP Configuration
```
device > setup > NTP > Add
- Server: 8.8.8.8
- Enable
```

## Phase 3: Zone Configuration

### Create Security Zones

**Trust Zone**
```
Network > Zones > Add
Name: trust
Type: Layer3
Include Interface: ethernet0/2
```

**DMZ Zone**
```
Network > Zones > Add
Name: dmz
Type: Layer3
Include Interface: ethernet0/3
```

**Untrust Zone**
```
Network > Zones > Add
Name: untrust
Type: Layer3
Include Interface: ethernet0/4
```

### Configure IP Addresses
```
Network > Interfaces > Ethernet

Ethernet 0/1 (Management):
- IP: 192.168.1.1/24
- Zone: management

Ethernet 0/2 (Trust):
- IP: 10.0.1.1/24
- Zone: trust

Ethernet 0/3 (DMZ):
- IP: 10.0.2.1/24
- Zone: dmz

Ethernet 0/4 (Untrust):
- IP: 10.0.3.1/24
- Zone: untrust
```

## Phase 4: Address & Service Objects

### Create Address Objects
```
Objects > Addresses > Add

Internal-Subnet: 10.0.1.0/24
DMZ-Subnet: 10.0.2.0/24
Web-Server: 10.0.2.10/32
DB-Server: 10.0.1.20/32
```

### Create Service Objects
```
Objects > Services > Add

HTTP-Alt: TCP 8080
DNS-TCP: TCP 53
NTP: UDP 123
Radius: UDP 1812
```

## Phase 5: Security Policy Configuration

### Inbound Policy (DMZ Traffic)
```
Policies > Security > Add

Name: Allow-Internet-to-DMZ
From Zone: untrust
To Zone: dmz
Source: any
Destination: Web-Server
Service: http, https
Application: web-browsing
Action: allow
Logging: yes
```

### Internal Policy (Trust to DMZ)
```
Policies > Security > Add

Name: Allow-Internal-to-DMZ
From Zone: trust
To Zone: dmz
Source: Internal-Subnet
Destination: any
Service: any
Application: any
Action: allow
Logging: yes
```

### Default Deny Policy
```
Policies > Security > Add

Name: Deny-All
From Zone: any
To Zone: any
Source: any
Destination: any
Service: any
Application: any
Action: deny
Logging: yes
```

## Phase 6: NAT Configuration

### Source NAT (Internal to Internet)
```
Policies > NAT > Add

Name: Internal-to-Internet-SNAT
From Zone: trust
To Zone: untrust
Source Address: Internal-Subnet
Destination Address: any
Service: any
Source Translation:
  - Dynamic IP and Port
  - Translated Address: [External-IP]
```

### Destination NAT (Web Server)
```
Policies > NAT > Add

Name: Internet-to-WebServer-DNAT
From Zone: untrust
To Zone: dmz
Destination Address: [External-IP]
Destination Port: 80
Translated Address: 10.0.2.10
Translated Port: 80
```

## Phase 7: App-ID Configuration

### Enable App-ID
```
Device > Setup > Content-ID > App-ID
Enable: Yes
```

### Create Application Groups
```
Objects > Application Groups > Add

Web-Apps:
- web-browsing
- http
- https

Business-Apps:
- ssl
- dns
- ntp
```

### Create App-Based Policy
```
Policies > Security > Add

Name: Allow-Web-Apps
Application: Web-Apps
Action: allow
Logging: yes
```

## Phase 8: User-ID Configuration

### Configure User-ID Agent
```
Device > User Identification > User-ID Agent
- Enabled: yes
- Port: 5007
```

### LDAP Integration
```
Device > Servers > LDAP > Add

Name: Lab-AD
Server: 10.0.1.50
Port: 389
Base DN: dc=lab,dc=local
Bind DN: admin@lab.local
Password: [admin-password]
```

### Create User-Based Policy
```
Policies > Security > Add

Name: Allow-Admins-Full-Access
Source User: admin@lab.local
Destination: any
Service: any
Action: allow
Logging: yes
```

## Phase 9: VPN Configuration

### IPSec VPN Setup
```
Network > VPN > IPSec Crypto > Add

Name: Site-to-Site-VPN
IKE Version: IKEv2
Encryption: AES-256
Authentication: SHA-256
DH Group: group14
```

### IPSec Tunnel
```
Network > IPSec Tunnels > Add

Name: Site-to-Site-Tunnel
Tunnel Interface: tunnel.1
IKE Gateway: [config-IKE]
IPSec Crypto: Site-to-Site-VPN
LocalSubnet: 10.0.0.0/16
PeerSubnet: 192.168.0.0/16
```

### GlobalProtect Gateway
```
Network > GlobalProtect > Gateway > Add

Name: VPN-Gateway
Authentication:
- LDAP Server: Lab-AD
- Require MFA: yes
- Certificate: [import-cert]
```

## Phase 10: URL Filtering

### Enable URL Filtering
```
Device > Setup > Content-ID > URL Filtering
Enabled: yes
```

### URL Filter Policy
```
Policies > Security > URL Filtering > Add

Name: Block-Adult-Content
Zone: trust to untrust
Categories: Adult, Gambling
Action: deny
Logging: yes
```

### Custom URL List
```
Objects > Custom URL Category > Add

Name: Blocked-Sites
URLs:
- example-blocked.com
- test-block.org
```

## Commit Changes
```
Commit > Commit and Push to Devices
- Description: Initial configuration
- Include device and network
- Wait for completion
```

## Verification

### Check Policy Status
```
Policies > Security > View Policy HitCount
```

### Monitor Traffic
```
Monitor > Traffic > Logs
Filter: last hour
```

### Test Connectivity
```
Device > Diagnostics > Ping
Host: 8.8.8.8
```

---

**Setup Complete!** Lab is ready for testing.
