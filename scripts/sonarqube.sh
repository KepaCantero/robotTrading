#!/usr/bin/env bash
# ============================================================================
# SonarQube Analysis Script - AlgoTrading
# ============================================================================
# Usage: ./scripts/sonarqube.sh [--setup|--analyze|--teardown|--full]
#
# --setup     : Start SonarQube Docker container + install scanner
# --analyze   : Run the analysis
# --teardown  : Stop and remove the Docker container
# --full      : Setup + Analyze (default)
# ============================================================================

set -euo pipefail

# --- Config ---
SONARQUBE_CONTAINER="sonarqube-algotrading"
SONARQUBE_PORT=9000
SONARQUBE_IMAGE="sonarqube:community"
SONARQUBE_URL="http://localhost:${SONARQUBE_PORT}"
SONAR_TOKEN=""
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[SONAR]${NC} $*"; }
warn() { echo -e "${YELLOW}[SONAR]${NC} $*"; }
err()  { echo -e "${RED}[SONAR]${NC} $*" >&2; }

# ============================================================================
# SETUP: Start SonarQube + install scanner
# ============================================================================
setup() {
    log "Checking prerequisites..."

    # --- Docker ---
    if ! command -v docker &>/dev/null; then
        err "Docker not found. Install: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        err "Docker daemon not running. Start Docker Desktop or run: open -a Docker"
        exit 1
    fi

    # --- Start SonarQube container ---
    if docker ps -a --format '{{.Names}}' | grep -q "^${SONARQUBE_CONTAINER}$"; then
        if docker ps --format '{{.Names}}' | grep -q "^${SONARQUBE_CONTAINER}$"; then
            log "SonarQube container already running on port ${SONARQUBE_PORT}"
        else
            log "Starting existing SonarQube container..."
            docker start "${SONARQUBE_CONTAINER}"
        fi
    else
        log "Pulling and starting SonarQube ${SONARQUBE_IMAGE}..."
        docker run -d \
            --name "${SONARQUBE_CONTAINER}" \
            -p "${SONARQUBE_PORT}:9000" \
            -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true \
            "${SONARQUBE_IMAGE}"
    fi

    # --- Wait for SonarQube to be ready ---
    log "Waiting for SonarQube to start (this takes ~60-90s on first run)..."
    local max_attempts=60
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "${SONARQUBE_URL}/api/system/status" 2>/dev/null | grep -q '"status":"UP"'; then
            log "SonarQube is UP!"
            break
        fi
        attempt=$((attempt + 1))
        printf "\r  Waiting... [%d/%d]" $attempt $max_attempts
        sleep 3
    done
    echo ""

    if [ $attempt -eq $max_attempts ]; then
        err "SonarQube failed to start. Check: docker logs ${SONARQUBE_CONTAINER}"
        exit 1
    fi

    # --- Install sonar-scanner ---
    if command -v sonar-scanner &>/dev/null; then
        log "sonar-scanner already installed: $(sonar-scanner -v 2>&1 | head -1)"
    else
        log "Installing sonar-scanner..."
        if [[ "$(uname)" == "Darwin" ]]; then
            brew install sonar-scanner
        else
            err "Install sonar-scanner manually: https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/"
            exit 1
        fi
    fi

    # --- Generate token ---
    log "Creating analysis token..."
    SONAR_TOKEN=$(curl -sf -u admin:admin \
        -X POST "${SONARQUBE_URL}/api/user_tokens/generate" \
        -d "name=algotrading-$(date +%Y%m%d%H%M%S)" \
        2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || true)

    if [ -z "${SONAR_TOKEN}" ]; then
        warn "Could not auto-generate token. Using default admin credentials."
        warn "You may need to log in at ${SONARQUBE_URL} (admin/admin) and generate a token manually."
    else
        log "Token generated successfully."
    fi

    echo ""
    log "Setup complete!"
    log "  Dashboard: ${SONARQUBE_URL}"
    log "  Login:     admin / admin"
    if [ -n "${SONAR_TOKEN}" ]; then
        log "  Token:     ${SONAR_TOKEN}"
    fi
}

# ============================================================================
# ANALYZE: Run SonarQube scanner
# ============================================================================
analyze() {
    cd "${PROJECT_DIR}"

    if [ ! -f "sonar-project.properties" ]; then
        err "sonar-project.properties not found in ${PROJECT_DIR}"
        exit 1
    fi

    # Check SonarQube is reachable
    if ! curl -sf "${SONARQUBE_URL}/api/system/status" &>/dev/null; then
        err "SonarQube not reachable at ${SONARQUBE_URL}. Run with --setup first."
        exit 1
    fi

    # Check scanner is installed
    if ! command -v sonar-scanner &>/dev/null; then
        err "sonar-scanner not found. Run with --setup first."
        exit 1
    fi

    log "Running SonarQube analysis..."
    log "  Project:  ${PROJECT_DIR}"
    log "  Sources:  app/ (636 files), tests/ (1150 files)"
    echo ""

    local scan_cmd="sonar-scanner"

    if [ -n "${SONAR_TOKEN}" ]; then
        scan_cmd="${scan_cmd} -Dsonar.login=${SONAR_TOKEN}"
    else
        scan_cmd="${scan_cmd} -Dsonar.login=admin -Dsonar.password=admin"
    fi

    ${scan_cmd} \
        -Dsonar.host.url="${SONARQUBE_URL}"

    echo ""
    log "Analysis complete!"
    log "  View results: ${SONARQUBE_URL}/dashboard?id=algotrading"
}

# ============================================================================
# TEARDOWN: Stop and remove container
# ============================================================================
teardown() {
    log "Stopping SonarQube container..."
    docker stop "${SONARQUBE_CONTAINER}" 2>/dev/null || true
    docker rm "${SONARQUBE_CONTAINER}" 2>/dev/null || true
    log "Container removed."
}

# ============================================================================
# Main
# ============================================================================
ACTION="${1:---full}"

case "${ACTION}" in
    --setup)
        setup
        ;;
    --analyze)
        analyze
        ;;
    --teardown)
        teardown
        ;;
    --full)
        setup
        echo ""
        analyze
        ;;
    *)
        echo "Usage: $0 [--setup|--analyze|--teardown|--full]"
        echo ""
        echo "  --setup     Start SonarQube Docker + install scanner"
        echo "  --analyze   Run the analysis"
        echo "  --teardown  Stop and remove the Docker container"
        echo "  --full      Setup + Analyze (default)"
        exit 1
        ;;
esac
