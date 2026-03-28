#!/usr/bin/env python3
"""
Pydantic V2 Migration Script
Testing Reviewer Audit - Phase 1: Critical Fixes
"""

import re
from pathlib import Path


def migrate_pydantic_v2_file(file_path: Path) -> bool:
    """Migrate a single file from Pydantic V1 to V2."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Replace imports
        content = re.sub(
            r"from pydantic import ([^,]*,\s*)?validator",
            r"from pydantic import \1field_validator",
            content,
        )

        # Replace @validator with @field_validator
        content = re.sub(
            r"@validator\(([^)]+)\)\s*\n\s*def (\w+)\(cls, v\):",
            r"@field_validator(\1)\n    @classmethod\n    def \2(cls, v):",
            content,
        )

        # Replace Config class with model_config
        content = re.sub(
            r'class Config:\s*\n\s*env_file = "([^"]+)"\s*\n\s*env_file_encoding = [\'"]([^\'"]+)[\'"]\s*\n\s*case_sensitive = (True|False)',
            r'model_config = {\n        "env_file": "\1",\n        "env_file_encoding": "\2",\n        "case_sensitive": \3\n    }',
            content,
        )

        # Replace Field with env parameter
        content = re.sub(r'Field\(([^)]*),\s*env="([^"]+)"([^)]*)\)', r"Field(\1\3)", content)

        # Add env parameter separately
        field_pattern = r"(\w+):\s*(\w+)\s*=\s*Field\(([^)]*)\)"
        env_pattern = r'Field\(([^)]*),\s*env="([^"]+)"([^)]*)\)'

        def add_env_to_field(match):
            field_name = match.group(1)
            field_type = match.group(2)
            field_args = match.group(3)

            # Check if env parameter exists
            if "env=" in field_args:
                return match.group(0)

            # Add env parameter
            if field_args.strip():
                new_args = f'{field_args}, env="{field_name.upper()}"'
            else:
                new_args = f'env="{field_name.upper()}"'

            return f"{field_name}: {field_type} = Field({new_args})"

        content = re.sub(field_pattern, add_env_to_field, content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
        print(f"Error migrating {file_path}: {e}")
        return False


def migrate_all_pydantic_files():
    """Migrate all Pydantic files in the project."""
    project_root = Path(".")

    # Find all Python files
    python_files = []
    for pattern in ["**/*.py"]:
        python_files.extend(project_root.glob(pattern))

    migrated_files = []

    for file_path in python_files:
        # Skip test files and __pycache__
        if "test" in str(file_path) or "__pycache__" in str(file_path):
            continue

        # Check if file contains Pydantic V1 patterns
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if "@validator" in content or "class Config:" in content:
                if migrate_pydantic_v2_file(file_path):
                    migrated_files.append(file_path)
                    print(f"✅ Migrated: {file_path}")
                else:
                    print(f"ℹ️  No changes needed: {file_path}")

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            print(f"❌ Error processing {file_path}: {e}")

    print(f"\n🎉 Migration complete! {len(migrated_files)} files migrated.")
    return migrated_files


if __name__ == "__main__":
    migrate_all_pydantic_files()
