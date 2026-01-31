"""
Security test configuration - isolated from main app imports
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Simple pytest configuration without importing from app/main
import pytest


@pytest.fixture
def sample_secrets():
    """Sample secrets for testing."""
    return {
        "STRONG_SECRET": "Abc123!@#Xyz789$%^Def456&*()Ghi012",
        "WEAK_SECRET": "password",
        "SHORT_SECRET": "Ab1!",
        "NO_SPECIAL": "abcdefghijk123456789",
    }
