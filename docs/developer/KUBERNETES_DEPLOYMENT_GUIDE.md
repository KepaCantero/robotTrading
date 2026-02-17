# Kubernetes Deployment Guide for AlgoTrading

Complete guide for deploying AlgoTrading to Kubernetes clusters (AWS EKS, GKE, AKS, or on-premises).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Local Development Setup](#local-development-setup)
4. [AWS EKS Deployment](#aws-eks-deployment)
5. [Configuration & Secrets](#configuration--secrets)
6. [Monitoring & Logging](#monitoring--logging)
7. [Scaling & Performance](#scaling--performance)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Prerequisites

### Required Tools

```bash
# Kubernetes CLI
kubectl version --client

# Docker (for building images)
docker version

# Helm 3 (for package management)
helm version

# AWS CLI (for EKS)
aws --version

# kustomize (for manifest customization)
kustomize version
```

### Required Permissions

- EKS cluster with admin access
- ECR registry access (for image storage)
- AWS IAM permissions for:
  - EC2 (manage nodes)
  - RDS (if using managed database)
  - ElastiCache (if using managed Redis)
  - Secrets Manager (for secrets)
  - CloudWatch (for logging)

### Cluster Requirements

- **Kubernetes Version**: 1.27+ (recommended 1.28+)
- **Node Count**: Minimum 3 nodes for production
- **Node Type**: 2 CPU, 4 GB RAM minimum per node
- **Storage**: 50 GB minimum (for databases and logs)
- **Networking**: VPC with private and public subnets

---

## Architecture Overview

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Ingress Controller (NGINX)               │
│         Handles HTTP/HTTPS traffic, SSL termination         │
└────┬────────────────────────────────────────────────────────┘
     │
┌────▼──────────────────────────────────────────────────────────┐
│              Load Balancer (AWS NLB/ALB)                      │
└────┬───────────────────────────────────────────────────────────┘
     │
┌────▼──────────────────────────────────────────────────────────┐
│                   Kubernetes Services                         │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  API Service    │  │ Database     │  │ Cache Service    │ │
│  │  (Port 8000)    │  │ Service      │  │ (Redis)          │ │
│  └────────┬────────┘  │ (PostgreSQL) │  │                  │ │
│           │           └──────────────┘  └──────────────────┘ │
└───────────┼──────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│            Deployments (with Auto-Scaling)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ API Pod 1    │  │ API Pod 2    │  │ API Pod 3    │  ... │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│                    Storage & Monitoring                      │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │ PersistentVolumes│      │  Prometheus + Grafana        │ │
│  │ (Database/Logs)  │      │  (Metrics & Dashboards)      │ │
│  └──────────────────┘      └──────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Kubernetes Resources

- **Namespaces**: `algotrading`, `monitoring`, `ingress-nginx`
- **Deployments**: API, PostgreSQL, Redis
- **Services**: ClusterIP (internal), LoadBalancer (external)
- **ConfigMaps**: Application configuration
- **Secrets**: Database credentials, API keys, TLS certificates
- **Ingress**: HTTP/HTTPS routing
- **HPA**: Horizontal Pod Autoscaler (auto-scaling)
- **PDB**: Pod Disruption Budget (availability)
- **NetworkPolicy**: Network security & isolation
- **RBAC**: Role-based access control

---

## Local Development Setup

### 1. Install Minikube (local K8s)

```bash
# Install Minikube
brew install minikube

# Start cluster (requires Docker)
minikube start --cpus=4 --memory=8192

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server

# Get dashboard
minikube dashboard
```

### 2. Deploy Locally

```bash
# Create namespace
kubectl create namespace algotrading

# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml -f k8s/rbac.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/network-policy.yaml

# Or use Kustomize
kubectl apply -k k8s/
```

### 3. Verify Deployment

```bash
# Check pod status
kubectl get pods -n algotrading

# Check services
kubectl get svc -n algotrading

# Check logs
kubectl logs -f deployment/algotrading-api -n algotrading

# Port forward to access locally
kubectl port-forward svc/algotrading-api 8000:8000 -n algotrading

# Visit http://localhost:8000
```

---

## AWS EKS Deployment

### 1. Create EKS Cluster

```bash
# Using eksctl (recommended)
eksctl create cluster \
  --name algotrading-prod \
  --region us-east-1 \
  --nodegroup-name worker-nodes \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --enable-ssm

# Or using AWS Console/CloudFormation
```

### 2. Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --name algotrading-prod \
  --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### 3. Set Up Container Registry (ECR)

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name algotrading \
  --region us-east-1

# Get registry URL
ECR_REGISTRY=$(aws ecr describe-repositories \
  --repository-names algotrading \
  --query 'repositories[0].repositoryUri' \
  --output text \
  --region us-east-1)

echo $ECR_REGISTRY  # Output: 123456789.dkr.ecr.us-east-1.amazonaws.com/algotrading
```

### 4. Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REGISTRY

# Build image
docker build -t $ECR_REGISTRY:latest \
  --target production \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  .

# Push to ECR
docker push $ECR_REGISTRY:latest
```

### 5. Install Required Add-ons

```bash
# AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=algotrading-prod

# Metrics Server (for HPA)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace

# Cert-Manager (for TLS)
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

### 6. Create Secrets

```bash
# Create namespace
kubectl create namespace algotrading

# Create secrets from environment variables
kubectl create secret generic algotrading-secrets \
  --from-literal=DATABASE_PASSWORD=$DB_PASSWORD \
  --from-literal=REDIS_PASSWORD=$REDIS_PASSWORD \
  --from-literal=SECRET_KEY=$SECRET_KEY \
  --from-literal=ALPACA_API_KEY=$ALPACA_KEY \
  --from-literal=ALPACA_API_SECRET=$ALPACA_SECRET \
  --from-literal=JWT_SECRET=$JWT_SECRET \
  -n algotrading

# Or create from file
kubectl create secret generic algotrading-secrets \
  --from-file=.env \
  -n algotrading
```

### 7. Deploy Application

```bash
# Using Kustomize
kubectl apply -k k8s/

# Or using Helm
helm install algotrading helm/ \
  --namespace algotrading \
  --values helm/values-prod.yaml

# Monitor deployment
kubectl rollout status deployment/algotrading-api -n algotrading
```

---

## Configuration & Secrets

### ConfigMap Management

Update `k8s/configmap.yaml` with environment-specific values:

```yaml
data:
  ENVIRONMENT: "production"
  DATABASE_HOST: "postgres.algotrading.svc.cluster.local"
  LOG_LEVEL: "INFO"
  # ... other config
```

Apply changes:

```bash
kubectl apply -f k8s/configmap.yaml -n algotrading
```

### Secrets Management

**IMPORTANT**: Never commit secrets to git!

Options for secrets:

#### 1. Sealed Secrets (recommended)

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
echo -n password | kubectl create secret generic mysecret \
  --dry-run=client \
  --from-file=password=/dev/stdin \
  -o yaml | kubeseal -f - > mysealedsecret.yaml

# Apply sealed secret (safe to commit)
kubectl apply -f mysealedsecret.yaml
```

#### 2. AWS Secrets Manager

```bash
# Store secret
aws secretsmanager create-secret \
  --name algotrading/db-password \
  --secret-string $DB_PASSWORD

# Reference in pod (requires CSI driver)
# volumeMounts:
# - name: secrets
#   mountPath: /mnt/secrets
# volumes:
# - name: secrets
#   csi:
#     driver: secrets-store.csi.k8s.io
#     readOnly: true
#     volumeAttributes:
#       provider: aws
```

#### 3. External Secrets Operator

```bash
# Install external-secrets
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace

# Create SecretStore (AWS Secrets Manager)
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretstore
  namespace: algotrading
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
EOF

# Create ExternalSecret
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: algotrading-secrets
  namespace: algotrading
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretstore
    kind: SecretStore
  target:
    name: algotrading-secrets
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_PASSWORD
      remoteRef:
        key: algotrading/db-password
EOF
```

---

## Monitoring & Logging

### 1. Install Prometheus & Grafana

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values - <<EOF
prometheus:
  prometheusSpec:
    retention: 30d
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources:
            requests:
              storage: 50Gi

grafana:
  adminPassword: $(openssl rand -base64 12)
  persistence:
    enabled: true
    size: 10Gi
EOF
```

### 2. Access Grafana

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Default credentials
# Username: admin
# Password: (from helm install output)

# Visit http://localhost:3000
```

### 3. Configure Prometheus Scraping

Update `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    scrape_configs:
      - job_name: 'algotrading-api'
        static_configs:
          - targets: ['algotrading-api:8000']
        metrics_path: '/metrics'
```

### 4. Logging with ELK Stack (optional)

```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging

# Install Filebeat (collects logs)
helm install filebeat elastic/filebeat \
  --namespace kube-system \
  --set config.filebeat.inputs[0].paths={/var/log/pods/*/*/*.log}
```

---

## Scaling & Performance

### 1. Horizontal Pod Autoscaler (HPA)

```bash
# View HPA status
kubectl get hpa -n algotrading

# Manually scale
kubectl scale deployment algotrading-api \
  --replicas=5 \
  -n algotrading

# Check scaling metrics
kubectl describe hpa algotrading-api-hpa -n algotrading
```

### 2. Vertical Pod Autoscaler (VPA)

```bash
# Install VPA
git clone https://github.com/kubernetes/autoscaler.git
cd autoscaler/vertical-pod-autoscaler
./hack/vpa-up.sh

# View VPA recommendations
kubectl describe vpa algotrading-api-vpa -n algotrading
```

### 3. Node Auto-Scaling

```bash
# Enable cluster autoscaler on EKS
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=algotrading-prod \
  --set awsRegion=us-east-1
```

### 4. Performance Tuning

```bash
# Adjust resource requests/limits in deployment.yaml
resources:
  requests:
    cpu: 1000m      # Increase if CPU-bound
    memory: 1Gi     # Increase if memory-bound
  limits:
    cpu: 4000m
    memory: 4Gi

# Apply changes
kubectl apply -f k8s/deployment.yaml
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n algotrading

# Check logs
kubectl logs <pod-name> -n algotrading

# Check events
kubectl get events -n algotrading
```

### Database Connection Issues

```bash
# Verify service DNS
kubectl exec -it <pod-name> -n algotrading -- nslookup postgres.algotrading.svc.cluster.local

# Test connection
kubectl exec -it <pod-name> -n algotrading -- psql -h postgres -U postgres -d algotrading
```

### Memory/CPU Issues

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n algotrading

# Check resource quotas
kubectl describe resourcequota -n algotrading
```

### Persistent Volume Issues

```bash
# Check PVCs
kubectl get pvc -n algotrading

# Check PVs
kubectl get pv

# Resize PVC
kubectl patch pvc postgres-storage -n algotrading -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

---

## Best Practices

### 1. High Availability

- ✅ Run at least 3 replicas of critical components
- ✅ Use Pod Disruption Budgets (PDB)
- ✅ Spread pods across availability zones (node affinity)
- ✅ Use managed services (RDS, ElastiCache) for databases

### 2. Security

- ✅ Use RBAC for access control
- ✅ Use Network Policies for network segmentation
- ✅ Use sealed-secrets or external-secrets for credential management
- ✅ Enable pod security standards
- ✅ Use private container registries
- ✅ Scan images for vulnerabilities (Trivy, Snyk)
- ✅ Use TLS/HTTPS for all communication

### 3. Observability

- ✅ Implement structured logging (JSON)
- ✅ Monitor metrics with Prometheus
- ✅ Use Grafana for visualization
- ✅ Set up alerting rules
- ✅ Use distributed tracing (Jaeger, Zipkin)
- ✅ Implement health checks (liveness, readiness, startup probes)

### 4. Cost Optimization

- ✅ Set resource requests/limits appropriately
- ✅ Use node auto-scaling
- ✅ Use spot instances for non-critical workloads
- ✅ Use resource quotas per namespace
- ✅ Monitor cluster costs

### 5. Operational Excellence

- ✅ Use GitOps (ArgoCD, Flux) for deployment management
- ✅ Implement automated backups
- ✅ Use infrastructure-as-code (Terraform)
- ✅ Document runbooks for common issues
- ✅ Test disaster recovery procedures

---

## Further Resources

- [Kubernetes Official Documentation](https://kubernetes.io/docs/)
- [EKS Best Practices Guide](https://aws.github.io/aws-eks-best-practices/)
- [Helm Documentation](https://helm.sh/docs/)
- [CNCF Landscape](https://landscape.cncf.io/)

---

## Support

For issues or questions:
1. Check pod logs: `kubectl logs -f <pod-name> -n algotrading`
2. Describe resources: `kubectl describe <resource-type> <resource-name>`
3. Check events: `kubectl get events -n algotrading`
4. Review this guide's troubleshooting section
