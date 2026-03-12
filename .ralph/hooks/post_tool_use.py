#!/usr/bin/env python3
"""
Post-tool-use hook for .ralph
Validates tool outputs after execution
"""
import json
import sys


def main():
    """Main hook function."""
    # Read hook input from stdin
    input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    tool_output = input_data.get("tool_output", {})

    # Check for required patterns in output
    issues = []

    # Convert output to string for checking
    output_str = str(tool_output) if tool_output else ""

    # Check for TODO/FIXME comments that should be resolved
    if tool_output:
        if "TODO:" in output_str or "FIXME:" in output_str:
            issues.append("Output contains TODO/FIXME - should be resolved")

    # Check for empty outputs
    if not output_str or output_str.strip() == "":
        issues.append("Empty output - no work done")

    # Check for error patterns
    error_patterns = [
        "Error:",
        "Exception:",
        "Traceback:",
        "Failed:",
    ]

    for pattern in error_patterns:
        if pattern in output_str:
            issues.append(f"Output contains error pattern: {pattern}")

    # Report issues
    if issues:
        print(json.dumps({
            "status": "warn",
            "issues": issues,
            "suggestion": "Review and fix the issues before continuing"
        }))
    else:
        print(json.dumps({
            "status": "allow",
            "issues": [],
            "message": "Output validated"
        }))


if __name__ == "__main__":
    main()
