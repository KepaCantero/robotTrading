#!/usr/bin/env python3
"""
Phase 5b: Manual fixes for remaining ImportError fallbacks

Handles the 18 remaining complex fallback patterns that the automated
script couldn't handle properly.

Author: Backend Developer
Date: 2026-01-28
"""

from pathlib import Path

PROJECT_ROOT = Path("/Users/kepa.cantero/Projects/algoTrading")

# Manual fixes for specific files
MANUAL_FIXES = {
    "app/backtesting/seasonality_analyzer.py": [
        {
            "search": "            except ImportError:\n                logger.warning(\"statsmodels not available, skipping decomposition\")\n                return None",
            "replace": "",  # Remove the fallback
            "add_import": "from statsmodels.tsa.seasonal import seasonal_decompose"
        }
    ],
    "app/backtesting/comprehensive_backtest_runner.py": [
        {
            "search": "                except ImportError:\n                    logger.warning(\"HMM detector not available, falling back to clustering\")\n                    detection_method = 'clustering'\n                except Exception as e:\n                    logger.warning(f\"HMM detection error: {e}, falling back to clustering\")\n                    detection_method = 'clustering'",
            "replace": "                # HMM required - fail fast if not available",
            "add_import": "from app.engines.context_engine.regime_detectors.hmm_regime_detector import HMMRegimeDetector"
        }
    ],
    "app/strategies/momentum_modular/learning/learning_updater.py": [
        {
            "search": "        except ImportError as e:",
            "replace": "",  # Remove fallback
            "context": "Reinforcement learning imports required"
        }
    ],
    "app/strategies/factory.py": [
        {
            "search": "        except ImportError as e:",
            "replace": "",  # Multiple fallbacks to remove
        }
    ],
    "app/engines/risk_engine/alert_system.py": [
        {
            "search": "        except ImportError:\n            self.logger.warning(\"requests no disponible para Slack\")",
            "replace": "",  # Remove fallback
            "add_import": "import requests"
        }
    ],
    "app/engines/risk_engine/__init__.py": [
        {
            "search": "except ImportError:",
            "replace": "",  # Remove empty except blocks
        }
    ],
    "app/engines/risk_engine/var_calculators/var_calculators.py": [
        {
            "search": "        except ImportError:\n            self.logger.warning(\"scipy no disponible. Usando aproximación básica.\")",
            "replace": "",  # Remove fallback - scipy is required
        },
        {
            "search": "        except ImportError:\n            calculator = ParametricVaRCalculator(self.config)\n            return calculator.calculate_var(returns, portfolio_value)",
            "replace": "",  # Remove fallback - arch is required
        }
    ],
    "app/engines/data_engine/sources/ohlcv_sources.py": [
        {
            "search": "        except ImportError:",
            "replace": "",  # Remove fallback - ib_insync required
        }
    ],
    "app/api/health.py": [
        {
            "search": "        except ImportError:",
            "replace": "",  # Remove fallback
        }
    ],
    "app/services/metrics_database/questdb_connector.py": [
        {
            "search": "            except ImportError:",
            "replace": "",  # Remove fallback
        }
    ],
    "app/services/live_trading/broker_adapters/alpaca_client.py": [
        {
            "search": "        except ImportError:",
            "replace": "",  # Remove fallback
        }
    ],
    "app/services/backtesting_orchestration/backtest_orchestrator.py": [
        {
            "search": "    except ImportError:",
            "replace": "",  # Remove fallback
        }
    ],
}


def apply_fixes():
    """Apply all manual fixes."""

    print("=" * 80)
    print("PHASE 5b: MANUAL FIXES FOR REMAINING FALLBACKS")
    print("=" * 80)
    print()

    fixed_count = 0

    for file_path, fixes in MANUAL_FIXES.items():
        full_path = PROJECT_ROOT / file_path

        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        print(f"Processing: {file_path}")

        try:
            content = full_path.read_text()
            original_content = content

            for fix in fixes:
                search = fix.get("search")
                replace = fix.get("replace", "")

                if search and search in content:
                    content = content.replace(search, replace)
                    print(f"  ✅ Applied fix: {search[:50]}...")
                    fixed_count += 1

                # Add import if specified
                if "add_import" in fix:
                    import_line = fix["add_import"]
                    # Find the last import line and add after it
                    lines = content.split('\n')
                    import_idx = -1

                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            import_idx = i

                    if import_idx >= 0:
                        lines.insert(import_idx + 1, import_line)
                        content = '\n'.join(lines)
                        print(f"  ✅ Added import: {import_line}")

            if content != original_content:
                full_path.write_text(content)
                print(f"  💾 Saved changes")
            else:
                print(f"  ℹ️  No changes needed")

        except Exception as e:
            print(f"  ❌ Error: {e}")

        print()

    print("=" * 80)
    print(f"Total fixes applied: {fixed_count}")
    print("=" * 80)


if __name__ == "__main__":
    apply_fixes()
