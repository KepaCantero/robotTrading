#!/usr/bin/env python3
"""
Deployment Management Scripts
TASK-7: Configuración de CI/CD pipeline
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
import requests
from botocore.exceptions import ClientError

from app.core.environment_config import get_config
from app.database import db_manager
from app.database.models import SystemLog
from app.database.repositories import SystemLogRepository


class DeploymentManager:
    """Manages deployment operations."""

    def __init__(self):
        self.config = get_config()
        self.ecs_client = boto3.client("ecs", region_name=self.config.api.api_host)
        self.elbv2_client = boto3.client("elbv2", region_name=self.config.api.api_host)

    def create_deployment_record(
        self,
        environment: str,
        version: str,
        commit: str,
        image_uri: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a deployment record."""
        try:
            session = db_manager.get_sync_session()
            log_repo = SystemLogRepository(SystemLog, session)

            deployment_data = {
                "environment": environment,
                "version": version,
                "commit": commit,
                "image_uri": image_uri,
                "metadata": metadata or {},
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat(),
            }

            log_repo.create(
                level="INFO",
                service="deployment",
                message=f"Deployment started: {environment} v{version}",
                metadata=deployment_data,
            )

            session.close()
            return deployment_data

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            print(f"Error creating deployment record: {e}")
            sys.exit(1)

    def update_deployment_status(
        self,
        environment: str,
        version: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update deployment status."""
        try:
            session = db_manager.get_sync_session()
            log_repo = SystemLogRepository(SystemLog, session)

            status_data = {
                "environment": environment,
                "version": version,
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            log_repo.create(
                level="INFO" if status == "success" else "ERROR",
                service="deployment",
                message=f"Deployment {status}: {environment} v{version}",
                metadata=status_data,
            )

            session.close()

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            print(f"Error updating deployment status: {e}")
            sys.exit(1)

    def get_service_status(self, cluster: str, service: str) -> Dict[str, Any]:
        """Get ECS service status."""
        try:
            response = self.ecs_client.describe_services(
                cluster=cluster, services=[service]
            )

            if not response["services"]:
                return {"error": "Service not found"}

            service_info = response["services"][0]
            return {
                "status": service_info["status"],
                "running_count": service_info["runningCount"],
                "desired_count": service_info["desiredCount"],
                "task_definition": service_info["taskDefinition"],
                "deployments": service_info["deployments"],
            }

        except ClientError as e:
            return {"error": str(e)}

    def get_load_balancer_health(self, load_balancer_name: str) -> Dict[str, Any]:
        """Get load balancer health status."""
        try:
            # Get load balancer ARN
            lb_response = self.elbv2_client.describe_load_balancers(
                Names=[load_balancer_name]
            )

            if not lb_response["LoadBalancers"]:
                return {"error": "Load balancer not found"}

            lb_arn = lb_response["LoadBalancers"][0]["LoadBalancerArn"]

            # Get target groups
            tg_response = self.elbv2_client.describe_target_groups(
                LoadBalancerArn=lb_arn
            )

            health_status = {}
            for tg in tg_response["TargetGroups"]:
                tg_arn = tg["TargetGroupArn"]

                # Get target health
                health_response = self.elbv2_client.describe_target_health(
                    TargetGroupArn=tg_arn
                )

                health_status[tg["TargetGroupName"]] = {
                    "targets": health_response["TargetHealthDescriptions"],
                    "healthy_count": len(
                        [
                            t
                            for t in health_response["TargetHealthDescriptions"]
                            if t["TargetHealth"]["State"] == "healthy"
                        ]
                    ),
                }

            return health_status

        except ClientError as e:
            return {"error": str(e)}

    def run_health_check(self, url: str, timeout: int = 30) -> bool:
        """Run health check against service."""
        try:
            response = requests.get(f"{url}/health", timeout=timeout)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def run_smoke_tests(self, base_url: str) -> bool:
        """Run smoke tests against deployed service."""
        try:
            # Basic health check
            if not self.run_health_check(base_url):
                return False

            # API endpoints check
            endpoints = [
                "/health",
                "/api/v1/portfolios",
                "/api/v1/assets",
                "/api/v1/strategies",
            ]

            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    if response.status_code not in [
                        200,
                        401,
                        403,
                    ]:  # 401/403 are OK for protected endpoints
                        print(
                            f"Endpoint {endpoint} returned status {response.status_code}"
                        )
                        return False
                except requests.RequestException as e:
                    print(f"Error testing endpoint {endpoint}: {e}")
                    return False

            return True

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            print(f"Error running smoke tests: {e}")
            return False


def main():
    """Main function for deployment scripts."""
    parser = argparse.ArgumentParser(description="Deployment Management Script")
    parser.add_argument(
        "--environment", required=True, help="Environment (staging/production)"
    )
    parser.add_argument("--version", required=True, help="Version to deploy")
    parser.add_argument("--commit", required=True, help="Git commit hash")
    parser.add_argument("--image", help="Docker image URI")
    parser.add_argument(
        "--status", help="Deployment status (in_progress/success/failed)"
    )
    parser.add_argument(
        "--action", choices=["create", "update", "status", "health"], required=True
    )

    args = parser.parse_args()

    deployment_manager = DeploymentManager()

    if args.action == "create":
        if not args.image:
            print("Error: --image is required for create action")
            sys.exit(1)

        metadata = {
            "git_ref": os.getenv("GITHUB_REF", ""),
            "workflow_run": os.getenv("GITHUB_RUN_ID", ""),
            "actor": os.getenv("GITHUB_ACTOR", ""),
        }

        result = deployment_manager.create_deployment_record(
            environment=args.environment,
            version=args.version,
            commit=args.commit,
            image_uri=args.image,
            metadata=metadata,
        )

        print(json.dumps(result, indent=2))

    elif args.action == "update":
        if not args.status:
            print("Error: --status is required for update action")
            sys.exit(1)

        metadata = {
            "completed_at": datetime.utcnow().isoformat(),
            "workflow_run": os.getenv("GITHUB_RUN_ID", ""),
        }

        deployment_manager.update_deployment_status(
            environment=args.environment,
            version=args.version,
            status=args.status,
            metadata=metadata,
        )

        print(f"Deployment status updated to: {args.status}")

    elif args.action == "status":
        cluster_name = f"algotrading-{args.environment}"
        service_name = f"algotrading-api-{args.environment}"

        status = deployment_manager.get_service_status(cluster_name, service_name)
        print(json.dumps(status, indent=2))

    elif args.action == "health":
        lb_name = f"algotrading-{args.environment}-lb"

        health = deployment_manager.get_load_balancer_health(lb_name)
        print(json.dumps(health, indent=2))


if __name__ == "__main__":
    main()
