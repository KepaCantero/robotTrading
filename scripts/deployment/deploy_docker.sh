#!/bin/bash
# Docker Deployment Script for AlgoTrading
# TASK-2: Dockerización completa

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="algo-trading"
ENVIRONMENT=${1:-development}
DOCKER_COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

check_environment_file() {
    log_info "Checking environment configuration..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        if [ ! -f ".env.prod" ]; then
            log_warning "Production environment file (.env.prod) not found"
            log_info "Creating template .env.prod file..."
            
            cat > .env.prod << 'EOF'
# Production Environment Configuration
# TASK-2: Dockerización completa

# Database Configuration (AWS RDS)
DATABASE_URL=postgresql://username:password@rds-endpoint:5432/algotrading

# Redis Configuration (AWS ElastiCache)
REDIS_URL=redis://redis-endpoint:6379/0

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Trading Configuration
PAPER_TRADING=true
LIVE_TRADING=false
MAX_POSITION_SIZE=0.1
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10

# Security (Change these in production!)
SECRET_KEY=change_me_in_production
JWT_SECRET_KEY=change_me_in_production

# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# Monitoring
GRAFANA_ADMIN_PASSWORD=change_me_in_production
GRAFANA_SECRET_KEY=change_me_in_production
EOF
            
            log_warning "Please update .env.prod with your actual configuration values"
        fi
        
        # Load production environment variables
        if [ -f ".env.prod" ]; then
            export $(cat .env.prod | grep -v '^#' | xargs)
        fi
    else
        if [ ! -f ".env.dev" ]; then
            log_info "Creating development environment file..."
            
            cat > .env.dev << 'EOF'
# Development Environment Configuration
# TASK-2: Dockerización completa

# Database Configuration
DATABASE_URL=postgresql://algotrading_dev:dev_password@postgres:5432/algotrading_dev

# Redis Configuration
REDIS_URL=redis://:dev_redis_password@redis:6379/0

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Trading Configuration
PAPER_TRADING=true
LIVE_TRADING=false
MAX_POSITION_SIZE=0.1
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10

# Security (Development only)
SECRET_KEY=dev_secret_key
JWT_SECRET_KEY=dev_jwt_secret

# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
EOF
        fi
        
        # Load development environment variables
        if [ -f ".env.dev" ]; then
            export $(cat .env.dev | grep -v '^#' | xargs)
        fi
    fi
    
    log_success "Environment configuration loaded"
}

build_images() {
    log_info "Building Docker images..."
    
    # Build the main application image
    docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache app
    
    # Build worker and scheduler images
    docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache worker scheduler
    
    log_success "Docker images built successfully"
}

start_services() {
    log_info "Starting services..."
    
    # Start services in dependency order
    docker-compose -f $DOCKER_COMPOSE_FILE up -d postgres redis
    
    # Wait for database and cache to be ready
    log_info "Waiting for database and cache to be ready..."
    sleep 10
    
    # Start the main application
    docker-compose -f $DOCKER_COMPOSE_FILE up -d app
    
    # Start background services
    docker-compose -f $DOCKER_COMPOSE_FILE up -d worker scheduler
    
    # Start monitoring services
    docker-compose -f $DOCKER_COMPOSE_FILE up -d nginx prometheus grafana
    
    # Start additional services for development
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $DOCKER_COMPOSE_FILE up -d flower
    fi
    
    # Start logging services for production
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f $DOCKER_COMPOSE_FILE up -d elasticsearch logstash kibana
    fi
    
    log_success "Services started successfully"
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    # Wait for the application to be ready
    sleep 15
    
    # Run migrations
    docker-compose -f $DOCKER_COMPOSE_FILE exec app python -m alembic upgrade head
    
    log_success "Database migrations completed"
}

check_health() {
    log_info "Checking service health..."
    
    # Check application health
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "Application is healthy"
            break
        else
            log_info "Waiting for application to be ready... (attempt $attempt/$max_attempts)"
            sleep 5
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "Application failed to become healthy"
        return 1
    fi
    
    # Check other services
    docker-compose -f $DOCKER_COMPOSE_FILE ps
    
    log_success "Health check completed"
}

show_service_urls() {
    log_info "Service URLs:"
    
    echo ""
    echo "🌐 Application:"
    echo "   - API: http://localhost:8000"
    echo "   - Docs: http://localhost:8000/docs"
    echo "   - Health: http://localhost:8000/health"
    
    if [ "$ENVIRONMENT" = "development" ]; then
        echo ""
        echo "🔧 Development Tools:"
        echo "   - Flower (Celery): http://localhost:5555"
        echo "   - Prometheus: http://localhost:9090"
        echo "   - Grafana: http://localhost:3000 (admin/admin)"
    else
        echo ""
        echo "📊 Monitoring:"
        echo "   - Prometheus: http://localhost:9090"
        echo "   - Grafana: http://localhost:3000"
        echo "   - Kibana: http://localhost:5601"
    fi
    
    echo ""
    echo "🗄️ Databases:"
    echo "   - PostgreSQL: localhost:5432"
    echo "   - Redis: localhost:6379"
    
    echo ""
}

cleanup_old_containers() {
    log_info "Cleaning up old containers..."
    
    # Stop and remove old containers
    docker-compose -f $DOCKER_COMPOSE_FILE down --remove-orphans
    
    # Remove unused images
    docker image prune -f
    
    log_success "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting Docker deployment for $PROJECT_NAME ($ENVIRONMENT environment)..."
    
    check_prerequisites
    check_environment_file
    cleanup_old_containers
    build_images
    start_services
    run_database_migrations
    check_health
    show_service_urls
    
    log_success "Docker deployment completed successfully!"
    log_info "Use 'docker-compose -f $DOCKER_COMPOSE_FILE logs -f' to view logs"
    log_info "Use 'docker-compose -f $DOCKER_COMPOSE_FILE down' to stop services"
}

# Run main function
main "$@"
