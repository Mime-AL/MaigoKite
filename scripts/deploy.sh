#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

ENVIRONMENT="${1:-development}"

info "Deploying NanamiGopher (environment: $ENVIRONMENT)..."

# Select config file
case "$ENVIRONMENT" in
  production) CONFIG_FILE="config/config.prod.yaml" ;;
  staging)    CONFIG_FILE="config/config.staging.yaml" ;;
  *)          CONFIG_FILE="config/config.dev.yaml" ;;
esac

if [ ! -f "$PROJECT_ROOT/$CONFIG_FILE" ]; then
  warn "Config file $CONFIG_FILE not found, falling back to config.yaml"
  CONFIG_FILE="config/config.yaml"
fi

export APP_ENV="$ENVIRONMENT"

# Build Docker images
info "Building Docker images..."
if ! command -v docker &>/dev/null; then
  error "Docker is not installed"
fi

if ! command -v docker compose &>/dev/null && ! command -v docker-compose &>/dev/null; then
  error "Docker Compose is not installed"
fi

COMPOSE_CMD="docker compose"
command -v docker-compose &>/dev/null && COMPOSE_CMD="docker-compose"

# Start services
info "Starting services with $COMPOSE_CMD..."
(
  cd "$PROJECT_ROOT"
  $COMPOSE_CMD -f docker-compose.yml up -d --build 2>&1
) || error "Deployment failed"

# Health check
info "Waiting for services to become healthy..."
sleep 5

SERVICES_HEALTHY=true
for port in 8080 8081 8000; do
  if ! curl -sf "http://localhost:$port/health" >/dev/null 2>&1; then
    warn "Service on port $port not responding yet"
    SERVICES_HEALTHY=false
  else
    info "Service on port $port is healthy"
  fi
done

if [ "$SERVICES_HEALTHY" = true ]; then
  info "All services deployed successfully!"
  info "API:      http://localhost:8080"
  info "Agent:    http://localhost:8081"
  info "VectorDB: http://localhost:8000"
  info "Web:      http://localhost"
else
  warn "Some services may still be starting. Check with: docker ps"
fi
