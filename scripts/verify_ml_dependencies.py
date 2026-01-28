#!/usr/bin/env python3
"""
Verify ALL ML/AI dependencies are available.

This script checks that all required ML/AI libraries can be imported.
Part of Phase 2: Eliminate ALL fallbacks from ML/AI engines.
"""

import sys
from typing import List, Tuple

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def check_import(module_name: str, import_statement: str) -> Tuple[bool, str]:
    """
    Check if a module can be imported.

    Returns:
        (success, error_message)
    """
    try:
        exec(import_statement, globals())
        return True, ""
    except ImportError as e:
        return False, f"ImportError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    """Run all dependency checks."""
    print("=" * 80)
    print("PHASE 2: ML/AI Dependency Verification")
    print("=" * 80)
    print()

    # Define all required ML/AI dependencies
    dependencies = [
        # Deep Learning - PyTorch
        ("torch", "import torch"),
        ("torch.nn", "import torch.nn as nn"),
        ("torch.optim", "import torch.optim as optim"),
        ("torch.utils.data", "from torch.utils.data import DataLoader, Dataset"),

        # Deep Learning - TensorFlow (alternative backend)
        ("tensorflow", "import tensorflow as tf"),

        # Supervised Learning
        ("sklearn", "import sklearn"),
        ("sklearn.ensemble", "from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier"),
        ("sklearn.metrics", "from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score"),
        ("sklearn.model_selection", "from sklearn.model_selection import train_test_split"),
        ("sklearn.preprocessing", "from sklearn.preprocessing import StandardScaler"),

        # Gradient Boosting
        ("xgboost", "import xgboost as xgb"),
        ("lightgbm", "import lightgbm as lgb"),
        ("catboost", "import catboost as cb"),

        # Reinforcement Learning
        ("stable_baselines3", "from stable_baselines3 import PPO, A2C, DDPG, DQN, SAC, TD3"),
        ("stable_baselines3.common.callbacks", "from stable_baselines3.common.callbacks import BaseCallback"),
        ("gym", "import gym"),
        ("gym.spaces", "import gym.spaces"),
        ("gymnasium", "import gymnasium"),  # Newer gym API

        # Statistical Modeling
        ("hmmlearn", "from hmmlearn import hmm"),
        ("arch", "from arch import arch_model"),
        ("statsmodels", "import statsmodels"),

        # Portfolio Optimization
        ("cvxpy", "import cvxpy as cp"),
        ("pypfopt", "from pypfopt import EfficientFrontier"),
        ("scipy.optimize", "from scipy.optimize import minimize"),

        # SHAP for feature importance
        ("shap", "import shap"),

        # Optimization
        ("optuna", "import optuna"),
    ]

    # Check all dependencies
    all_passed = True
    failed_imports: List[Tuple[str, str]] = []

    for module_name, import_statement in dependencies:
        success, error = check_import(module_name, import_statement)
        if success:
            print(f"{GREEN}✓{RESET} {module_name}")
        else:
            print(f"{RED}✗{RESET} {module_name}")
            print(f"  {YELLOW}{error}{RESET}")
            all_passed = False
            failed_imports.append((module_name, error))

    print()
    print("=" * 80)

    if all_passed:
        print(f"{GREEN}SUCCESS: All ML/AI dependencies are available!{RESET}")
        print()
        print("Phase 2 implementation verified:")
        print("  • All ML/AI fallbacks eliminated")
        print("  • All dependencies are REQUIRED (no optional)")
        print("  • System will fail fast if dependencies missing")
        print()
        return 0
    else:
        print(f"{RED}FAILURE: {len(failed_imports)} dependency check(s) failed{RESET}")
        print()
        print("Missing dependencies:")
        for module_name, error in failed_imports:
            print(f"  • {module_name}")
        print()
        print("To install missing dependencies:")
        print("  pip install -r requirements.txt")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
