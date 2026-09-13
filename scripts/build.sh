#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[BUILD]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

BUILD_TYPE="${1:-all}"

build_go() {
  info "Building Go API..."
  local output="nanamigopher-api"
  if [ "$BUILD_TYPE" != "go" ] && [ "$BUILD_TYPE" != "all" ]; then
    warn "Skipping Go build (requested: $BUILD_TYPE)"
    return
  fi
  (cd "$PROJECT_ROOT" && \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
      -ldflags="-s -w -X main.Version=$(grep '^version' config/config.yaml | head -1 | cut -d'"' -f2)" \
      -o "$PROJECT_ROOT/dist/$output" \
      ./go/cmd/api/ 2>&1) || error "Go build failed"
  info "Go binary: dist/$output"
}

build_python() {
  info "Building Python package..."
  if [ "$BUILD_TYPE" != "python" ] && [ "$BUILD_TYPE" != "all" ]; then
    warn "Skipping Python build (requested: $BUILD_TYPE)"
    return
  fi
  mkdir -p "$PROJECT_ROOT/dist"
  if command -v uv &>/dev/null; then
    (cd "$PROJECT_ROOT" && uv build 2>&1) || error "uv build failed"
  elif command -v poetry &>/dev/null; then
    (cd "$PROJECT_ROOT" && poetry build 2>&1) || error "Poetry build failed"
  else
    (cd "$PROJECT_ROOT" && python -m build 2>&1) || error "Python build failed"
  fi
  info "Python wheel/sdist in dist/"
}

build_vue() {
  info "Building Vue frontend..."
  if [ "$BUILD_TYPE" != "vue" ] && [ "$BUILD_TYPE" != "all" ]; then
    warn "Skipping Vue build (requested: $BUILD_TYPE)"
    return
  fi
  if [ ! -d "$PROJECT_ROOT/web" ]; then
    warn "No web/ directory found – skipping Vue build"
    return
  fi
  (cd "$PROJECT_ROOT/web" && npm run build 2>&1) || error "Vue build failed"
  info "Vue build output: web/dist/"
}

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  NanamiGopher Build ($BUILD_TYPE)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

mkdir -p "$PROJECT_ROOT/dist"

build_go
echo ""
build_python
echo ""
build_vue
echo ""

echo -e "${BLUE}========================================${NC}"
info "Build complete! Artifacts in dist/"
echo -e "${BLUE}========================================${NC}"
