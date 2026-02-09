#!/bin/bash

# Database Initialization Script
# TASK-6: Configuración de base de datos

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="algotrading"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

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
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  init        - Initialize database and create tables"
    echo "  migrate     - Run database migrations"
    echo "  reset       - Reset database (drop and recreate)"
    echo "  seed        - Seed database with sample data"
    echo "  backup      - Create database backup"
    echo "  restore     - Restore database from backup"
    echo "  health      - Check database health"
    echo ""
    echo "Options:"
    echo "  --help, -h  - Show this help message"
    echo "  --env ENV   - Use specific environment (dev/test/prod)"
    echo "  --force     - Force operation without confirmation"
    echo ""
    echo "Examples:"
    echo "  $0 init"
    echo "  $0 migrate --env production"
    echo "  $0 reset --force"
    echo "  $0 seed --env development"
}

# Function to check database connection
check_database_connection() {
    local env=${1:-development}
    
    print_info "Checking database connection for environment: $env"
    
    # Load environment variables
    if [ -f "config/${env}.env" ]; then
        export $(cat "config/${env}.env" | grep -v '^#' | xargs)
    fi
    
    # Test connection
    if command -v psql &> /dev/null; then
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -c "SELECT 1;" &> /dev/null; then
            print_success "Database connection successful"
            return 0
        else
            print_error "Database connection failed"
            return 1
        fi
    else
        print_warning "psql not found, skipping connection test"
        return 0
    fi
}

# Function to create database
create_database() {
    local env=${1:-development}
    
    print_info "Creating database for environment: $env"
    
    # Load environment variables
    if [ -f "config/${env}.env" ]; then
        export $(cat "config/${env}.env" | grep -v '^#' | xargs)
    fi
    
    # Check if database exists
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        print_warning "Database '$DB_NAME' already exists"
    else
        print_info "Creating database '$DB_NAME'"
        PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
        print_success "Database '$DB_NAME' created successfully"
    fi
}

# Function to initialize database
initialize_database() {
    local env=${1:-development}
    
    print_info "Initializing database for environment: $env"
    
    # Check connection
    if ! check_database_connection "$env"; then
        print_error "Cannot connect to database"
        exit 1
    fi
    
    # Create database if it doesn't exist
    create_database "$env"
    
    # Initialize Python environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    
    # Run database initialization
    python -c "
from app.database import initialize_database
try:
    initialize_database()
    print('Database initialization completed successfully')
except Exception as e:
    print(f'Database initialization failed: {e}')
    exit(1)
"
    
    print_success "Database initialization completed"
}

# Function to run migrations
run_migrations() {
    local env=${1:-development}
    
    print_info "Running database migrations for environment: $env"
    
    # Load environment variables
    if [ -f "config/${env}.env" ]; then
        export $(cat "config/${env}.env" | grep -v '^#' | xargs)
    fi
    
    # Initialize Python environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    
    # Run Alembic migrations
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
        print_success "Database migrations completed"
    else
        print_error "Alembic configuration not found"
        exit 1
    fi
}

# Function to reset database
reset_database() {
    local env=${1:-development}
    local force=${2:-false}
    
    print_warning "Resetting database for environment: $env"
    
    if [ "$force" != "true" ]; then
        read -p "Are you sure you want to reset the database? This will delete all data! (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Database reset cancelled"
            exit 0
        fi
    fi
    
    # Load environment variables
    if [ -f "config/${env}.env" ]; then
        export $(cat "config/${env}.env" | grep -v '^#' | xargs)
    fi
    
    # Drop and recreate database
    print_info "Dropping database '$DB_NAME'"
    PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" --if-exists
    
    print_info "Creating database '$DB_NAME'"
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"
    
    # Initialize database
    initialize_database "$env"
    
    print_success "Database reset completed"
}

# Function to seed database
seed_database() {
    local env=${1:-development}
    
    print_info "Seeding database for environment: $env"
    
    # Initialize Python environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    
    # Run database seeding
    python -c "
from app.database import initialize_database
from app.database.models import User, Asset, Portfolio
from app.database.repositories import UserRepository, AssetRepository, PortfolioRepository
from app.database import db_manager
from decimal import Decimal
import uuid

try:
    # Initialize database
    initialize_database()
    
    # Get session
    session = db_manager.get_sync_session()
    
    # Create repositories
    user_repo = UserRepository(User, session)
    asset_repo = AssetRepository(Asset, session)
    portfolio_repo = PortfolioRepository(Portfolio, session)
    
    # Create sample user
    user = user_repo.create(
        username='demo_user',
        email='demo@example.com',
        hashed_password='hashed_password_demo'
    )
    print(f'Created user: {user.username}')
    
    # Create sample assets
    assets = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_class': 'stock', 'exchange': 'NASDAQ'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'asset_class': 'stock', 'exchange': 'NASDAQ'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'asset_class': 'stock', 'exchange': 'NASDAQ'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'asset_class': 'stock', 'exchange': 'NASDAQ'},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'asset_class': 'stock', 'exchange': 'NASDAQ'},
    ]
    
    for asset_data in assets:
        asset = asset_repo.create(**asset_data)
        print(f'Created asset: {asset.symbol}')
    
    # Create sample portfolio
    portfolio = portfolio_repo.create(
        user_id=user.id,
        name='Demo Portfolio',
        description='Sample portfolio for demonstration',
        initial_cash=Decimal('100000.00'),
        current_cash=Decimal('100000.00'),
        total_value=Decimal('100000.00')
    )
    print(f'Created portfolio: {portfolio.name}')
    
    session.close()
    print('Database seeding completed successfully')
    
except Exception as e:
    print(f'Database seeding failed: {e}')
    exit(1)
"
    
    print_success "Database seeding completed"
}

# Function to backup database
backup_database() {
    local env=${1:-development}
    local backup_file="backup_${env}_$(date +%Y%m%d_%H%M%S).sql"
    
    print_info "Creating database backup for environment: $env"
    
    # Load environment variables
    if [ -f "config/${env}.env" ]; then
        export $(cat "config/${env}.env" | grep -v '^#' | xargs)
    fi
    
    # Create backup
    PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" > "$backup_file"
    
    print_success "Database backup created: $backup_file"
}

# Function to restore database
restore_database() {
    local env=${1:-development}
    local backup_file=${2:-""}
    
    if [ -z "$backup_file" ]; then
        print_error "Backup file not specified"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    print_warning "Restoring database from backup: $backup_file"
    read -p "Are you sure you want to restore the database? This will overwrite existing data! (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Database restore cancelled"
        exit 0
    fi
    
    # Load environment variables
    if [ -f "config/${env}.env" ]; then
        export $(cat "config/${env}.env" | grep -v '^#' | xargs)
    fi
    
    # Restore database
    print_info "Restoring database from backup"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" < "$backup_file"
    
    print_success "Database restore completed"
}

# Function to check database health
check_database_health() {
    local env=${1:-development}
    
    print_info "Checking database health for environment: $env"
    
    # Initialize Python environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
    
    # Run health check
    python -c "
from app.database import check_database_health
try:
    if check_database_health():
        print('Database health check: PASSED')
    else:
        print('Database health check: FAILED')
        exit(1)
except Exception as e:
    print(f'Database health check failed: {e}')
    exit(1)
"
    
    print_success "Database health check completed"
}

# Main function
main() {
    local command=""
    local env="development"
    local force=false
    local backup_file=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_usage
                exit 0
                ;;
            --env)
                env="$2"
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            init|migrate|reset|seed|backup|restore|health)
                command="$1"
                shift
                ;;
            *)
                if [ -z "$command" ]; then
                    print_error "Unknown command: $1"
                    show_usage
                    exit 1
                else
                    backup_file="$1"
                    shift
                fi
                ;;
        esac
    done
    
    if [ -z "$command" ]; then
        print_error "No command specified"
        show_usage
        exit 1
    fi
    
    print_info "Starting database operation: $command"
    
    case $command in
        init)
            initialize_database "$env"
            ;;
        migrate)
            run_migrations "$env"
            ;;
        reset)
            reset_database "$env" "$force"
            ;;
        seed)
            seed_database "$env"
            ;;
        backup)
            backup_database "$env"
            ;;
        restore)
            restore_database "$env" "$backup_file"
            ;;
        health)
            check_database_health "$env"
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
    
    print_success "Database operation completed successfully"
}

# Run main function with all arguments
main "$@"
