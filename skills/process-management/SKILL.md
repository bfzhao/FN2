---
name: "process-management"
description: "Manages system processes including listing, monitoring, and controlling processes. Invoke when user asks about running processes or needs process control."
commands: ["ps aux", "top -bn1", "pgrep", "kill <PID>", "htop"]
---

# Process Management

This skill helps monitor and manage system processes.

## Available Commands

### Listing Processes
- `ps aux` - All running processes
- `ps -ef` - Full process list
- `top -bn1` - Top processes (batch mode)
- `htop` - Interactive process viewer (if available)

### Process Details
- `ps -p <PID> -o pid,ppid,user,cmd,%cpu,%mem,stat` - Specific process info
- `pgrep <pattern>` - Find process by name
- `pkill <pattern>` - Kill process by name

### Process Control
- `kill <PID>` - Terminate process gracefully
- `kill -9 <PID>` - Force kill process
- `killall <process-name>` - Kill all processes by name
- `nohup command &` - Run process in background

### Process Tree
- `pstree` - Process tree view
- `ps -ef --forest` - Hierarchical process list

### Resource Usage
- `top -bn1` - CPU/memory usage
- `iostat` - I/O statistics
- `vmstat 1` - Virtual memory stats

## Usage

When you need to work with processes, invoke this skill with the appropriate command.

## Examples

- "Show running processes" → Use `ps aux` or `top -bn1`
- "Find my application" → Use `ps aux | grep myapp`
- "Kill a process" → Use `pkill <process-name>` or `kill <PID>`
- "Check CPU usage" → Use `top -bn1` or `vmstat 1`

## Safety Notes

- Be careful when killing processes
- Check process ID before killing
- Some system processes should not be killed
