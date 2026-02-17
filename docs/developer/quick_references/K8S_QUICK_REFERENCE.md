# Kubernetes Quick Reference

Common kubectl commands and operations for AlgoTrading deployment.

## Deployment Operations

### View Deployments

```bash
# List all deployments
kubectl get deployments -n algotrading

# Watch deployment status
kubectl rollout status deployment/algotrading-api -n algotrading

# View deployment details
kubectl describe deployment algotrading-api -n algotrading

# View deployment YAML
kubectl get deployment algotrading-api -n algotrading -o yaml
```

### Update Deployments

```bash
# Update image
kubectl set image deployment/algotrading-api \
  api=ghcr.io/YOUR_ORG/algotrading:v1.1.0 \
  -n algotrading

# Rollback to previous version
kubectl rollout undo deployment/algotrading-api -n algotrading

# Scale manually
kubectl scale deployment algotrading-api --replicas=5 -n algotrading

# Apply new manifest
kubectl apply -f k8s/deployment.yaml -n algotrading
```

## Pod Operations

### View Pods

```bash
# List pods
kubectl get pods -n algotrading

# List pods with more details
kubectl get pods -n algotrading -o wide

# Watch pods
kubectl get pods -n algotrading --watch

# Get pod details
kubectl describe pod <pod-name> -n algotrading
```

### Pod Debugging

```bash
# View logs
kubectl logs <pod-name> -n algotrading

# Tail logs
kubectl logs -f <pod-name> -n algotrading

# View logs from previous crash
kubectl logs <pod-name> --previous -n algotrading

# Execute command in pod
kubectl exec -it <pod-name> -n algotrading -- /bin/bash

# Copy files from pod
kubectl cp algotrading/<pod-name>:/app/logs ./logs -n algotrading

# Port forward
kubectl port-forward <pod-name> 8000:8000 -n algotrading
```

### Delete Pods

```bash
# Delete pod (will restart due to deployment)
kubectl delete pod <pod-name> -n algotrading

# Delete all pods in deployment
kubectl delete pods -l app=algotrading -n algotrading
```

## Service Operations

### View Services

```bash
# List services
kubectl get services -n algotrading

# Get service details
kubectl describe svc algotrading-api -n algotrading

# Get service endpoints
kubectl get endpoints algotrading-api -n algotrading
```

### Port Forwarding

```bash
# Forward port to service
kubectl port-forward svc/algotrading-api 8000:8000 -n algotrading

# Forward port to pod
kubectl port-forward pod/algotrading-api-xxx 8000:8000 -n algotrading
```

## ConfigMap & Secrets

### ConfigMap Operations

```bash
# List ConfigMaps
kubectl get configmaps -n algotrading

# View ConfigMap
kubectl get cm algotrading-config -n algotrading -o yaml

# Edit ConfigMap
kubectl edit cm algotrading-config -n algotrading

# Create ConfigMap from file
kubectl create configmap app-config \
  --from-file=config.env \
  -n algotrading

# Update ConfigMap
kubectl apply -f k8s/configmap.yaml -n algotrading
```

### Secrets Operations

```bash
# List secrets
kubectl get secrets -n algotrading

# View secret (base64 encoded)
kubectl get secret algotrading-secrets -n algotrading -o yaml

# Create secret
kubectl create secret generic db-creds \
  --from-literal=password=$DB_PASSWORD \
  -n algotrading

# Delete secret
kubectl delete secret algotrading-secrets -n algotrading

# Update secret
kubectl patch secret algotrading-secrets -p '{"data":{"key":"value"}}' -n algotrading
```

## Resource Management

### Resource Quotas

```bash
# View resource quota
kubectl describe resourcequota -n algotrading

# Set resource quota
kubectl create quota my-quota \
  --hard=pods=10,cpu=5,memory=5Gi \
  -n algotrading
```

### Resource Limits

```bash
# View node resources
kubectl top nodes

# View pod resources
kubectl top pods -n algotrading

# View resource requests/limits
kubectl describe pod <pod-name> -n algotrading | grep -A 5 "Limits\|Requests"
```

## Monitoring & Logging

### Events

```bash
# View cluster events
kubectl get events -n algotrading

# Watch events
kubectl get events -n algotrading --watch

# Get events for specific pod
kubectl describe pod <pod-name> -n algotrading | grep -A 20 "Events:"
```

### Metrics

```bash
# View node metrics
kubectl top nodes

# View pod metrics
kubectl top pods -n algotrading

# View pod metrics with sorted output
kubectl top pods -n algotrading --sort-by=cpu
kubectl top pods -n algotrading --sort-by=memory
```

## Scaling & Auto-scaling

### Horizontal Pod Autoscaler (HPA)

```bash
# View HPA status
kubectl get hpa -n algotrading

# Describe HPA
kubectl describe hpa algotrading-api-hpa -n algotrading

# Create HPA
kubectl autoscale deployment algotrading-api \
  --min=3 --max=10 \
  --cpu-percent=70 \
  -n algotrading

# Update HPA
kubectl patch hpa algotrading-api-hpa \
  -p '{"spec":{"maxReplicas":15}}' \
  -n algotrading
```

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment algotrading-api \
  --replicas=5 \
  -n algotrading

# Scale all deployments
kubectl scale deployments -l app=algotrading \
  --replicas=5 \
  -n algotrading
```

## Network & Connectivity

### DNS Resolution

```bash
# Test service DNS (from pod)
kubectl exec -it <pod-name> -n algotrading -- nslookup postgres

# Check service endpoints
kubectl get endpoints -n algotrading

# Test connectivity
kubectl exec -it <pod-name> -n algotrading -- curl http://algotrading-api:8000/health
```

### Ingress Operations

```bash
# List ingresses
kubectl get ingress -n algotrading

# Describe ingress
kubectl describe ingress algotrading-ingress -n algotrading

# View ingress IP
kubectl get ingress -n algotrading --watch

# Edit ingress
kubectl edit ingress algotrading-ingress -n algotrading
```

## Cluster Information

### Cluster Status

```bash
# Cluster info
kubectl cluster-info

# Cluster version
kubectl version

# Node information
kubectl get nodes -o wide

# Node resources
kubectl describe nodes

# Persistent volumes
kubectl get pv

# Persistent volume claims
kubectl get pvc -n algotrading
```

### Node Management

```bash
# Cordon node (prevent new pods)
kubectl cordon <node-name>

# Drain node (remove existing pods)
kubectl drain <node-name> --ignore-daemonsets

# Uncordon node
kubectl uncordon <node-name>

# View node status
kubectl describe node <node-name>
```

## RBAC & Permissions

### View RBAC Resources

```bash
# List roles
kubectl get roles -n algotrading

# List role bindings
kubectl get rolebindings -n algotrading

# View role
kubectl describe role algotrading-api -n algotrading

# View role binding
kubectl describe rolebinding algotrading-api -n algotrading

# Check permissions
kubectl auth can-i get pods -n algotrading --as=system:serviceaccount:algotrading:algotrading-api
```

## Cleanup & Deletion

### Delete Resources

```bash
# Delete by file
kubectl delete -f k8s/deployment.yaml -n algotrading

# Delete by selector
kubectl delete pods -l app=algotrading -n algotrading

# Delete entire namespace
kubectl delete namespace algotrading

# Delete without waiting for termination
kubectl delete pod <pod-name> --grace-period=0 --force -n algotrading
```

## Advanced Operations

### Apply Changes

```bash
# Apply with kustomize
kubectl apply -k k8s/

# Apply with dry-run (preview changes)
kubectl apply -f k8s/deployment.yaml --dry-run=client -n algotrading

# Apply with server-side changes
kubectl apply -f k8s/deployment.yaml --server-side -n algotrading
```

### Edit Resources

```bash
# Edit deployment
kubectl edit deployment algotrading-api -n algotrading

# Edit ConfigMap
kubectl edit cm algotrading-config -n algotrading

# Edit secret
kubectl edit secret algotrading-secrets -n algotrading
```

### Label Management

```bash
# Add label
kubectl label pods <pod-name> app=algotrading -n algotrading

# Remove label
kubectl label pods <pod-name> app- -n algotrading

# View labels
kubectl get pods -n algotrading --show-labels

# Select by label
kubectl get pods -l app=algotrading -n algotrading
```

### Patch Resources

```bash
# Patch deployment
kubectl patch deployment algotrading-api \
  -p '{"spec":{"replicas":5}}' \
  -n algotrading

# Patch pod
kubectl patch pod <pod-name> \
  -p '{"spec":{"containers":[{"name":"api","image":"new-image"}]}}' \
  -n algotrading
```

## Troubleshooting Commands

```bash
# Common debugging pipeline
kubectl get events -n algotrading  # See what happened
kubectl describe pod <pod-name> -n algotrading  # Get pod details
kubectl logs <pod-name> -n algotrading  # View logs
kubectl logs <pod-name> --previous -n algotrading  # View crash logs
kubectl exec -it <pod-name> -n algotrading -- /bin/bash  # Debug inside pod

# Check health
kubectl get pods -n algotrading
kubectl get svc -n algotrading
kubectl describe ingress -n algotrading
kubectl top nodes
kubectl top pods -n algotrading
```

## Save/Export Configuration

```bash
# Export deployment as YAML
kubectl get deployment algotrading-api -n algotrading -o yaml > deployment-backup.yaml

# Export all resources
kubectl get all -n algotrading -o yaml > algotrading-backup.yaml

# Backup database
kubectl exec postgres-0 -n algotrading -- pg_dump -U postgres algotrading > backup.sql
```

## Helpful Aliases

Add to your shell profile (~/.bashrc, ~/.zshrc):

```bash
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgd='kubectl get deployments'
alias kgs='kubectl get services'
alias kl='kubectl logs'
alias kex='kubectl exec -it'
alias kdesc='kubectl describe'
alias kaf='kubectl apply -f'
alias kdel='kubectl delete'
alias kgpa='kubectl get pods -A'
alias kgda='kubectl get deployments -A'
alias kgsa='kubectl get services -A'

# Use namespace alias
alias kn='kubectl config set-context --current --namespace'
kn algotrading  # Switch to namespace
```

---

**Quick Help**: `kubectl <command> --help`

**Full Reference**: https://kubernetes.io/docs/reference/kubectl/cheatsheet/
