#!/bin/bash

# ELK Stack Deployment Script for AlgoTrading
# TASK-3: Configuración de logging centralizado

set -e

echo "🚀 Starting ELK Stack deployment for AlgoTrading..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create log directories
echo "📁 Creating log directories..."
mkdir -p logs/fastapi
mkdir -p logs/trading
mkdir -p logs/market_data
mkdir -p logs/portfolio
mkdir -p logs/errors
mkdir -p logs/performance

# Set permissions
chmod 755 logs/
chmod 755 logs/*/

# Check if ELK Stack is already running
if docker-compose -f docker-compose.logging.yml ps | grep -q "Up"; then
    echo "⚠️  ELK Stack is already running. Stopping existing containers..."
    docker-compose -f docker-compose.logging.yml down
fi

# Start ELK Stack
echo "🐳 Starting ELK Stack containers..."
docker-compose -f docker-compose.logging.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."

# Wait for Elasticsearch
echo "🔍 Waiting for Elasticsearch..."
until curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; do
    echo "   Elasticsearch is not ready yet..."
    sleep 5
done
echo "✅ Elasticsearch is ready!"

# Wait for Kibana
echo "📊 Waiting for Kibana..."
until curl -s http://localhost:5601/api/status > /dev/null 2>&1; do
    echo "   Kibana is not ready yet..."
    sleep 5
done
echo "✅ Kibana is ready!"

# Wait for Logstash
echo "📝 Waiting for Logstash..."
sleep 10
echo "✅ Logstash is ready!"

# Wait for Filebeat
echo "📄 Waiting for Filebeat..."
sleep 5
echo "✅ Filebeat is ready!"

# Create index patterns in Kibana
echo "🔧 Setting up Kibana index patterns..."
curl -X POST "http://localhost:5601/api/saved_objects/index-pattern/algotrading-logs-*" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "title": "algotrading-logs-*",
      "timeFieldName": "@timestamp"
    }
  }' > /dev/null 2>&1 || echo "⚠️  Index pattern creation failed (may already exist)"

# Create sample dashboard
echo "📈 Creating sample dashboard..."
curl -X POST "http://localhost:5601/api/saved_objects/dashboard/algotrading-dashboard" \
  -H "kbn-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "title": "AlgoTrading Logs Dashboard",
      "description": "Dashboard for AlgoTrading application logs",
      "panelsJSON": "[]",
      "optionsJSON": "{\"darkTheme\":false}",
      "version": 1,
      "timeRestore": false,
      "kibanaSavedObjectMeta": {
        "searchSourceJSON": "{\"query\":{\"query\":\"\",\"language\":\"kuery\"},\"filter\":[]}"
      }
    }
  }' > /dev/null 2>&1 || echo "⚠️  Dashboard creation failed (may already exist)"

# Display status
echo ""
echo "🎉 ELK Stack deployment completed successfully!"
echo ""
echo "📊 Services Status:"
docker-compose -f docker-compose.logging.yml ps
echo ""
echo "🌐 Access URLs:"
echo "   Elasticsearch: http://localhost:9200"
echo "   Kibana: http://localhost:5601"
echo "   Logstash: localhost:5044-5049"
echo ""
echo "📁 Log directories created:"
echo "   logs/fastapi/"
echo "   logs/trading/"
echo "   logs/market_data/"
echo "   logs/portfolio/"
echo "   logs/errors/"
echo "   logs/performance/"
echo ""
echo "🔧 Next steps:"
echo "   1. Configure your application to use the centralized logging service"
echo "   2. Access Kibana at http://localhost:5601"
echo "   3. Create index patterns and dashboards as needed"
echo "   4. Monitor logs in real-time"
echo ""
echo "📚 Documentation:"
echo "   - Centralized Logging Service: app/services/centralized_logging.py"
echo "   - Logging Middleware: app/middleware/logging_middleware.py"
echo "   - Configuration files: logging/"
echo ""
echo "✅ ELK Stack is ready for use!"
