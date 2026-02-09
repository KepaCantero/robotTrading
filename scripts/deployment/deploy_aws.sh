#!/bin/bash
# AWS Infrastructure Deployment Script
# TASK-1: Configuración base de AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="algo-trading"
AWS_REGION="us-east-1"
ENVIRONMENT="production"
TERRAFORM_DIR="infrastructure/terraform"

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
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

create_s3_bucket() {
    log_info "Creating S3 bucket for Terraform state..."
    
    BUCKET_NAME="${PROJECT_NAME}-terraform-state-$(date +%s)"
    
    if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
        aws s3 mb "s3://$BUCKET_NAME" --region $AWS_REGION
        log_success "S3 bucket created: $BUCKET_NAME"
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket $BUCKET_NAME \
            --versioning-configuration Status=Enabled
        
        # Enable server-side encryption
        aws s3api put-bucket-encryption \
            --bucket $BUCKET_NAME \
            --server-side-encryption-configuration '{
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }'
        
        log_success "S3 bucket configured with versioning and encryption"
    else
        log_warning "S3 bucket already exists: $BUCKET_NAME"
    fi
    
    echo $BUCKET_NAME
}

create_key_pair() {
    log_info "Creating EC2 key pair..."
    
    KEY_NAME="${PROJECT_NAME}-key"
    
    if ! aws ec2 describe-key-pairs --key-names $KEY_NAME &> /dev/null; then
        aws ec2 create-key-pair \
            --key-name $KEY_NAME \
            --query 'KeyMaterial' \
            --output text > "${KEY_NAME}.pem"
        
        chmod 400 "${KEY_NAME}.pem"
        log_success "EC2 key pair created: $KEY_NAME"
    else
        log_warning "EC2 key pair already exists: $KEY_NAME"
    fi
}

deploy_infrastructure() {
    log_info "Deploying AWS infrastructure with Terraform..."
    
    cd $TERRAFORM_DIR
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan \
        -var="aws_region=$AWS_REGION" \
        -var="environment=$ENVIRONMENT" \
        -var="project_name=$PROJECT_NAME" \
        -out=tfplan
    
    # Apply deployment
    log_info "Applying Terraform configuration..."
    terraform apply tfplan
    
    log_success "Infrastructure deployed successfully"
    
    # Save outputs
    terraform output -json > ../outputs.json
    
    cd - > /dev/null
}

create_secrets() {
    log_info "Creating AWS Secrets Manager secrets..."
    
    # Database password
    DB_PASSWORD=$(openssl rand -base64 32)
    aws secretsmanager create-secret \
        --name "${PROJECT_NAME}/database/password" \
        --description "Database password for AlgoTrading" \
        --secret-string "$DB_PASSWORD" \
        --region $AWS_REGION
    
    # Application secret key
    SECRET_KEY=$(openssl rand -base64 64)
    aws secretsmanager create-secret \
        --name "${PROJECT_NAME}/app/secret-key" \
        --description "Application secret key for AlgoTrading" \
        --secret-string "$SECRET_KEY" \
        --region $AWS_REGION
    
    # JWT secret key
    JWT_SECRET=$(openssl rand -base64 64)
    aws secretsmanager create-secret \
        --name "${PROJECT_NAME}/app/jwt-secret" \
        --description "JWT secret key for AlgoTrading" \
        --secret-string "$JWT_SECRET" \
        --region $AWS_REGION
    
    log_success "Secrets created in AWS Secrets Manager"
}

setup_monitoring() {
    log_info "Setting up CloudWatch monitoring..."
    
    # Create CloudWatch dashboard
    aws cloudwatch put-dashboard \
        --dashboard-name "${PROJECT_NAME}-dashboard" \
        --dashboard-body '{
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "CPUUtilization", "InstanceId", "i-1234567890abcdef0"],
                            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "algo-trading-db"],
                            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "algo-trading-redis"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "'$AWS_REGION'",
                        "title": "System CPU Utilization"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "NetworkIn", "InstanceId", "i-1234567890abcdef0"],
                            ["AWS/EC2", "NetworkOut", "InstanceId", "i-1234567890abcdef0"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "'$AWS_REGION'",
                        "title": "Network Traffic"
                    }
                }
            ]
        }' \
        --region $AWS_REGION
    
    log_success "CloudWatch dashboard created"
}

create_alarms() {
    log_info "Creating CloudWatch alarms..."
    
    # High CPU alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${PROJECT_NAME}-high-cpu" \
        --alarm-description "High CPU utilization" \
        --metric-name CPUUtilization \
        --namespace AWS/EC2 \
        --statistic Average \
        --period 300 \
        --threshold 80 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --region $AWS_REGION
    
    # High memory alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${PROJECT_NAME}-high-memory" \
        --alarm-description "High memory utilization" \
        --metric-name MemoryUtilization \
        --namespace AlgoTrading/EC2 \
        --statistic Average \
        --period 300 \
        --threshold 85 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --region $AWS_REGION
    
    # Database connection alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${PROJECT_NAME}-db-connections" \
        --alarm-description "High database connections" \
        --metric-name DatabaseConnections \
        --namespace AWS/RDS \
        --statistic Average \
        --period 300 \
        --threshold 80 \
        --comparison-operator GreaterThanThreshold \
        --evaluation-periods 2 \
        --region $AWS_REGION
    
    log_success "CloudWatch alarms created"
}

generate_deployment_summary() {
    log_info "Generating deployment summary..."
    
    cd $TERRAFORM_DIR
    
    cat > ../deployment_summary.md << EOF
# AWS Infrastructure Deployment Summary

## Deployment Information
- **Project**: $PROJECT_NAME
- **Environment**: $ENVIRONMENT
- **Region**: $AWS_REGION
- **Deployment Date**: $(date)

## Infrastructure Components

### EC2 Instance
- **Instance ID**: $(terraform output -raw ec2_instance_id)
- **Public IP**: $(terraform output -raw ec2_public_ip)
- **Instance Type**: $(terraform output -raw instance_type)

### RDS Database
- **Endpoint**: $(terraform output -raw rds_endpoint)
- **Engine**: PostgreSQL 15.4
- **Instance Class**: $(terraform output -raw db_instance_class)

### ElastiCache Redis
- **Endpoint**: $(terraform output -raw redis_endpoint)
- **Engine**: Redis 7.0
- **Node Type**: $(terraform output -raw redis_node_type)

### Security Groups
- **Web SG**: $(terraform output -raw security_group_web)
- **Database SG**: $(terraform output -raw security_group_database)
- **Cache SG**: $(terraform output -raw security_group_cache)

## Next Steps

1. **SSH Access**: Use the generated key pair to access the EC2 instance
2. **Application Deployment**: Clone the repository and deploy the application
3. **Database Setup**: Run migrations and seed data
4. **Monitoring**: Check CloudWatch dashboard and alarms
5. **SSL Certificate**: Configure SSL certificate for HTTPS

## Security Notes

- Change default passwords in production
- Restrict SSH access to specific IPs
- Enable VPC Flow Logs
- Set up AWS Config for compliance monitoring
- Regular security updates and patches

## Cost Optimization

- Monitor usage and adjust instance sizes
- Use Spot Instances for non-critical workloads
- Implement auto-scaling policies
- Regular cleanup of unused resources
EOF
    
    cd - > /dev/null
    
    log_success "Deployment summary generated: infrastructure/deployment_summary.md"
}

# Main execution
main() {
    log_info "Starting AWS infrastructure deployment for $PROJECT_NAME..."
    
    check_prerequisites
    BUCKET_NAME=$(create_s3_bucket)
    create_key_pair
    deploy_infrastructure
    create_secrets
    setup_monitoring
    create_alarms
    generate_deployment_summary
    
    log_success "AWS infrastructure deployment completed successfully!"
    log_info "Check infrastructure/deployment_summary.md for details"
}

# Run main function
main "$@"
