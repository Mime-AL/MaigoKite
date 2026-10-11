#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v node >/dev/null 2>&1 || { echo 'Node.js is required; see README.md for supported versions.' >&2; exit 1; }
exec bash "$SCRIPT_DIR/start.sh" web dev "$@"
