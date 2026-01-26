#!/bin/bash
# Validate configuration files
# Phase 4.2: Production Config Management Validation Script

set -e
set -u
set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/config"
ERRORS=0
WARNINGS=0

log_info "Validating AlgoTrading configuration..."
log_info "Config directory: ${CONFIG_DIR}"

# ============================================================================
# 1. Check Python and required modules
# ============================================================================

log_check "Checking Python installation..."

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    ERRORS=$((ERRORS + 1))
else
    python_version=$(python3 --version | cut -d' ' -f2)
    log_info "Python version: ${python_version}"

    # Check PyYAML
    if ! python3 -c "import yaml" 2>/dev/null; then
        log_warn "PyYAML not installed, YAML validation will be limited"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# ============================================================================
# 2. Validate YAML syntax
# ============================================================================

log_check "Validating YAML syntax..."

yaml_files=(
    "production.yaml"
    "development.yaml"
    "staging.yaml"
    "secrets.yaml.example"
)

for yaml_file in "${yaml_files[@]}"; do
    file_path="${CONFIG_DIR}/${yaml_file}"

    if [ ! -f "${file_path}" ]; then
        if [[ "${yaml_file}" == *"example" ]]; then
            log_warn "Optional file not found: ${yaml_file}"
        else
            log_error "Required config file not found: ${yaml_file}"
            ERRORS=$((ERRORS + 1))
        fi
        continue
    fi

    log_info "Validating: ${yaml_file}"

    # Check if file is readable
    if [ ! -r "${file_path}" ]; then
        log_error "File is not readable: ${yaml_file}"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # Validate YAML syntax with Python
    if command -v python3 &> /dev/null && python3 -c "import yaml" 2>/dev/null; then
        if python3 -c "import yaml; yaml.safe_load(open('${file_path}'))" 2>/dev/null; then
            log_info "  YAML syntax is valid"
        else
            log_error "  YAML syntax is invalid: ${yaml_file}"
            ERRORS=$((ERRORS + 1))
        fi
    else
        log_warn "  Skipping YAML validation (PyYAML not available)"
    fi
done

# ============================================================================
# 3. Validate production configuration structure
# ============================================================================

log_check "Validating production configuration structure..."

prod_config="${CONFIG_DIR}/production.yaml"

if [ -f "${prod_config}" ]; then
    # Check for required sections
    required_sections=(
        "environment"
        "database"
        "brokers"
        "risk"
        "monitoring"
        "tax"
        "compliance"
    )

    for section in "${required_sections[@]}"; do
        if grep -q "^${section}:" "${prod_config}"; then
            log_info "  Section found: ${section}"
        else
            log_error "  Required section missing: ${section}"
            ERRORS=$((ERRORS + 1))
        fi
    done

    # Check environment value
    environment=$(grep "^environment:" "${prod_config}" | cut -d':' -f2 | tr -d ' "')
    if [ "${environment}" = "production" ]; then
        log_info "  Environment is correctly set to: ${environment}"
    else
        log_error "  Environment must be 'production', found: ${environment}"
        ERRORS=$((ERRORS + 1))
    fi

    # Check debug mode
    debug=$(grep "^debug:" "${prod_config}" | cut -d':' -f2 | tr -d ' ')
    if [ "${debug}" = "false" ]; then
        log_info "  Debug mode is correctly disabled"
    else
        log_error "  Debug mode must be false in production"
        ERRORS=$((ERRORS + 1))
    fi
fi

# ============================================================================
# 4. Check for secrets placeholder values
# ============================================================================

log_check "Checking for placeholder values in production config..."

if [ -f "${prod_config}" ]; then
    placeholders=(
        "your_"
        "CHANGE_THIS"
        "example.com"
    )

    found_placeholder=false
    for placeholder in "${placeholders[@]}"; do
        if grep -i "${placeholder}" "${prod_config}" > /dev/null 2>&1; then
            log_warn "  Found placeholder with '${placeholder}' in production config"
            found_placeholder=true
        fi
    done

    if [ "$found_placeholder" = true ]; then
        log_warn "  Placeholder values found - ensure these are replaced before deployment"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# ============================================================================
# 5. Validate environment variable references
# ============================================================================

log_check "Validating environment variable references..."

env_vars_in_config=($(grep -o '\${[^}]*}' "${CONFIG_DIR}/production.yaml" 2>/dev/null | sort -u || true))

if [ ${#env_vars_in_config[@]} -gt 0 ]; then
    log_info "  Environment variables referenced in config:"
    for var in "${env_vars_in_config[@]}"; do
        # Remove ${ and } safely
        var_name="${var#\$\{}"
        var_name="${var_name%\}}"
        log_info "    - ${var_name}"
    done

    # Check if .env.prod exists
    if [ -f "${PROJECT_ROOT}/.env.prod" ]; then
        log_info "  .env.prod file exists"

        # Check if referenced variables are defined
        for var in "${env_vars_in_config[@]}"; do
            # Remove ${ and } safely
            var_name="${var#\$\{}"
            var_name="${var_name%\}}"
            if grep -q "^${var_name}=" "${PROJECT_ROOT}/.env.prod" 2>/dev/null; then
                log_info "    ${var_name} is defined in .env.prod"
            else
                log_warn "    ${var_name} is NOT defined in .env.prod"
                WARNINGS=$((WARNINGS + 1))
            fi
        done
    else
        log_warn "  .env.prod file not found - environment variables cannot be validated"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    log_info "  No environment variable references found"
fi

# ============================================================================
# 6. Check file permissions
# ============================================================================

log_check "Checking file permissions..."

# Production config should be readable by owner only (ideally)
if [ -f "${prod_config}" ]; then
    perms=$(stat -c "%a" "${prod_config}" 2>/dev/null || stat -f "%OLp" "${prod_config}" 2>/dev/null)
    log_info "  Production config permissions: ${perms}"

    # Warn if world-readable
    if [ "${perms}" = "644" ] || [ "${perms}" = "666" ]; then
        log_warn "  Production config is world-readable - consider restricting permissions"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check for secrets.yaml (should not exist in repo)
if [ -f "${CONFIG_DIR}/secrets.yaml" ]; then
    log_warn "  secrets.yaml found - this file should NOT be committed to version control"
    WARNINGS=$((WARNINGS + 1))
fi

# ============================================================================
# 7. Check deployment script
# ============================================================================

log_check "Checking deployment script..."

deploy_script="${PROJECT_ROOT}/scripts/deploy_production.sh"

if [ ! -f "${deploy_script}" ]; then
    log_error "Deployment script not found: scripts/deploy_production.sh"
    ERRORS=$((ERRORS + 1))
else
    log_info "Deployment script exists"

    # Check if executable
    if [ -x "${deploy_script}" ]; then
        log_info "Deployment script is executable"
    else
        log_warn "Deployment script is not executable - run: chmod +x scripts/deploy_production.sh"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# ============================================================================
# 8. Summary
# ============================================================================

echo ""
echo "============================================================================"
echo "Validation Summary"
echo "============================================================================"

if [ ${ERRORS} -eq 0 ] && [ ${WARNINGS} -eq 0 ]; then
    log_info "All checks passed!"
    exit 0
elif [ ${ERRORS} -eq 0 ]; then
    log_warn "Validation passed with ${WARNINGS} warning(s)"
    exit 0
else
    log_error "Validation failed with ${ERRORS} error(s) and ${WARNINGS} warning(s)"
    exit 1
fi
