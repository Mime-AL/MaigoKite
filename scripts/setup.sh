#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# --- Dependency checks ---
check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    error "Required command '$1' not found. Please install it first."
  fi
}

info "Checking system dependencies..."

# Core runtimes
check_cmd go
check_cmd python3
check_cmd node

# Optional but recommended
for cmd in docker docker-compose; do
  if command -v "$cmd" &>/dev/null; then
    info "Found $cmd"
  else
    warn "$cmd not found – Docker features will be unavailable"
  fi
done

# --- Install Go dependencies ---
info "Installing Go dependencies..."
(cd "$PROJECT_ROOT" && go mod download)

# --- Install Python dependencies ---
info "Installing Python dependencies..."
if command -v uv &>/dev/null; then
  (cd "$PROJECT_ROOT" && uv sync --all-extras)
elif command -v poetry &>/dev/null; then
  (cd "$PROJECT_ROOT" && poetry install --no-root)
else
  (cd "$PROJECT_ROOT" && pip install -e ".[dev]" 2>/dev/null || pip install -r requirements.txt 2>/dev/null || true)
fi

# --- Install Node.js dependencies ---
info "Installing Node.js dependencies..."
if [ -d "$PROJECT_ROOT/web" ] && [ -f "$PROJECT_ROOT/web/package.json" ]; then
  (cd "$PROJECT_ROOT/web" && npm ci)
else
  warn "No web/ directory found – skipping frontend installation"
fi

# --- Create data directories ---
info "Creating data directories..."
DATA_DIR="$HOME/.nanamigopher/data"
SKILLS_DIR="$HOME/.nanamigopher/skills"
mkdir -p "$DATA_DIR" "$SKILLS_DIR"

# --- Copy configuration ---
info "Copying default configuration..."
CONFIG_SRC="$PROJECT_ROOT/config"
CONFIG_DST="$DATA_DIR"
if [ ! -f "$DATA_DIR/config.yaml" ]; then
  cp "$CONFIG_SRC/config.yaml" "$CONFIG_DST/"
  info "Copied config.yaml to $DATA_DIR"
else
  info "config.yaml already exists – skipping"
fi

info "Setup complete!"
