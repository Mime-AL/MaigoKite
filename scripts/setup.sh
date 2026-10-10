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
(cd "$PROJECT_ROOT/gateway" && go mod download)

# --- Install Python dependencies ---
info "Installing Python dependencies..."
if command -v uv &>/dev/null; then
  (cd "$PROJECT_ROOT" && uv sync --locked --extra dev)
else
  if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    python3 -m venv "$PROJECT_ROOT/.venv"
  fi
  (cd "$PROJECT_ROOT" && "$PROJECT_ROOT/.venv/bin/python" -m pip install -e ".[dev]")
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
DATA_DIR="$HOME/.maigokite/data"
SKILLS_DIR="$HOME/.maigokite/skills"
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
