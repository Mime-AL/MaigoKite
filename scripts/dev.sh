#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[DEV]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

export APP_ENV="development"
export NANAMI_WORKSPACE_ROOT="${NANAMI_WORKSPACE_ROOT:-$PROJECT_ROOT}"

cleanup() {
  info "Shutting down development servers..."
  jobs -p | xargs -r kill 2>/dev/null
  wait 2>/dev/null
  exit
}
trap cleanup EXIT INT TERM

info "Starting NanamiGopher development environment..."
echo ""

# --- Go API server ---
info "Starting Go API server on :8080..."
(
  cd "$PROJECT_ROOT/gateway"
  NANAMI_CONFIG="$PROJECT_ROOT/config/config.dev.yaml" go run ./cmd/gateway 2>&1
) &
GO_PID=$!
info "Go API PID: $GO_PID"

# --- Python Agent server ---
info "Starting Python agent on :8081..."
if [ -d "$PROJECT_ROOT/python" ]; then
  PYTHON_BIN="${NANAMI_PYTHON:-python3}"
  if [ -x "$PROJECT_ROOT/.venv/bin/python" ] && [ -z "${NANAMI_PYTHON:-}" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
  fi
  (
    cd "$PROJECT_ROOT"
    PYTHONPATH="$PROJECT_ROOT/python" "$PYTHON_BIN" \
      -m agent.main run --config "$PROJECT_ROOT/config/config.dev.yaml" --port 8081 2>&1
  ) &
  PY_PID=$!
  info "Python Agent PID: $PY_PID"
else
  warn "python/ directory not found – skipping Python agent"
fi

# --- Vue dev server ---
info "Starting Vue dev server on :5173..."
if [ -d "$PROJECT_ROOT/web" ] && [ -f "$PROJECT_ROOT/web/package.json" ]; then
  (
    cd "$PROJECT_ROOT/web"
    npx vite --host 0.0.0.0 --port 5173 2>&1
  ) &
  VUE_PID=$!
  info "Vue Dev Server PID: $VUE_PID"
else
  warn "web/ directory not found – skipping Vue dev server"
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Development Servers Running${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  Go API:     http://localhost:8080"
echo -e "  Python:     grpc://localhost:8081"
echo -e "  Vue:        http://localhost:5173"
echo -e "${CYAN}========================================${NC}"
echo ""
info "Press Ctrl+C to stop all servers"

wait
