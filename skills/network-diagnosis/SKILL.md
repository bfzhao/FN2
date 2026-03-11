---
name: "network-diagnosis"
description: "Diagnoses network issues including connections, DNS, ports, and connectivity. Invoke when user asks about network status or connectivity issues."
commands: ["ip addr show", "hostname -I", "ping -c 4", "netstat -tuln", "curl google.com"]
---

# Network Diagnosis

This skill helps diagnose network issues and check connectivity.

## Available Commands

### Network Interfaces
- `ip addr show` - All network interfaces
- `ip addr show eth0` - Specific interface
- `ifconfig` - Legacy interface config (if available)

### IP Addresses
- `hostname -I` - Local IP addresses
- `ip route show` - Routing table
- `ip route` - Default route

### Connectivity
- `ping -c 4 google.com` - Test connectivity
- `curl -I https://google.com` - HTTP check
- `wget -q --spider http://example.com` - Quiet check

### DNS
- `nslookup google.com` - DNS lookup
- `dig google.com` - Detailed DNS info
- `cat /etc/resolv.conf` - DNS servers

### Ports & Connections
- `netstat -tuln` - Listening ports
- `ss -tuln` - Modern port check
- `lsof -i :8080` - Process using port

### Network Stats
- `netstat -s` - Protocol statistics
- `nstat` - Network statistics
- `cat /proc/net/dev` - Interface stats

### Firewall
- `ufw status` - Firewall status (Ubuntu)
- `iptables -L` - Firewall rules

## Usage

When you need to check network status, invoke this skill with the appropriate command.

## Examples

- "Check internet connection" → Use `ping -c 4 8.8.8.8` or `curl google.com`
- "Show my IP" → Use `hostname -I` or `curl ifconfig.me`
- "Check listening ports" → Use `netstat -tuln` or `ss -tuln`
- "DNS lookup" → Use `nslookup example.com` or `dig example.com`
- "Test port" → Use `nc -zv hostname port` or `telnet hostname port`

## Safety Notes

- Some commands require root privileges
- Be mindful of network traffic when testing
- Check firewall rules if connection fails
