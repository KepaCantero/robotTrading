#!/usr/bin/env python3
"""
Fix remaining Pydantic V2 validators
"""

import re
from pathlib import Path


def fix_validators_in_file(file_path: Path):
    """Fix validators in a single file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace @validator with @field_validator and add @classmethod
    content = re.sub(
        r"@validator\(([^)]+)\)\s*\n\s*def (\w+)\(cls, v(?:, [^)]+)?\):",
        r"@field_validator(\1)\n    @classmethod\n    def \2(cls, v, info=None):",
        content,
    )

    # Replace values parameter with info.data
    content = re.sub(
        r"values\.get\(([^)]+)\)",
        r'info.data.get(\1) if info and hasattr(info, "data") else None',
        content,
    )

    # Replace values['key'] with info.data['key']
    content = re.sub(
        r"values\['([^']+)'\]",
        r"info.data['\1'] if info and hasattr(info, 'data') and '\1' in info.data else None",
        content,
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


# Fix the files
fix_validators_in_file(Path("app/models/cost_analysis.py"))
fix_validators_in_file(Path("app/models/optimization.py"))

print("✅ Fixed remaining Pydantic V2 validators")
