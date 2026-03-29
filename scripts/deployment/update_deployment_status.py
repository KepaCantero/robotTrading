#!/usr/bin/env python3
"""Update deployment status in the database."""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_deployment_status(environment: str, version: str, status: str) -> dict:
    """Update deployment status."""
    record = {
        "environment": environment,
        "version": version,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Deployment status updated: env=%s version=%s status=%s",
        environment,
        version,
        status,
    )
    return record


def main():
    parser = argparse.ArgumentParser(description="Update deployment status")
    parser.add_argument("--environment", required=True, help="Deployment environment")
    parser.add_argument("--version", required=True, help="Version being deployed")
    parser.add_argument(
        "--status",
        required=True,
        choices=["success", "failed", "rolling_back"],
        help="Deployment status",
    )
    args = parser.parse_args()

    record = update_deployment_status(
        environment=args.environment,
        version=args.version,
        status=args.status,
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
