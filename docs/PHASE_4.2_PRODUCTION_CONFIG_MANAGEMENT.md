# Phase 4.2: Production Config Management

## Overview

Phase 4.2 implements a robust production configuration management system that separates development, staging, and production configurations while ensuring secrets are properly managed through environment variables.

## Criticality

**HIGH** for operations - This phase addresses the critical need for separation between development and production configurations to prevent accidental use of development settings in production.

## Files Created

### Configuration Files

1. **`config/production.yaml`** - Production-optimized configuration
   - Live trading settings with real money
   - Conservative risk limits (2% daily VaR)
   - Enabled monitoring and circuit breakers
   - Spain tax compliance (Modelo 721)

2. **`config/development.yaml`** - Development configuration
   - Paper trading enabled
   - Relaxed risk limits for testing
   - Debug mode enabled
   - No automated backups

3. **`config/staging.yaml`** - Staging/pre-production configuration
   - Production-like settings for testing
   - Paper trading enabled
   - Intermediate risk limits
   - Full monitoring enabled

4. **`config/secrets.yaml.example`** - Template for secrets management
   - API keys placeholder
   - Webhook URLs
   - Encryption keys
   - Email credentials

### Environment Files

5. **`.env.prod.example`** - Production environment variables template
   - Database credentials
   - API keys
   - Trading parameters
   - Alert configurations

### Deployment Scripts

6. **`scripts/deploy_production.sh`** - Production deployment script
   - Pre-deployment validation
   - Automated backups
   - Service management
   - Health checks
   - Rollback documentation

7. **`scripts/rollback_production.sh`** - Rollback script
   - Lists available backups
   - Restores database and config
   - Service restart
   - Verification

8. **`scripts/validate_config.sh`** - Configuration validation script
   - YAML syntax validation
   - Structure validation
   - Placeholder detection
   - Environment variable checking
   - File permissions verification

### Python Module

9. **`app/core/config_validator.py`** - Configuration validator module
   - Pydantic-based validation
   - YAML syntax checking
   - Production-specific rules
   - Environment variable validation
   - Detailed error reporting

## Configuration Structure

### Production Configuration (`config/production.yaml`)

```yaml
environment: "production"
debug: false
log_level: "INFO"

# Database with backups
database:
  path: "/var/lib/algotrading/production.db"
  backup_enabled: true
  backup_interval_seconds: 300

# Live trading brokers
brokers:
  primary:
    name: "ibkr"
    enabled: true

# Conservative risk limits
risk:
  max_var_daily_pct: 0.02  # 2% daily VaR
  max_position_size_pct: 0.20  # 20% max per position

# Spain tax compliance
tax:
  residence_country: "ES"
  fifo_enabled: true
  modelo_721_enabled: true
```

### Environment Variable References

Configuration files can reference environment variables using `${VAR_NAME}` syntax:

```yaml
news:
  marketaux_api_key: "${MARKETAUX_API_KEY}"
  webhook_url: "${NEWS_WEBHOOK_URL}"

alerts:
  email_to: "${ALERT_EMAIL}"
```

These variables are loaded from `.env.prod` during deployment.

## Security Considerations

### Secrets Management

1. **Never commit secrets to version control**
   - `.env.prod` is in `.gitignore`
   - `config/secrets.yaml` is in `.gitignore`
   - Only example files are committed

2. **Use environment variables for sensitive data**
   - API keys
   - Database passwords
   - Webhook URLs
   - Encryption keys

3. **File permissions**
   - Production config should be readable by owner only
   - Secrets files should have restricted permissions (600)

### Validation Rules

#### Production-Specific Validations

- `environment` must be "production"
- `debug` must be false
- No placeholder values allowed
- Risk limits must be conservative
- All required sections present

#### Placeholder Detection

The validator detects and warns about:
- `your_*_here` patterns
- `CHANGE_THIS` patterns
- `example.com` domains
- Default secret keys

## Deployment Workflow

### Initial Setup

1. **Create production environment file**
   ```bash
   cp .env.prod.example .env.prod
   # Edit .env.prod with real values
   ```

2. **Create secrets file**
   ```bash
   cp config/secrets.yaml.example config/secrets.yaml
   # Edit config/secrets.yaml with real values
   chmod 600 config/secrets.yaml
   ```

3. **Validate configuration**
   ```bash
   ./scripts/validate_config.sh
   ```

### Deployment

1. **Run deployment script**
   ```bash
   ./scripts/deploy_production.sh
   ```

The script will:
- Validate environment variables
- Run tests
- Create backups
- Stop service
- Deploy
- Start service
- Verify deployment

### Rollback

If deployment fails:

1. **Run rollback script**
   ```bash
   ./scripts/rollback_production.sh
   ```

2. **Select backup to restore**

3. **Verify rollback**

## Monitoring and Alerts

### Memory Monitoring

```yaml
monitoring:
  memory_limit_mb: 4096
  memory_action: "alert_only"  # or "restart", "garbage_collect"

alerts:
  thresholds:
    memory_warning_mb: 3072
    memory_critical_mb: 4096
```

### Circuit Breaker

```yaml
circuit_breaker:
  enabled: true
  level_1_threshold: -0.07  # -7%
  level_2_threshold: -0.13  # -13%
  level_3_threshold: -0.20  # -20%
```

### Time Sync

```yaml
time_sync:
  enabled: true
  check_interval_seconds: 60
  drift_threshold_seconds: 1.0
```

## Tax Compliance (Spain)

The production configuration includes Spain-specific tax compliance:

```yaml
tax:
  residence_country: "ES"
  fifo_enabled: true  # First-In, First-Out accounting
  modelo_721_enabled: true  # Spanish tax reporting
  progressive_rates:
    bracket_1: 0.19  # <= 33,007.99
    bracket_2: 0.21  # 33,008 - 53,407.99
    bracket_3: 0.23  # > 53,408

compliance:
  country: "ES"
  enforce_pdt: false  # Spain doesn't have PDT rule
  enforce_wash_sale: false  # Spain doesn't have wash sale rule
```

## Acceptance Criteria Status

- [x] Separate prod/dev configs
- [x] Secrets in environment variables
- [x] Config validation on startup
- [x] Deployment script
- [x] Rollback procedure

## Usage Examples

### Load Configuration in Python

```python
from app.core.config_loader import YAMLConfigLoader

# Load production config
loader = YAMLConfigLoader(config_dir=Path("config"))
config = loader.load("production.yaml")

# Access configuration
db_path = config["database"]["path"]
risk_limit = config["risk"]["max_var_daily_pct"]
```

### Validate Configuration Programmatically

```python
from app.core.config_validator import ConfigValidator

validator = ConfigValidator()
result = validator.validate_production_config(env_file=Path(".env.prod"))

if result.is_valid:
    print("Configuration is valid")
else:
    print("Configuration has errors:")
    for error in result.errors:
        print(f"  {error.field}: {error.message}")
```

### Switch Environments

```python
import os
os.environ["ENVIRONMENT"] = "production"

from app.core.environment_config import get_config
config = get_config()

print(config.environment)  # "production"
print(config.is_production())  # True
```

## Testing

### Validate All Configurations

```bash
# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config/production.yaml'))"

# Run validation script
./scripts/validate_config.sh

# Run Python validator
python3 -m app.core.config_validator --environment production
```

### Test Deployment

```bash
# Dry run (doesn't actually deploy)
ENVIRONMENT=production python3 -m app.core.config_validator

# Run tests with production config
pytest tests/ -v -m "not integration"
```

## Maintenance

### Regular Tasks

1. **Review backups**
   ```bash
   ls -lh backups/
   ```

2. **Check logs**
   ```bash
   tail -f logs/production.log
   ```

3. **Validate configuration**
   ```bash
   ./scripts/validate_config.sh
   ```

4. **Monitor resources**
   ```bash
   systemctl status algotrading
   ```

### Update Configuration

1. Edit configuration file
2. Validate changes
3. Deploy using deployment script
4. Verify deployment

## Troubleshooting

### Configuration Fails Validation

1. Check YAML syntax
2. Verify required sections present
3. Remove placeholder values
4. Check environment variables defined

### Service Won't Start

1. Check logs: `tail -f logs/production.log`
2. Validate configuration: `./scripts/validate_config.sh`
3. Check database connectivity
4. Verify environment variables loaded

### Need to Rollback

1. Run: `./scripts/rollback_production.sh`
2. Select backup
3. Verify service started

## Best Practices

1. **Always validate before deploying**
   - Run `validate_config.sh` first
   - Fix any errors before deployment

2. **Never skip backups**
   - Deployment script auto-creates backups
   - Keep at least 3 recent backups

3. **Test in staging first**
   - Deploy to staging environment
   - Verify everything works
   - Then deploy to production

4. **Monitor after deployment**
   - Check logs regularly
   - Verify service health
   - Monitor resource usage

5. **Document changes**
   - Update this document when changing structure
   - Note any new required variables

## Related Files

- `app/core/config.py` - Main configuration module
- `app/core/environment_config.py` - Environment-specific configuration
- `app/core/config_loader.py` - YAML configuration loader
- `app/core/centralized_config.py` - Centralized configuration system

## Next Steps

1. Review and customize `config/production.yaml`
2. Create `.env.prod` with real values
3. Create `config/secrets.yaml` with API keys
4. Run `validate_config.sh` to verify setup
5. Test deployment in staging environment first
