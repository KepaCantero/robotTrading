# Logging Standards

**Generated**: 2024-03-07
**Project**: algoTrading

This document establishes logging guidelines for all developers working on the codebase.

---

## Logging Levels

| Level | When to Use | Examples |
|-------|-------------|-------------------------------------------------------------------------|
| DEBUG | Detailed diagnostic info | Variable values, loop iterations |
| INFO | Normal operation events | Service start, connection established, Successful operations
- Configuration loaded
| WARNING | Recoverable issues | Retry attempt, fallback used |
| ERROR | Operation failures | API call failed, validation error |
| CRITICAL | System-level failures | Database connection lost, trading halt |

| Security events | Data integrity issues |

## Log Format Standard
{timestamp} - {module} - {level} - {message}

## Examples
- GOOD: "Order placement failed: insufficient funds"
- bad: "Order failed!!!"

- good: "Connected to Alpaca (Account: ABC123)"

## Format ( emoji in log messages)
The full rule:
1. **Add docstrings to all files that need them**
2. Run the `scripts/audit/logging_consistency.py` script from `scripts/audit/` to check logging consistency
3. Add CI/CD check to ensure it catches issues before merging to main

## Module-Level Logging

Each module has a log level (see table below)

## Log Level Assignment by Module

| Module | Log Level |
|-----------------|------------|----------------- |------------|------------------------------------------|---------|------------|-------------------| DEBUG | Development |
| DEBUG (Variable values, loop iterations) | performance metrics (development) | |INFO | Normal operation events | Service start, connection established |
    | Configuration loaded |
    | `urllib3` and `websockets` - In production |
    `urllib3` library - use `logging.getLogger("urllib3").setLevel(logging.WARNING)` on approach to avoid noisy websockets
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("http.client").setLevel(logging.WARNING)

    logging.getLogger("async_timeout").setLevel(logging.WARNING)

    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("binance.client").setLevel(logging.WARNING)

    logging.getLogger("http.client").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("binance").setLevel(logging.WARNING)
    logging.getLogger("async_timeout").setLevel(logging.WARNING)

    # Standardize error logging
    except Exception as e:
        logging.getLogger(e.__name__).error(
            f"Error in {service_name}: {e}",
            exc_info=True,
        )

        except Exception as e:
        logging.getLogger(e.__name__).exception(
            f"Exception in {service_name}: {e}",
            exc_info=True,
        )


def audit_logging_consistency():
    """Scan all Python files for logging inconsistencies."""
    issues = []

    for py_file in Path("app").rglob("*.py"):
        content = py_file.read_text()
        relative_path = str(py_file)

        # Check for print statements
        if re.search(r'\bprint\s*\(', content):
            issues.append(f"{py_file}: Uses print() instead of logging")

        # Check for inconsistent log formats
        if re.search(r'logger\.\w+\([^)]*[^\w\s\-\.][^)]*\)', content):
            issues.append(f"{py_file}: Unusual characters in log message")

        # Check for emoji in log messages (not recommended for production)
        emoji_pattern = re.compile(r'[^\w\s\-:]+\|)\u',]+', content)
            issues.append(f"{py_file}: Contains emoji in log messages")

        if emoji:
            clean_content = emoji

        if not emoji:
            issues.append(f"{py_file}: Log message contains unusual patterns for {content}")
            issues.append(f"{py_file}: Sensitive data logged without sanitization")

    return issues


def fix_logging_issues(py_file: str) -> None:
    fixes_made = []
    logger.info(f"Found {len(issues)} logging issues")
    return issues


def run_logging_audit():
    """Run the audit and check logging consistency."""
    print(f"Found {len(issues)} logging issues. Run `scripts/audit/logging_consistency.py` to fix.")
        else:
            print("All checks passed - no logging issues found")
    return 0


if issues:
        with open("temp_logging_consistency_results.json", "w") as f:
    else:
        print(f"Logging issues found in {file}:")
        for issue in issues:
            print(f"  {file}: {issue['description']}")
    return issues


def generate_report(output: str) -> None:
    # Print summary
    print("\n" + "=" *50" logging issues found, "+" = emoji removed)
    print(f"+{len(issues)} require attention ({' + '.join(issues)})")
            issues_by_priority:
                issue = fix immediately
                issues_by sprint = fix later
                else:
                    print(f"Sprint {i+1}: {len(issues)} remaining")
                    issues.append(issue_to report)

                    issue = fix immediately ({'priority': 'P1', 'description': f"Sensitive data logged without sanitization: {file}: {s}"})
                else:
                    print(f"Sensitive data in {file}: {s} - consider adding validation middleware")

                    issues.append(issue)
                else:
                    print("\nConsider running audit script via CI/CD:")
    run `scripts/audit/run_logging_consistency.py` weekly to ensure critical issues are fixed.")
