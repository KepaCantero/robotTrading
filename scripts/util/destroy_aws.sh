#!/bin/bash
# AWS Infrastructure Destruction Script
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

confirm_destruction() {
    log_warning "This will DESTROY all AWS infrastructure for $PROJECT_NAME"
    log_warning "This action is IRREVERSIBLE and will result in DATA LOSS"
    echo
    read -p "Are you sure you want to continue? Type 'yes' to confirm: " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log_info "Destruction cancelled"
        exit 0
    fi
}

destroy_infrastructure() {
    log_info "Destroying AWS infrastructure with Terraform..."
    
    cd $TERRAFORM_DIR
    
    # Plan destruction
    terraform plan -destroy -out=destroy.tfplan
    
    # Apply destruction
    log_warning "Applying destruction plan..."
    terraform apply destroy.tfplan
    
    log_success "Infrastructure destroyed successfully"
    
    cd - > /dev/null
}

cleanup_secrets() {
    log_info "Cleaning up AWS Secrets Manager secrets..."
    
    # List secrets
    SECRETS=$(aws secretsmanager list-secrets \
        --query "SecretList[?starts_with(Name, '$PROJECT_NAME/')].Name" \
        --output text \
        --region $AWS_REGION)
    
    if [ -n "$SECRETS" ]; then
        for secret in $SECRETS; do
            log_info "Deleting secret: $secret"
            aws secretsmanager delete-secret \
                --secret-id "$secret" \
                --force-delete-without-recovery \
                --region $AWS_REGION
        done
        log_success "Secrets cleaned up"
    else
        log_info "No secrets found to clean up"
    fi
}

cleanup_monitoring() {
    log_info "Cleaning up CloudWatch resources..."
    
    # Delete dashboard
    aws cloudwatch delete-dashboards \
        --dashboard-names "${PROJECT_NAME}-dashboard" \
        --region $AWS_REGION 2>/dev/null || true
    
    # Delete alarms
    ALARMS=$(aws cloudwatch describe-alarms \
        --alarm-names "${PROJECT_NAME}-high-cpu" "${PROJECT_NAME}-high-memory" "${PROJECT_NAME}-db-connections" \
        --query "MetricAlarms[].AlarmName" \
        --output text \
        --region $AWS_REGION 2>/dev/null || true)
    
    if [ -n "$ALARMS" ]; then
        aws cloudwatch delete-alarms \
            --alarm-names $ALARMS \
            --region $AWS_REGION
        log_success "CloudWatch alarms deleted"
    fi
    
    log_success "CloudWatch resources cleaned up"
}

cleanup_key_pair() {
    log_info "Cleaning up EC2 key pair..."
    
    KEY_NAME="${PROJECT_NAME}-key"
    
    if aws ec2 describe-key-pairs --key-names $KEY_NAME &> /dev/null; then
        aws ec2 delete-key-pair --key-name $KEY_NAME
        rm -f "${KEY_NAME}.pem"
        log_success "EC2 key pair deleted"
    else
        log_info "EC2 key pair not found"
    fi
}

cleanup_s3_bucket() {
    log_info "Cleaning up S3 bucket..."
    
    # Find Terraform state bucket
    BUCKETS=$(aws s3api list-buckets \
        --query "Buckets[?starts_with(Name, '$PROJECT_NAME-terraform-state')].Name" \
        --output text \
        --region $AWS_REGION)
    
    if [ -n "$BUCKETS" ]; then
        for bucket in $BUCKETS; do
            log_info "Deleting S3 bucket: $bucket"
            
            # Delete all objects
            aws s3 rm "s3://$bucket" --recursive
            
            # Delete bucket
            aws s3api delete-bucket --bucket "$bucket" --region $AWS_REGION
            
            log_success "S3 bucket deleted: $bucket"
        done
    else
        log_info "No S3 buckets found to clean up"
    fi
}

cleanup_log_groups() {
    log_info "Cleaning up CloudWatch log groups..."
    
    LOG_GROUPS=$(aws logs describe-log-groups \
        --log-group-name-prefix "/aws/ec2/$PROJECT_NAME" \
        --query "logGroups[].logGroupName" \
        --output text \
        --region $AWS_REGION 2>/dev/null || true)
    
    if [ -n "$LOG_GROUPS" ]; then
        for log_group in $LOG_GROUPS; do
            log_info "Deleting log group: $log_group"
            aws logs delete-log-group --log-group-name "$log_group" --region $AWS_REGION
        done
        log_success "CloudWatch log groups deleted"
    else
        log_info "No log groups found to clean up"
    fi
}

generate_cleanup_summary() {
    log_info "Generating cleanup summary..."
    
    cat > infrastructure/cleanup_summary.md << EOF
# AWS Infrastructure Cleanup Summary

## Cleanup Information
- **Project**: $PROJECT_NAME
- **Region**: $AWS_REGION
- **Cleanup Date**: $(date)

## Cleaned Up Resources

### Infrastructure
- ✅ EC2 Instance
- ✅ RDS Database
- ✅ ElastiCache Redis
- ✅ VPC and Subnets
- ✅ Security Groups
- ✅ Internet Gateway
- ✅ Route Tables

### Monitoring
- ✅ CloudWatch Dashboard
- ✅ CloudWatch Alarms
- ✅ CloudWatch Log Groups

### Security
- ✅ EC2 Key Pair
- ✅ AWS Secrets Manager Secrets

### Storage
- ✅ S3 Bucket (Terraform State)

## Notes

- All data has been permanently deleted
- No backups were created during cleanup
- Infrastructure can be recreated using the deployment script
- Consider creating snapshots before destruction in the future

## Cost Impact

- All AWS resources have been terminated
- No ongoing charges will be incurred
- Check AWS Billing Console for final charges
EOF
    
    log_success "Cleanup summary generated: infrastructure/cleanup_summary.md"
}

# Main execution
main() {
    log_warning "Starting AWS infrastructure cleanup for $PROJECT_NAME..."
    
    confirm_destruction
    
    destroy_infrastructure
    cleanup_secrets
    cleanup_monitoring
    cleanup_key_pair
    cleanup_s3_bucket
    cleanup_log_groups
    generate_cleanup_summary
    
    log_success "AWS infrastructure cleanup completed successfully!"
    log_info "Check infrastructure/cleanup_summary.md for details"
}

# Run main function
main "$@"
