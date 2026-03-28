#!/usr/bin/env python3
"""
Script para ejecutar validación de integridad del sistema.

Ejecuta todas las validaciones y genera el dashboard state JSON.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.system.verify_system_integrity import SystemIntegrityValidator

if __name__ == "__main__":
    validator = SystemIntegrityValidator()
    results = validator.validate_all()

    # Exit code based on status
    exit_code = 0 if results["overall_status"] in ["ok", "warning"] else 1
    sys.exit(exit_code)
