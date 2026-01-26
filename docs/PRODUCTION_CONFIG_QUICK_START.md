# Production Config Management - Quick Start Guide

## Initial Setup (5 minutes)

### 1. Create Production Environment File

```bash
# Copy the example
cp .env.prod.example .env.prod

# Edit with your real values
nano .env.prod
```

**Required variables to set:**
- `SECRET_KEY` (32+ characters)
- `DATABASE_URL` or database credentials
- `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- `MARKETAUX_API_KEY`
- `ALERT_EMAIL`

### 2. Create Secrets File

```bash
# Copy the example
cp config/secrets.yaml.example config/secrets.yaml

# Edit with your real values
nano config/secrets.yaml

# Set secure permissions
chmod 600 config/secrets.yaml
```

### 3. Validate Configuration

```bash
# Run validation script
./scripts/validate_config.sh
```

**Expected output:**
```
[INFO] Configuration validation passed: All checks OK
```

## Deployment

### Standard Deployment

```bash
# Deploy to production
./scripts/deploy_production.sh
```

The script will:
- Validate configuration
- Run tests
- Create backups
- Deploy application
- Start service
- Verify deployment

### Deployment with Verification

```bash
# Deploy
./scripts/deploy_production.sh

# Check service status
systemctl status algotrading

# View logs
tail -f logs/production.log

# Check health endpoint
curl http://localhost:8000/health
```

## Rollback

### Quick Rollback

```bash
# Run rollback script
./scripts/rollback_production.sh

# Select backup number when prompted
# Example: Enter '0' for most recent backup
```

### Manual Rollback

```bash
# Stop service
sudo systemctl stop algotrading

# Restore database
cp backups/pre-deploy-orders-YYYYMMDD_HHMMSS.db data/orders.db

# Restore config
tar -xzf backups/pre-deploy-config-YYYYMMDD_HHMMSS.tar.gz

# Start service
sudo systemctl start algotrading
```

## Configuration Management

### Switch Environments

```python
# Set environment variable
export ENVIRONMENT=production

# Or in Python before importing
import os
os.environ["ENVIRONMENT"] = "production"
```

### Override Config Values

```bash
# Set environment variable to override
export RISK_MAX_VAR_DAILY_PCT=0.03

# Or in .env.prod
RISK_MAX_VAR_DAILY_PCT=0.03
```

### View Current Configuration

```bash
# View production config
cat config/production.yaml

# View environment variables
cat .env.prod

# View secrets (be careful!)
cat config/secrets.yaml
```

## Monitoring

### Check Service Health

```bash
# System service status
systemctl status algotrading

# Check if process is running
pgrep -f "python.*algotrading"

# Check health endpoint
curl http://localhost:8000/health
```

### View Logs

```bash
# Follow production logs
tail -f logs/production.log

# Search for errors
grep "ERROR" logs/production.log

# View last 100 lines
tail -n 100 logs/production.log
```

### Check Resource Usage

```bash
# Memory usage
free -h

# Disk usage
df -h

# Process resource usage
top -p $(pgrep -f "python.*algotrading")
```

## Validation

### Validate YAML Syntax

```bash
# Validate production.yaml
python3 -c "import yaml; yaml.safe_load(open('config/production.yaml'))"

# Validate all configs
for f in config/*.yaml; do
    echo "Validating $f..."
    python3 -c "import yaml; yaml.safe_load(open('$f'))"
done
```

### Validate Environment Variables

```bash
# Check if required variables are set
source .env.prod
echo "SECRET_KEY: ${SECRET_KEY:0:10}..."
echo "DATABASE_URL: ${DATABASE_URL:0:20}..."

# Run validation script
./scripts/validate_config.sh
```

### Validate Python Config

```bash
# Run Python validator
python3 -m app.core.config_validator --environment production

# With custom env file
python3 -m app.core.config_validator \
    --environment production \
    --env-file .env.prod
```

## Troubleshooting

### Problem: Configuration validation fails

**Solution:**
```bash
# Check what's wrong
./scripts/validate_config.sh

# Common issues:
# - Missing environment variables in .env.prod
# - Placeholder values in production.yaml
# - Invalid YAML syntax
```

### Problem: Service won't start

**Solution:**
```bash
# Check logs
tail -f logs/production.log

# Validate configuration
./scripts/validate_config.sh

# Check database connectivity
python3 -c "from app.core.database import engine; print(engine.connect())"
```

### Problem: Environment variables not loading

**Solution:**
```bash
# Verify .env.prod exists
ls -la .env.prod

# Check file permissions
chmod 600 .env.prod

# Test loading
source .env.prod
echo $SECRET_KEY
```

### Problem: Need to check what changed

**Solution:**
```bash
# Compare configs
diff config/development.yaml config/production.yaml

# View git diff
git diff config/production.yaml

# Check recent backups
ls -lt backups/
```

## Maintenance Tasks

### Daily

```bash
# Check service status
systemctl status algotrading

# Review logs for errors
grep "ERROR" logs/production.log | tail -20

# Check disk space
df -h
```

### Weekly

```bash
# Review backups
ls -lh backups/

# Clean old backups (keep last 5)
cd backups
ls -t pre-deploy-* | tail -n +6 | xargs rm -f

# Validate configuration
./scripts/validate_config.sh
```

### Monthly

```bash
# Review and update configuration
nano config/production.yaml

# Test deployment in staging first
# (if you have staging environment)

# Security audit
# - Check who has access to secrets
# - Review API key usage
# - Update dependencies
```

## Security Best Practices

### File Permissions

```bash
# Secure production config
chmod 600 config/production.yaml

# Secure secrets file
chmod 600 config/secrets.yaml

# Secure environment file
chmod 600 .env.prod

# Verify
ls -la config/secrets.yaml .env.prod
```

### Secrets Rotation

```bash
# 1. Generate new secrets
# 2. Update config/secrets.yaml
# 3. Update .env.prod
# 4. Validate configuration
./scripts/validate_config.sh

# 5. Deploy during maintenance window
./scripts/deploy_production.sh

# 6. Verify everything works
# 7. Keep old secrets for 1 week (rollback)
```

### Audit Access

```bash
# Who can read secrets?
find config -name "*.yaml" -exec ls -la {} \;

# Check file modification times
ls -lt config/secrets.yaml .env.prod

# Review git log for config changes
git log --oneline -- config/
```

## Common Commands Reference

```bash
# Validation
./scripts/validate_config.sh
python3 -m app.core.config_validator

# Deployment
./scripts/deploy_production.sh

# Rollback
./scripts/rollback_production.sh

# Service Management
systemctl start algotrading
systemctl stop algotrading
systemctl restart algotrading
systemctl status algotrading

# Logs
tail -f logs/production.log
grep "ERROR" logs/production.log

# Backups
ls -lh backups/
cp data/orders.db backups/manual-backup-$(date +%Y%m%d).db
```

## Getting Help

1. Check logs: `tail -f logs/production.log`
2. Validate config: `./scripts/validate_config.sh`
3. Read docs: `docs/PHASE_4.2_PRODUCTION_CONFIG_MANAGEMENT.md`
4. Check service: `systemctl status algotrading`

## Emergency Procedures

### Immediate Stop Trading

```bash
# Stop service immediately
sudo systemctl stop algotrading

# Or kill process
pkill -9 -f "python.*algotrading"
```

### Emergency Rollback

```bash
# Stop service
sudo systemctl stop algotrading

# Find most recent backup
ls -lt backups/ | head -5

# Restore
cp backups/LATEST_BACKUP.db data/orders.db

# Start service
sudo systemctl start algotrading
```

### Contact Information

- System Administrator: [admin-email@example.com]
- On-Call: [phone-number]
- Documentation: `docs/PHASE_4.2_PRODUCTION_CONFIG_MANAGEMENT.md`
