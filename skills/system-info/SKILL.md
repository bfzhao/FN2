---
name: "system-info"
description: "Collects system information including OS, CPU, memory, disk, and GPU. Invoke when user asks for system specs, hardware info, or system diagnostics."
commands: ["uname -a", "lscpu", "free -h", "df -h", "nvidia-smi"]
---

# System Information Collector

This skill collects comprehensive system information using shell commands.

## Available Commands

### OS Information
- `uname -a` - Full system information
- `cat /etc/os-release` - Operating system details
- `hostname` - Hostname

### CPU Information
- `lscpu` - CPU architecture details
- `cat /proc/cpuinfo` - Detailed CPU info

### Memory Information
- `free -h` - Memory usage in human-readable format
- `cat /proc/meminfo` - Detailed memory info

### Disk Information
- `df -h` - Disk space usage
- `lsblk` - Block device list
- `du -sh /path` - Directory size

### GPU Information
- `nvidia-smi` - NVIDIA GPU status (if available)
- `lspci | grep -i vga` - GPU hardware

### Network Information
- `ip addr show` - Network interfaces
- `hostname -I` - IP addresses
- `netstat -tuln` - Network connections

### System Status
- `uptime` - System uptime and load
- `top -bn1` - Process summary
- `dmesg | tail` - Recent kernel messages

## Usage

When you need system information, invoke this skill with the appropriate command.

## Examples

- "Get system specs" → Use `uname -a`, `lscpu`, `free -h`
- "Check disk space" → Use `df -h`, `lsblk`
- "GPU status" → Use `nvidia-smi`
