#!/usr/bin/env python3
"""Create a deployment record in the database."""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_deployment_record(environment: str, version: str, commit: str, image: str) -> dict:
    """Create a deployment record."""
    record = {
        "environment": environment,
        "version": version,
        "commit": commit,
        "image": image,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "status": "deploying",
    }

    logger.info(
        "Deployment record created: env=%s version=%s commit=%s",
        environment,
        version,
        commit,
    )
    return record


def main():
    parser = argparse.ArgumentParser(description="Create deployment record")
    parser.add_argument("--environment", required=True, help="Deployment environment")
    parser.add_argument("--version", required=True, help="Version being deployed")
    parser.add_argument("--commit", required=True, help="Git commit SHA")
    parser.add_argument("--image", required=True, help="Docker image URI")
    args = parser.parse_args()

    record = create_deployment_record(
        environment=args.environment,
        version=args.version,
        commit=args.commit,
        image=args.image,
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
