#!/usr/bin/env python3
"""
Pre-tool-use hook for .ralph
Validates tool calls before execution
"""
import json
import sys

def main():
    # Read hook input from stdin
    input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Validation rules
    blocked_tools = [
        # Dangerous operations
        "Bash(rm -rf /)",  # Recursive delete
        "Bash(format",  # Format disk (Windows)
        "Bash(del * /.*",  # Delete all
    ]

    # Check if tool is blocked
    for blocked in blocked_tools:
        if blocked in tool_name:
            print(json.dumps({
                "status": "block",
                "reason": f"Tool '{tool_name}' is blocked for safety"
            }))
            sys.exit(0)

    # Log tool use for    log_file = Path(".ralph/logs/tool_usage.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, "a") as f:
        f.write(json.dumps({
            "timestamp": input_data.get("timestamp", ""),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "status": "allowed"
        }) + "\n")

    # Allow tool
    print(json.dumps({
        "status": "allow",
        "reason": "Tool validated"
    }))


if __name__ == "__main__":
    main()
