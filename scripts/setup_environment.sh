#!/bin/bash

# Environment Configuration Script
# TASK-5: Configuración de variables de entorno

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration directory
CONFIG_DIR="config"
ENV_FILE=".env"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [ENVIRONMENT] [OPTIONS]"
    echo ""
    echo "Environments:"
    echo "  development  - Development environment (default)"
    echo "  testing      - Testing environment"
    echo "  staging      - Staging environment"
    echo "  production   - Production environment"
    echo ""
    echo "Options:"
    echo "  --help, -h   - Show this help message"
    echo "  --validate   - Validate configuration without applying"
    echo "  --backup     - Backup current .env file before applying"
    echo "  --force      - Force apply configuration without confirmation"
    echo ""
    echo "Examples:"
    echo "  $0 development"
    echo "  $0 production --backup"
    echo "  $0 staging --validate"
}

# Function to validate environment
validate_environment() {
    local env=$1
    local config_file="${CONFIG_DIR}/${env}.env"
    
    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        return 1
    fi
    
    print_info "Validating configuration for environment: $env"
    
    # Check for required variables
    local required_vars=(
        "ENVIRONMENT"
        "DEBUG"
        "APP_NAME"
        "APP_VERSION"
        "DB_HOST"
        "DB_PORT"
        "DB_NAME"
        "DB_USER"
        "API_HOST"
        "API_PORT"
        "SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$config_file"; then
            print_error "Required variable not found: $var"
            return 1
        fi
    done
    
    # Check for production-specific requirements
    if [ "$env" = "production" ]; then
        if grep -q "CHANGE_ME" "$config_file"; then
            print_error "Production configuration contains placeholder values (CHANGE_ME)"
            return 1
        fi
        
        if grep -q "DEBUG=true" "$config_file"; then
            print_error "Debug mode cannot be enabled in production"
            return 1
        fi
    fi
    
    print_success "Configuration validation passed for environment: $env"
    return 0
}

# Function to backup current .env file
backup_env_file() {
    if [ -f "$ENV_FILE" ]; then
        local backup_file="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$backup_file"
        print_success "Backed up current .env to: $backup_file"
    else
        print_warning "No existing .env file to backup"
    fi
}

# Function to apply configuration
apply_configuration() {
    local env=$1
    local config_file="${CONFIG_DIR}/${env}.env"
    
    print_info "Applying configuration for environment: $env"
    
    # Copy configuration file to .env
    cp "$config_file" "$ENV_FILE"
    
    # Add environment-specific header
    {
        echo "# Environment Configuration"
        echo "# Generated on: $(date)"
        echo "# Environment: $env"
        echo ""
        cat "$ENV_FILE"
    } > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE"
    
    print_success "Configuration applied successfully for environment: $env"
}

# Function to show configuration summary
show_config_summary() {
    local env=$1
    
    print_info "Configuration Summary for Environment: $env"
    echo "=========================================="
    
    # Show key configuration values
    if [ -f "$ENV_FILE" ]; then
        echo "Environment: $(grep '^ENVIRONMENT=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "Debug Mode: $(grep '^DEBUG=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "App Name: $(grep '^APP_NAME=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "App Version: $(grep '^APP_VERSION=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "API Host: $(grep '^API_HOST=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "API Port: $(grep '^API_PORT=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "Database: $(grep '^DB_NAME=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "Redis DB: $(grep '^REDIS_DB=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "Log Level: $(grep '^LOG_LEVEL=' "$ENV_FILE" | cut -d'=' -f2)"
        echo "Broker: $(grep '^BROKER_NAME=' "$ENV_FILE" | cut -d'=' -f2)"
    fi
    
    echo "=========================================="
}

# Function to check dependencies
check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check if config directory exists
    if [ ! -d "$CONFIG_DIR" ]; then
        print_error "Configuration directory not found: $CONFIG_DIR"
        return 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required but not installed"
        return 1
    fi
    
    print_success "Dependencies check passed"
    return 0
}

# Function to test configuration
test_configuration() {
    print_info "Testing configuration..."
    
    # Test Python configuration loading
    python3 -c "
import sys
sys.path.append('.')
try:
    from app.core.environment_config import get_config
    config = get_config()
    print(f'✓ Configuration loaded successfully')
    print(f'✓ Environment: {config.environment.value}')
    print(f'✓ Debug mode: {config.debug}')
    print(f'✓ App name: {config.app_name}')
except Exception as e:
    print(f'✗ Configuration test failed: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_success "Configuration test passed"
        return 0
    else
        print_error "Configuration test failed"
        return 1
    fi
}

# Main function
main() {
    local environment="development"
    local validate_only=false
    local backup=false
    local force=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_usage
                exit 0
                ;;
            --validate)
                validate_only=true
                shift
                ;;
            --backup)
                backup=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            development|testing|staging|production)
                environment=$1
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_info "Starting environment configuration setup..."
    
    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi
    
    # Validate configuration
    if ! validate_environment "$environment"; then
        exit 1
    fi
    
    # If validate only, exit here
    if [ "$validate_only" = true ]; then
        print_success "Validation completed successfully"
        exit 0
    fi
    
    # Confirm before applying (unless force is used)
    if [ "$force" = false ]; then
        echo ""
        print_warning "This will apply the $environment configuration to your .env file"
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Configuration application cancelled"
            exit 0
        fi
    fi
    
    # Backup current configuration if requested
    if [ "$backup" = true ]; then
        backup_env_file
    fi
    
    # Apply configuration
    apply_configuration "$environment"
    
    # Test configuration
    if ! test_configuration; then
        print_error "Configuration test failed. Please check your configuration."
        exit 1
    fi
    
    # Show summary
    show_config_summary "$environment"
    
    print_success "Environment configuration setup completed successfully!"
    print_info "You can now start the application with the $environment configuration"
}

# Run main function with all arguments
main "$@"
