#!/usr/bin/env python3
"""
Stop hook for .ralph
Handles session termination and cleanup
"""
import json
import sys
from pathlib import Path
from datetime import datetime

def main():
    # Read hook input from stdin
    input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "")
    completion_status = input_data.get("completion_status", "")

    # Save session summary
    summary_file = Path(".ralph/logs/session_summaries.jsonl")
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "completion_status": completion_status,
        "event": "session_end"
    }

    with open(summary_file, "a") as f:
        f.write(json.dumps(summary) + "\n")

    # Archive scratchpad if exists
    scratchpad = Path(".agent/scratchpad.md")
    if scratchpad.exists():
        archive_dir = Path(".ralph/archive")
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_name = f"scratchpad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        scratchpad.rename(archive_dir / archive_name)

    # Allow stop
    print(json.dumps({
        "status": "allow",
        "message": "Session cleanup completed"
    }))


if __name__ == "__main__":
    main()
