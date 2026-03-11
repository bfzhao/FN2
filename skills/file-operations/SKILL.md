---
name: "file-operations"
description: "Performs file operations including reading, writing, searching, and listing files. Invoke when user asks for file manipulation or content inspection."
commands: ["ls -la", "cat /path/to/file", "grep -r", "find . -name", "stat /path/to/file"]
---

# File Operations

This skill provides safe file operations using shell commands.

## Available Commands

### Listing Files
- `ls -la` - List all files with details
- `ls -lh` - Human-readable file sizes
- `find /path -name "*.ext"` - Find files by pattern
- `tree /path` - Directory tree structure

### Reading Files
- `cat /path/to/file` - Display file content
- `head -n 20 /path/to/file` - First N lines
- `tail -n 20 /path/to/file` - Last N lines
- `less /path/to/file` - Page through file

### Searching
- `grep "pattern" /path/to/file` - Search in file
- `grep -r "pattern" /path/` - Recursive search
- `find . -name "*.py" -exec grep "pattern" {} \;` - Find and search

### File Info
- `stat /path/to/file` - File status
- `file /path/to/file` - File type
- `wc -l /path/to/file` - Line count

### File Operations
- `cp source dest` - Copy file
- `mv source dest` - Move/rename
- `rm /path/to/file` - Delete file (be careful!)
- `mkdir /path` - Create directory
- `chmod 644 /path/to/file` - Change permissions

## Usage

When you need to work with files, invoke this skill with the appropriate command.

## Safety Notes

- Always verify file paths before operations
- Use `ls` first to verify file exists
- Be careful with `rm` and `chmod` commands

## Examples

- "Show me the log file" → Use `cat /var/log/syslog` or `tail -n 50 /path/to/log`
- "Find Python files" → Use `find . -name "*.py"`
- "Search for errors" → Use `grep -i "error" /path/to/file`
