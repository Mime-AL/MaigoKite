#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[TEST]${NC} $*"; }
warn()  { echo -e "${YELLOW}[SKIP]${NC} $*"; }

FAILED=0
TOTAL=0
PASSED=0

run_go_tests() {
  TOTAL=$((TOTAL + 1))
  info "Running Go tests..."
  if (cd "$PROJECT_ROOT/gateway" && go test ./... -count=1 -short 2>&1); then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
    warn "Go tests failed"
  fi
}

run_python_tests() {
  TOTAL=$((TOTAL + 1))
  info "Running Python tests..."
  if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    if (cd "$PROJECT_ROOT" && PYTHONPATH=python .venv/bin/python -m pytest python --tb=short 2>&1); then
      PASSED=$((PASSED + 1))
    else
      FAILED=$((FAILED + 1))
      warn "Python tests failed"
    fi
  elif command -v uv &>/dev/null; then
    if (cd "$PROJECT_ROOT/python" && uv run pytest --tb=short 2>&1); then
      PASSED=$((PASSED + 1))
    else
      FAILED=$((FAILED + 1))
      warn "Python tests failed"
    fi
  elif command -v python3 &>/dev/null; then
    if (cd "$PROJECT_ROOT" && PYTHONPATH=python python3 -m pytest python --tb=short 2>&1); then
      PASSED=$((PASSED + 1))
    else
      FAILED=$((FAILED + 1))
      warn "Python tests failed"
    fi
  else
    FAILED=$((FAILED + 1))
    warn "No Python test runner found"
  fi
}

run_vue_tests() {
  TOTAL=$((TOTAL + 1))
  info "Running Vue tests..."
  if [ -d "$PROJECT_ROOT/web" ] && [ -f "$PROJECT_ROOT/web/package.json" ]; then
    if (cd "$PROJECT_ROOT/web" && npx vitest run --reporter=verbose 2>&1); then
      PASSED=$((PASSED + 1))
    else
      FAILED=$((FAILED + 1))
      warn "Vue tests failed"
    fi
  else
    FAILED=$((FAILED + 1))
    warn "No web/ directory found"
  fi
}

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MaigoKite Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

run_go_tests
echo ""
run_python_tests
echo ""
run_vue_tests
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Results: ${PASSED}/${TOTAL} passed, ${FAILED} failed${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$FAILED" -gt 0 ]; then
  exit 1
fi
