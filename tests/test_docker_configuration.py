"""
Tests for Docker Configuration and Deployment
TASK-2: Dockerización completa
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestDockerConfiguration:
    """Test Docker configuration files and setup."""

    def setup_method(self):
        """Set up test fixtures."""
        self.dockerfile_path = Path("Dockerfile")
        self.docker_compose_dev_path = Path("docker-compose.dev.yml")
        self.docker_compose_prod_path = Path("docker-compose.prod.yml")
        self.nginx_dev_path = Path("nginx/nginx-dev.conf")
        self.nginx_prod_path = Path("nginx/nginx-prod.conf")
        self.prometheus_path = Path("monitoring/prometheus.yml")
        self.prometheus_prod_path = Path("monitoring/prometheus-prod.yml")

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        assert self.dockerfile_path.exists(), "Dockerfile should exist"

    def test_docker_compose_files_exist(self):
        """Test that docker-compose files exist."""
        assert self.docker_compose_dev_path.exists(), "docker-compose.dev.yml should exist"
        assert self.docker_compose_prod_path.exists(), "docker-compose.prod.yml should exist"

    def test_nginx_configs_exist(self):
        """Test that nginx configuration files exist."""
        assert self.nginx_dev_path.exists(), "nginx-dev.conf should exist"
        assert self.nginx_prod_path.exists(), "nginx-prod.conf should exist"

    def test_monitoring_configs_exist(self):
        """Test that monitoring configuration files exist."""
        assert self.prometheus_path.exists(), "prometheus.yml should exist"
        assert self.prometheus_prod_path.exists(), "prometheus-prod.yml should exist"

    def test_dockerfile_content(self):
        """Test Dockerfile content."""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()

        # Check for multi-stage build
        assert 'FROM python:3.11-slim as builder' in content
        assert 'FROM python:3.11-slim as production' in content
        assert 'FROM production as development' in content

        # Check for security best practices
        assert 'USER algotrading' in content
        assert 'RUN groupadd -r algotrading' in content
        # Check for security environment variables
        assert 'PYTHONDONTWRITEBYTECODE=1' in content
        assert 'PYTHONUNBUFFERED=1' in content

        # Check for health check
        assert 'HEALTHCHECK' in content
        assert 'curl -f http://localhost:8000/health' in content

        # Check for proper port exposure
        assert 'EXPOSE 8000' in content

    def test_docker_compose_dev_structure(self):
        """Test development docker-compose structure."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for required services
        assert 'postgres:' in content
        assert 'redis:' in content
        assert 'app:' in content
        assert 'worker:' in content
        assert 'scheduler:' in content
        assert 'nginx:' in content
        assert 'flower:' in content
        assert 'prometheus:' in content
        assert 'grafana:' in content

        # Check for development-specific configurations
        assert ('target: development' in content or 'dockerfile: Dockerfile.dev' in content)
        assert 'DEBUG: "true"' in content
        assert 'LOG_LEVEL: DEBUG' in content

    def test_docker_compose_prod_structure(self):
        """Test production docker-compose structure."""
        with open(self.docker_compose_prod_path, 'r') as f:
            content = f.read()

        # Check for required services
        assert 'app:' in content
        assert 'worker:' in content
        assert 'scheduler:' in content
        assert 'nginx:' in content
        assert 'prometheus:' in content
        assert 'grafana:' in content
        assert 'elasticsearch:' in content
        assert 'logstash:' in content
        assert 'kibana:' in content

        # Check for production-specific configurations
        assert 'target: production' in content
        assert 'DEBUG: "false"' in content
        assert 'LOG_LEVEL: INFO' in content
        assert 'deploy:' in content
        assert 'resources:' in content

    def test_nginx_dev_config(self):
        """Test nginx development configuration."""
        with open(self.nginx_dev_path, 'r') as f:
            content = f.read()

        # Check for basic nginx configuration
        assert 'events {' in content
        assert 'http {' in content
        assert 'server {' in content
        assert 'listen 80;' in content

        # Check for upstream configuration
        assert 'upstream fastapi_backend' in content
        assert 'server app:8000;' in content

        # Check for proxy configuration
        assert 'proxy_pass http://fastapi_backend;' in content
        assert 'proxy_set_header Host $host;' in content

        # Check for health check endpoint
        assert 'location /health' in content

    def test_nginx_prod_config(self):
        """Test nginx production configuration."""
        with open(self.nginx_prod_path, 'r') as f:
            content = f.read()

        # Check for SSL configuration
        assert 'listen 443 ssl http2;' in content
        assert 'ssl_certificate' in content
        assert 'ssl_certificate_key' in content

        # Check for security headers
        assert 'Strict-Transport-Security' in content
        assert 'X-Frame-Options' in content
        assert 'X-Content-Type-Options' in content

        # Check for rate limiting
        assert 'limit_req_zone' in content
        assert 'limit_conn_zone' in content

        # Check for HTTP to HTTPS redirect
        assert 'return 301 https://$host$request_uri;' in content

    def test_prometheus_config(self):
        """Test Prometheus configuration."""
        with open(self.prometheus_path, 'r') as f:
            content = f.read()

        # Check for basic Prometheus configuration
        assert 'global:' in content
        assert 'scrape_interval: 15s' in content
        assert 'scrape_configs:' in content

        # Check for job configurations
        assert ('job_name: \'prometheus\'' in content or 'job_name: "prometheus"' in content)
        assert ('job_name: \'algotrading-app\'' in content or 'job_name: "algotrading-app"' in content)
        assert ('job_name: \'nginx\'' in content or 'job_name: "nginx"' in content)
        assert ('job_name: \'redis\'' in content or 'job_name: "redis"' in content)
        assert ('job_name: \'postgres\'' in content or 'job_name: "postgres"' in content)

    def test_prometheus_prod_config(self):
        """Test Prometheus production configuration."""
        with open(self.prometheus_prod_path, 'r') as f:
            content = f.read()

        # Check for production-specific configurations
        assert ('cluster: \'algotrading-prod\'' in content or 'cluster: "algotrading-prod"' in content)
        assert ('job_name: \'celery-workers\'' in content or 'job_name: "celery-workers"' in content)
        assert ('job_name: \'celery-beat\'' in content or 'job_name: "celery-beat"' in content)
        assert ('job_name: \'elasticsearch\'' in content or 'job_name: "elasticsearch"' in content)
        assert ('job_name: \'logstash\'' in content or 'job_name: "logstash"' in content)

    def test_dockerfile_security(self):
        """Test Dockerfile security best practices."""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()

        # Check for non-root user
        assert 'USER algotrading' in content
        assert 'groupadd -r algotrading' in content

        # Check for security environment variables
        assert 'PYTHONDONTWRITEBYTECODE=1' in content
        assert 'PYTHONUNBUFFERED=1' in content

        # Check for proper permissions
        assert 'chown -R algotrading:algotrading' in content

        # Check for health check
        assert 'HEALTHCHECK' in content

    def test_docker_compose_networks(self):
        """Test docker-compose network configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check for network configuration
        assert 'networks:' in dev_content
        assert 'networks:' in prod_content
        assert 'algotrading-network:' in dev_content
        assert 'algotrading-network:' in prod_content

    def test_docker_compose_volumes(self):
        """Test docker-compose volume configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check for volume configuration
        assert 'volumes:' in dev_content
        assert 'volumes:' in prod_content
        assert 'postgres_data:' in dev_content
        assert 'redis_data:' in dev_content
        assert 'app_logs:' in dev_content

    def test_docker_compose_healthchecks(self):
        """Test docker-compose health check configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for health check configurations
        assert 'healthcheck:' in content
        assert 'CMD-SHELL' in content
        assert 'redis-cli' in content
        assert 'curl' in content and 'http://localhost:8000/health' in content

    def test_docker_compose_dependencies(self):
        """Test docker-compose service dependencies."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for dependency configurations
        assert 'depends_on:' in content
        assert 'postgres:' in content
        assert 'redis:' in content
        assert 'condition: service_healthy' in content

    def test_docker_compose_environment_variables(self):
        """Test docker-compose environment variable configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for environment variable configurations
        assert 'environment:' in content
        assert 'DATABASE_URL:' in content
        assert 'REDIS_URL:' in content
        assert 'ENVIRONMENT:' in content
        assert 'DEBUG:' in content
        assert 'LOG_LEVEL:' in content

    def test_docker_compose_restart_policies(self):
        """Test docker-compose restart policy configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for restart policy configurations
        assert 'restart: unless-stopped' in content

    def test_docker_compose_resource_limits(self):
        """Test docker-compose resource limit configuration."""
        with open(self.docker_compose_prod_path, 'r') as f:
            content = f.read()

        # Check for resource limit configurations
        assert 'deploy:' in content
        assert 'resources:' in content
        assert 'limits:' in content
        assert 'memory:' in content
        assert 'cpus:' in content

    def test_docker_compose_replicas(self):
        """Test docker-compose replica configuration."""
        with open(self.docker_compose_prod_path, 'r') as f:
            content = f.read()

        # Check for replica configurations
        assert 'replicas: 2' in content

    def test_dockerfile_multi_stage_build(self):
        """Test Dockerfile multi-stage build configuration."""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()

        # Check for multi-stage build stages
        assert 'FROM python:3.11-slim as builder' in content
        assert 'FROM python:3.11-slim as production' in content
        assert 'FROM production as development' in content
        assert 'FROM development as testing' in content
        assert 'FROM production as worker' in content
        assert 'FROM worker as scheduler' in content

    def test_dockerfile_optimization(self):
        """Test Dockerfile optimization techniques."""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()

        # Check for optimization techniques
        assert 'COPY requirements.txt .' in content
        assert 'RUN pip install --no-cache-dir' in content
        assert 'COPY --from=builder' in content

    def test_docker_compose_logging(self):
        """Test docker-compose logging configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for logging configurations
        assert 'volumes:' in content
        assert 'app_logs:' in content

    def test_docker_compose_monitoring(self):
        """Test docker-compose monitoring configuration."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for monitoring service configurations
        assert 'prometheus:' in content
        assert 'grafana:' in content
        assert 'flower:' in content

    def test_docker_compose_production_monitoring(self):
        """Test docker-compose production monitoring configuration."""
        with open(self.docker_compose_prod_path, 'r') as f:
            content = f.read()

        # Check for production monitoring configurations
        assert 'elasticsearch:' in content
        assert 'logstash:' in content
        assert 'kibana:' in content

    def test_nginx_security_headers(self):
        """Test nginx security header configuration."""
        with open(self.nginx_prod_path, 'r') as f:
            content = f.read()

        # Check for security headers
        assert 'Strict-Transport-Security' in content
        assert 'X-Frame-Options' in content
        assert 'X-Content-Type-Options' in content
        assert 'X-XSS-Protection' in content
        assert 'Referrer-Policy' in content
        assert 'Content-Security-Policy' in content

    def test_nginx_rate_limiting(self):
        """Test nginx rate limiting configuration."""
        with open(self.nginx_prod_path, 'r') as f:
            content = f.read()

        # Check for rate limiting configurations
        assert 'limit_req_zone' in content
        assert 'limit_req zone=' in content
        assert 'limit_conn_zone' in content
        assert 'limit_conn ' in content

    def test_nginx_ssl_configuration(self):
        """Test nginx SSL configuration."""
        with open(self.nginx_prod_path, 'r') as f:
            content = f.read()

        # Check for SSL configurations
        assert 'ssl_protocols' in content
        assert 'ssl_ciphers' in content
        assert 'ssl_prefer_server_ciphers' in content
        assert 'ssl_session_cache' in content
        assert 'ssl_certificate' in content
        assert 'ssl_certificate_key' in content

    def test_docker_compose_file_syntax(self):
        """Test docker-compose file syntax."""
        # Test development compose file
        result = subprocess.run(
            ['docker-compose', '-f', str(self.docker_compose_dev_path), 'config'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Development docker-compose syntax error: {result.stderr}"

        # Test production compose file
        result = subprocess.run(
            ['docker-compose', '-f', str(self.docker_compose_prod_path), 'config'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Production docker-compose syntax error: {result.stderr}"

    def test_dockerfile_syntax(self):
        """Test Dockerfile syntax."""
        # Basic syntax check - check for common Dockerfile patterns
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()

        # Check for proper FROM statements
        assert content.count('FROM ') >= 6  # Multiple stages

        # Check for proper RUN statements
        assert 'RUN ' in content

        # Check for proper COPY statements
        assert 'COPY ' in content

        # Check for proper EXPOSE statements
        assert 'EXPOSE ' in content

        # Check for proper CMD statements
        assert 'CMD ' in content

    def test_docker_compose_service_names(self):
        """Test docker-compose service naming."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for proper service naming
        assert 'postgres:' in content
        assert 'redis:' in content
        assert 'app:' in content
        assert 'worker:' in content
        assert 'scheduler:' in content
        assert 'nginx:' in content

    def test_docker_compose_port_mappings(self):
        """Test docker-compose port mappings."""
        with open(self.docker_compose_dev_path, 'r') as f:
            content = f.read()

        # Check for port mappings
        assert 'ports:' in content
        assert '"5432:5432"' in content
        assert '"6379:6379"' in content
        assert '"8000:8000"' in content
        assert '"80:80"' in content
        assert '"443:443"' in content

    def test_docker_compose_environment_consistency(self):
        """Test docker-compose environment variable consistency."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files have similar environment variables
        assert 'DATABASE_URL:' in dev_content
        assert 'DATABASE_URL:' in prod_content
        assert 'REDIS_URL:' in dev_content
        assert 'REDIS_URL:' in prod_content
        assert 'ENVIRONMENT:' in dev_content
        assert 'ENVIRONMENT:' in prod_content

    def test_docker_compose_volume_consistency(self):
        """Test docker-compose volume consistency."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files have similar volume configurations
        assert 'volumes:' in dev_content
        assert 'volumes:' in prod_content
        assert 'app_logs:' in dev_content
        assert 'app_logs:' in prod_content

    def test_docker_compose_network_consistency(self):
        """Test docker-compose network consistency."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files have similar network configurations
        assert 'networks:' in dev_content
        assert 'networks:' in prod_content
        assert 'algotrading-network:' in dev_content
        assert 'algotrading-network:' in prod_content

    def test_docker_compose_restart_consistency(self):
        """Test docker-compose restart policy consistency."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files have restart policies
        assert 'restart: unless-stopped' in dev_content
        assert 'restart: unless-stopped' in prod_content

    def test_docker_compose_healthcheck_consistency(self):
        """Test docker-compose health check consistency."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files have health checks
        assert 'healthcheck:' in dev_content
        assert 'healthcheck:' in prod_content

    def test_docker_compose_dependency_consistency(self):
        """Test docker-compose dependency consistency."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files have dependencies
        assert 'depends_on:' in dev_content
        assert 'depends_on:' in prod_content

    def test_docker_compose_file_completeness(self):
        """Test docker-compose file completeness."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that both files are not empty
        assert len(dev_content) > 1000, "Development docker-compose file seems incomplete"
        assert len(prod_content) > 1000, "Production docker-compose file seems incomplete"

    def test_docker_compose_file_readability(self):
        """Test docker-compose file readability."""
        with open(self.docker_compose_dev_path, 'r') as f:
            dev_content = f.read()

        with open(self.docker_compose_prod_path, 'r') as f:
            prod_content = f.read()

        # Check that files are properly formatted YAML
        assert 'version:' in dev_content
        assert 'version:' in prod_content
        assert 'services:' in dev_content
        assert 'services:' in prod_content
