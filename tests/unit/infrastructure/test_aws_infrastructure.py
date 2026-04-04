"""
Tests for AWS Infrastructure Configuration
TASK-1: Configuración base de AWS
"""

from pathlib import Path

import pytest
import yaml


class TestAWSInfrastructureConfig:
    """Test AWS infrastructure configuration files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_path = Path("config/aws_infrastructure.yaml")
        self.terraform_path = Path("infrastructure/terraform/main.tf")
        self.user_data_path = Path("infrastructure/terraform/user_data.sh")

    def test_aws_config_file_exists(self):
        """Test that AWS configuration file exists."""
        assert self.config_path.exists(), "AWS infrastructure config file should exist"

    def test_terraform_file_exists(self):
        """Test that Terraform main file exists."""
        assert self.terraform_path.exists(), "Terraform main.tf file should exist"

    def test_user_data_script_exists(self):
        """Test that user data script exists."""
        assert self.user_data_path.exists(), "User data script should exist"

    def test_aws_config_structure(self):
        """Test AWS configuration file structure."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Required top-level keys
        required_keys = [
            "region",
            "environment",
            "project_name",
            "version",
            "vpc",
            "ec2",
            "rds",
            "elasticache",
            "security_groups",
            "iam",
        ]

        for key in required_keys:
            assert key in config, f"Required key '{key}' missing from config"

    def test_vpc_configuration(self):
        """Test VPC configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        vpc = config["vpc"]

        assert vpc["name"] == "algo-trading-vpc"
        assert vpc["cidr_block"] == "10.0.0.0/16"
        assert len(vpc["availability_zones"]) == 2
        assert len(vpc["public_subnets"]) == 2
        assert len(vpc["private_subnets"]) == 2

    def test_ec2_configuration(self):
        """Test EC2 configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        ec2 = config["ec2"]

        assert ec2["instance_type"] == "t3.medium"
        assert "security_groups" in ec2
        assert "user_data" in ec2
        assert len(ec2["security_groups"]) >= 2

    def test_rds_configuration(self):
        """Test RDS configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        rds = config["rds"]

        assert rds["engine"] == "postgres"
        assert rds["engine_version"] == "15.4"
        assert rds["instance_class"] == "db.t3.micro"
        assert rds["allocated_storage"] == 20
        assert rds["database_name"] == "algotrading"
        assert rds["port"] == 5432

    def test_elasticache_configuration(self):
        """Test ElastiCache configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        elasticache = config["elasticache"]

        assert elasticache["engine"] == "redis"
        assert elasticache["engine_version"] == "7.0"
        assert elasticache["node_type"] == "cache.t3.micro"
        assert elasticache["port"] == 6379

    def test_security_groups_configuration(self):
        """Test security groups configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        security_groups = config["security_groups"]

        required_sgs = ["web_sg", "ssh_sg", "db_sg", "cache_sg"]
        for sg in required_sgs:
            assert sg in security_groups, f"Security group '{sg}' missing"

        # Test web security group
        web_sg = security_groups["web_sg"]
        assert web_sg["name"] == "algo-trading-web-sg"
        assert len(web_sg["ingress"]) >= 3  # HTTP, HTTPS, App port

    def test_iam_configuration(self):
        """Test IAM configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        iam = config["iam"]

        assert "ec2_role" in iam
        ec2_role = iam["ec2_role"]
        assert ec2_role["name"] == "algo-trading-ec2-role"
        assert len(ec2_role["policies"]) >= 2

    def test_terraform_syntax(self):
        """Test Terraform file syntax."""
        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Basic Terraform syntax checks
        assert "terraform {" in terraform_content
        assert 'provider "aws"' in terraform_content
        assert 'resource "aws_vpc"' in terraform_content
        assert 'resource "aws_instance"' in terraform_content
        assert 'resource "aws_db_instance"' in terraform_content
        assert 'resource "aws_elasticache_replication_group"' in terraform_content

    def test_user_data_script_content(self):
        """Test user data script content."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check for essential commands
        assert "yum update -y" in user_data
        assert "yum install -y docker" in user_data
        assert "systemctl start docker" in user_data
        assert "python3" in user_data
        assert "docker-compose" in user_data
        assert "aws" in user_data

    def test_deployment_script_exists(self):
        """Test that deployment script exists."""
        deploy_script = Path("scripts/deploy_aws.sh")
        assert deploy_script.exists(), "Deployment script should exist"

    def test_destruction_script_exists(self):
        """Test that destruction script exists."""
        destroy_script = Path("scripts/destroy_aws.sh")
        assert destroy_script.exists(), "Destruction script should exist"

    def test_deployment_script_executable(self):
        """Test that deployment script is executable."""
        deploy_script = Path("scripts/deploy_aws.sh")
        assert deploy_script.exists()

        # Check if script has proper shebang
        with open(deploy_script) as f:
            content = f.read()
            assert content.startswith("#!/bin/bash")

    def test_destruction_script_executable(self):
        """Test that destruction script is executable."""
        destroy_script = Path("scripts/destroy_aws.sh")
        assert destroy_script.exists()

        # Check if script has proper shebang
        with open(destroy_script) as f:
            content = f.read()
            assert content.startswith("#!/bin/bash")

    def test_configuration_consistency(self):
        """Test configuration consistency across files."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Check that project name is consistent
        project_name = config["project_name"]
        assert project_name in terraform_content

        # Check that region is consistent
        region = config["region"]
        assert region in terraform_content

    def test_security_best_practices(self):
        """Test security best practices in configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check that database is in private subnets
        rds = config["rds"]
        assert "vpc_security_groups" in rds
        assert "subnet_group" in rds

        # Check that cache is in private subnets
        elasticache = config["elasticache"]
        assert "subnet_group" in elasticache
        assert "security_groups" in elasticache

        # Check encryption settings
        assert elasticache.get("at_rest_encryption_enabled", False) or elasticache.get(
            "transit_encryption_enabled", False
        )

    def test_monitoring_configuration(self):
        """Test monitoring configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check CloudWatch configuration
        assert "cloudwatch" in config
        cloudwatch = config["cloudwatch"]
        assert "log_groups" in cloudwatch
        assert len(cloudwatch["log_groups"]) >= 3

    def test_backup_configuration(self):
        """Test backup configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check RDS backup settings
        rds = config["rds"]
        assert rds["backup_retention_period"] >= 7
        assert "backup_window" in rds

        # Check ElastiCache backup settings
        elasticache = config["elasticache"]
        assert elasticache["backup_retention_limit"] >= 7
        assert "backup_window" in elasticache

    def test_scalability_considerations(self):
        """Test scalability considerations."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check that RDS has max allocated storage
        rds = config["rds"]
        assert rds["max_allocated_storage"] > rds["allocated_storage"]

        # Check that instance types are reasonable for MVP
        ec2 = config["ec2"]
        assert ec2["instance_type"] in ["t3.medium", "t3.large", "t3.xlarge"]

    def test_cost_optimization(self):
        """Test cost optimization settings."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check that multi-AZ is disabled for MVP
        rds = config["rds"]
        assert not rds.get("multi_az", True)  # Should be False for MVP

        # Check that automatic failover is disabled for MVP
        elasticache = config["elasticache"]
        assert not elasticache.get("automatic_failover_enabled", True)  # Should be False for MVP

    def test_environment_variables(self):
        """Test environment variable configuration."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check that environment variables are properly set
        assert "DATABASE_URL=" in user_data
        assert "REDIS_URL=" in user_data
        assert "ENVIRONMENT=" in user_data
        assert "AWS_REGION=" in user_data

    def test_logging_configuration(self):
        """Test logging configuration."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check CloudWatch agent configuration
        assert "amazon-cloudwatch-agent" in user_data
        assert "amazon-cloudwatch-agent.json" in user_data

        # Check log rotation
        assert "logrotate" in user_data

    def test_health_checks(self):
        """Test health check configuration."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check that health checks are configured
        assert "healthcheck" in user_data
        assert "/health" in user_data

    def test_monitoring_scripts(self):
        """Test monitoring scripts."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check monitoring script creation
        assert "monitor.sh" in user_data
        assert "crontab" in user_data

        # Check backup script creation
        assert "backup.sh" in user_data

    def test_service_configuration(self):
        """Test systemd service configuration."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check systemd service creation
        assert "systemd/system" in user_data
        assert "algo-trading.service" in user_data
        assert "systemctl enable" in user_data

    def test_ssl_configuration(self):
        """Test SSL configuration placeholder."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check nginx SSL configuration
        assert "ssl" in user_data
        assert "443" in user_data

    def test_file_permissions(self):
        """Test file permissions configuration."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check that proper permissions are set
        assert "chmod" in user_data
        assert "chown" in user_data

    def test_error_handling(self):
        """Test error handling in scripts."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check that error handling is in place
        assert "set -e" in user_data or "set -o errexit" in user_data or "exec > >(tee" in user_data

    def test_resource_cleanup(self):
        """Test resource cleanup configuration."""
        with open(self.user_data_path) as f:
            user_data = f.read()

        # Check that cleanup is configured
        assert "rm" in user_data
        assert "cleanup" in user_data or "clean" in user_data or "backup" in user_data

    def test_configuration_validation(self):
        """Test configuration validation."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Validate numeric values
        assert isinstance(config["vpc"]["cidr_block"], str)
        assert isinstance(config["ec2"]["instance_type"], str)
        assert isinstance(config["rds"]["allocated_storage"], int)
        assert isinstance(config["elasticache"]["port"], int)

        # Validate that ports are in valid range
        assert 1 <= config["rds"]["port"] <= 65535
        assert 1 <= config["elasticache"]["port"] <= 65535

    def test_terraform_outputs(self):
        """Test Terraform outputs configuration."""
        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Check that important outputs are defined
        assert 'output "vpc_id"' in terraform_content
        assert 'output "ec2_public_ip"' in terraform_content
        assert 'output "rds_endpoint"' in terraform_content
        assert 'output "redis_endpoint"' in terraform_content

    def test_terraform_variables(self):
        """Test Terraform variables configuration."""
        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Check that important variables are defined
        assert 'variable "aws_region"' in terraform_content
        assert 'variable "environment"' in terraform_content
        assert 'variable "project_name"' in terraform_content
        assert 'variable "instance_type"' in terraform_content

    def test_terraform_backend(self):
        """Test Terraform backend configuration."""
        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Check that backend is configured
        assert 'backend "s3"' in terraform_content
        assert "bucket" in terraform_content
        assert "key" in terraform_content
        assert "region" in terraform_content

    def test_terraform_provider(self):
        """Test Terraform provider configuration."""
        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Check that AWS provider is configured
        assert 'provider "aws"' in terraform_content
        assert "required_providers" in terraform_content
        assert "hashicorp/aws" in terraform_content

    def test_terraform_required_version(self):
        """Test Terraform required version."""
        with open(self.terraform_path) as f:
            terraform_content = f.read()

        # Check that required version is specified
        assert "required_version" in terraform_content
        assert ">= 1.0" in terraform_content

    def test_configuration_completeness(self):
        """Test that configuration is complete."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        # Check that all required sections have content
        for section in ["vpc", "ec2", "rds", "elasticache", "security_groups", "iam"]:
            assert config[section], f"Section '{section}' should not be empty"

    def test_configuration_readability(self):
        """Test that configuration is readable and well-formatted."""
        with open(self.config_path) as f:
            content = f.read()

        # Check that file is properly formatted YAML
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Configuration file is not valid YAML: {e}")

    def test_terraform_readability(self):
        """Test that Terraform file is readable."""
        with open(self.terraform_path) as f:
            content = f.read()

        # Basic syntax checks
        assert content.count("{") == content.count("}"), "Unmatched braces in Terraform file"
        assert content.count("[") == content.count("]"), "Unmatched brackets in Terraform file"

    def test_script_readability(self):
        """Test that scripts are readable."""
        scripts = [
            "scripts/deploy_aws.sh",
            "scripts/destroy_aws.sh",
            "infrastructure/terraform/user_data.sh",
        ]

        for script_path in scripts:
            script_file = Path(script_path)
            if script_file.exists():
                with open(script_file) as f:
                    content = f.read()
                    assert len(content) > 0, f"Script {script_path} should not be empty"
                    assert (
                        "#!/bin/bash" in content
                    ), f"Script {script_path} should have bash shebang"
