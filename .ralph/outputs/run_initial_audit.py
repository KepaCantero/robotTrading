#!/usr/bin/env python3
"""Initial Audit: Validate all production Python files and generate audit report."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

def main():
    # Load file list
    file_list_path = Path(".ralph/outputs/PRODUCTION_FILE_LIST.json")
    with open(file_list_path) as f:
        data = json.load(f)
    
    files = data["files"]
    total = len(files)
    
    print(f"Starting Initial Audit of {total} files...", file=sys.stderr)
    
    passed_files = []
    failed_files = []
    
    for i, filepath in enumerate(files, 1):
        if i % 100 == 0 or i == total:
            print(f"Progress: {i}/{total} ({100*i//total}%) - Passed: {len(passed_files)}, Failed: {len(failed_files)}", file=sys.stderr)
        
        try:
            result = subprocess.run(
                ["bash", "scripts/validate_file_complete.sh", filepath],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse JSON output
            output = result.stdout.strip()
            if output:
                validation = json.loads(output)
                summary = validation.get("summary", {})
                
                if summary.get("success"):
                    passed_files.append(filepath)
                else:
                    checks = validation.get("checks", {})
                    failed_checks = [name for name, info in checks.items() 
                                    if isinstance(info, dict) and info.get("status") == "failed"]
                    failed_files.append({
                        "file": filepath,
                        "failed_checks": failed_checks,
                        "summary": {
                            "passed": summary.get("passed", 0),
                            "failed": summary.get("failed", 0)
                        }
                    })
            else:
                # Script produced no output - treat as error
                failed_files.append({
                    "file": filepath,
                    "failed_checks": ["script_error"],
                    "summary": {"passed": 0, "failed": 11}
                })
        except subprocess.TimeoutExpired:
            failed_files.append({
                "file": filepath,
                "failed_checks": ["timeout"],
                "summary": {"passed": 0, "failed": 11}
            })
        except json.JSONDecodeError:
            failed_files.append({
                "file": filepath,
                "failed_checks": ["json_parse_error"],
                "summary": {"passed": 0, "failed": 11}
            })
        except Exception as e:
            failed_files.append({
                "file": filepath,
                "failed_checks": [str(e)[:50]],
                "summary": {"passed": 0, "failed": 11}
            })
    
    # Generate audit report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": total,
        "passed": len(passed_files),
        "failed": len(failed_files),
        "pass_rate": round(100 * len(passed_files) / total, 2) if total > 0 else 0,
        "failed_files": failed_files
    }
    
    report_path = Path(".ralph/outputs/PRODUCTION_AUDIT_REPORT.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nAudit Complete!", file=sys.stderr)
    print(f"Total: {total}", file=sys.stderr)
    print(f"Passed: {len(passed_files)}", file=sys.stderr)
    print(f"Failed: {len(failed_files)}", file=sys.stderr)
    print(f"Pass Rate: {report['pass_rate']}%", file=sys.stderr)
    print(f"Report saved to: {report_path}", file=sys.stderr)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
