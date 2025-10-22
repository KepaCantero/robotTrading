#!/bin/bash
# User Data Script for AlgoTrading EC2 Instance
# TASK-1: Configuración base de AWS

# Log all output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Python 3.11 and pip
yum install -y python3 python3-pip git

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create application directory
mkdir -p /opt/algo-trading
cd /opt/algo-trading

# Clone repository (replace with actual repository URL)
# git clone https://github.com/your-org/algo-trading.git .

# Create environment file
cat > /opt/algo-trading/.env << EOF
# Database Configuration
DATABASE_URL=postgresql://algotrading_admin:temp_password_change_me@${db_endpoint}:5432/algotrading

# Redis Configuration
REDIS_URL=redis://${redis_endpoint}:6379/0

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# Trading Configuration
PAPER_TRADING=true
LIVE_TRADING=false
MAX_POSITION_SIZE=0.1
STOP_LOSS_PCT=0.05
TAKE_PROFIT_PCT=0.10

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
SECRET_KEY=change_me_in_production
JWT_SECRET_KEY=change_me_in_production
EOF

# Create docker-compose.yml
cat > /opt/algo-trading/docker-compose.yml << 'EOF'
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - ENVIRONMENT=${ENVIRONMENT}
      - DEBUG=${DEBUG}
      - LOG_LEVEL=${LOG_LEVEL}
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
EOF

# Create nginx configuration
cat > /opt/algo-trading/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://app/health;
            access_log off;
        }
    }
}
EOF

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root"
    },
    "metrics": {
        "namespace": "AlgoTrading/EC2",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 60
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/algo-trading",
                        "log_stream_name": "{instance_id}/user-data.log"
                    },
                    {
                        "file_path": "/opt/algo-trading/logs/app.log",
                        "log_group_name": "/aws/ec2/algo-trading",
                        "log_stream_name": "{instance_id}/app.log"
                    }
                ]
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Create systemd service for the application
cat > /etc/systemd/system/algo-trading.service << 'EOF'
[Unit]
Description=AlgoTrading Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/algo-trading
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl enable algo-trading.service

# Create log rotation configuration
cat > /etc/logrotate.d/algo-trading << 'EOF'
/opt/algo-trading/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
    postrotate
        systemctl reload algo-trading.service
    endscript
}
EOF

# Set proper permissions
chown -R ec2-user:ec2-user /opt/algo-trading
chmod +x /opt/algo-trading/docker-compose.yml

# Create monitoring script
cat > /opt/algo-trading/monitor.sh << 'EOF'
#!/bin/bash
# Monitoring script for AlgoTrading

LOG_FILE="/opt/algo-trading/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check if Docker is running
if ! systemctl is-active --quiet docker; then
    echo "[$DATE] ERROR: Docker is not running" >> $LOG_FILE
    systemctl start docker
fi

# Check if application containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "[$DATE] ERROR: Application containers are not running" >> $LOG_FILE
    cd /opt/algo-trading && docker-compose up -d
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "[$DATE] WARNING: Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEM_USAGE -gt 80 ]; then
    echo "[$DATE] WARNING: Memory usage is ${MEM_USAGE}%" >> $LOG_FILE
fi

echo "[$DATE] INFO: System check completed" >> $LOG_FILE
EOF

chmod +x /opt/algo-trading/monitor.sh

# Add monitoring to crontab
echo "*/5 * * * * /opt/algo-trading/monitor.sh" | crontab -u ec2-user -

# Create backup script
cat > /opt/algo-trading/backup.sh << 'EOF'
#!/bin/bash
# Backup script for AlgoTrading

BACKUP_DIR="/opt/algo-trading/backups"
DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="algo-trading-backup-$DATE.tar.gz"

mkdir -p $BACKUP_DIR

# Backup application data
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    --exclude='logs' \
    --exclude='backups' \
    --exclude='.git' \
    /opt/algo-trading

# Keep only last 7 backups
cd $BACKUP_DIR
ls -t algo-trading-backup-*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: $BACKUP_FILE"
EOF

chmod +x /opt/algo-trading/backup.sh

# Add backup to crontab (daily at 2 AM)
echo "0 2 * * * /opt/algo-trading/backup.sh" | crontab -u ec2-user -

# Signal completion
echo "User data script completed successfully" > /tmp/user-data-complete

# Start the application (commented out until repository is cloned)
# systemctl start algo-trading.service
