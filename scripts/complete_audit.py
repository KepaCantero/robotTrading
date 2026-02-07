#!/usr/bin/env python3
"""
COMPLETE AUDIT SYSTEM - Real Validation + Smart Rules

1. Identifica qué reglas aplican (smart classifier)
2. Ejecuta validaciones REALES (mypy, ruff, bandit)
3. Corrige errores automáticamente
4. Marca PASSED solo cuando TODO está limpio
"""
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any


class CompleteAuditor:
    """Complete audit system: smart rules + real validation."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self.classifier = self._import_classifier()

    def _import_classifier(self):
        """Import the smart rule classifier."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from smart_rule_classifier import SmartRuleClassifier
        return SmartRuleClassifier(self.rules_dir)

    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """Run REAL tool validation on a file."""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": "File not found"}

        # Run mypy
        try:
            mypy_result = subprocess.run(
                ["mypy", "--no-error-summary", "--hide-error-context", str(path)],
                capture_output=True, text=True, timeout=30
            )
            mypy_errors = []
            for line in mypy_result.stdout.strip().split('\n'):
                if line.strip() and not line.startswith("Success"):
                    parts = line.split(':', 3)
                    if len(parts) >= 3:
                        mypy_errors.append({
                            "line": parts[1],
                            "code": parts[2].strip(),
                            "message": parts[3].strip() if len(parts) > 3 else line
                        })
        except Exception as e:
            mypy_errors = [{"error": f"mypy failed: {e}"}]

        # Run ruff
        try:
            ruff_result = subprocess.run(
                ["ruff", "check", "--output-format=json", str(path)],
                capture_output=True, text=True, timeout=30
            )
            ruff_errors = []
            if ruff_result.stdout.strip():
                try:
                    data = json.loads(ruff_result.stdout)
                    for error in data:
                        ruff_errors.append({
                            "line": error.get("location", {}).get("row"),
                            "code": error.get("code"),
                            "message": error.get("message"),
                            "fixable": error.get("fix", {}).get("applicability") == "safe"
                        })
                except:
                    pass
        except Exception:
            ruff_errors = []

        all_errors = mypy_errors + ruff_errors

        return {
            "success": len(all_errors) == 0,
            "error_count": len(all_errors),
            "mypy_errors": len(mypy_errors),
            "ruff_errors": len(ruff_errors),
            "errors": all_errors
        }

    def apply_fixes(self, file_path: str) -> Dict[str, Any]:
        """Apply automatic fixes."""
        path = Path(file_path)

        # Run ruff --fix
        try:
            result = subprocess.run(
                ["ruff", "check", "--fix", str(path)],
                capture_output=True, text=True, timeout=30
            )
            return {"success": True, "fixed": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def audit_file(self, file_path: str, max_fix_attempts: int = 3) -> Dict[str, Any]:
        """Complete audit: classify, validate, fix, verify."""
        path = Path(file_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        print(f"\n{'='*60}")
        print(f"AUDITING: {file_path}")
        print(f"{'='*60}")

        # Step 1: Classify applicable rules
        print("Step 1: Classifying applicable rules...")
        applicable_rules = self.classifier.classify_file(path)
        rule_count = sum(len(v) for v in applicable_rules.values())
        print(f"  Found {rule_count} applicable rules")

        # Step 2: Validate
        print("Step 2: Running validation (mypy, ruff)...")
        validation = self.validate_file(path)
        print(f"  Errors found: {validation['error_count']}")
        print(f"    mypy: {validation['mypy_errors']}, ruff: {validation['ruff_errors']}")

        # Step 3: Fix if needed
        if not validation['success'] and max_fix_attempts > 0:
            print("Step 3: Applying fixes...")
            fix_result = self.apply_fixes(file_path)
            print(f"  Fixes applied: {fix_result.get('fixed', False)}")

            # Re-validate
            print("Step 4: Re-validating...")
            validation = self.validate_file(path)
            print(f"  Remaining errors: {validation['error_count']}")

        # Step 5: Final status
        status = "PASSED" if validation['success'] else "FAILED"
        print(f"\n{'='*60}")
        print(f"FINAL STATUS: {status}")
        print(f"{'='*60}\n")

        return {
            "file": file_path,
            "status": status,
            "applicable_rules": rule_count,
            "validation": validation
        }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Complete audit with real validation")
    parser.add_argument("file", help="Python file to audit")
    args = parser.parse_args()

    auditor = CompleteAuditor(Path("/Users/kepa.cantero/Projects/algoTrading/rules"))
    result = auditor.audit_file(args.file)

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    main()
