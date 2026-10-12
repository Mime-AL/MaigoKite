#!/usr/bin/env bash
# Core interpreter discovery only; workspace tools and MCP keep their own runtimes.

maigokite_venv_dir() {
  local directory="${UV_PROJECT_ENVIRONMENT:-$1/.venv}"
  case "$directory" in
    /* | [[:alpha:]]:*) ;;
    *) directory="$1/$directory" ;;
  esac
  printf '%s\n' "$directory"
}

maigokite_env_python() {
  local candidate
  for candidate in "$1/bin/python" "$1/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

maigokite_probe_python() {
  # Match the project's minor version and retain the selected venv executable path.
  "$@" -I -c 'import sys; sys.exit("Python 3.14.x required") if sys.version_info[:2] != (3, 14) else print(sys.executable)' 2>/dev/null
}

maigokite_resolve_python() (
  local project_root="$1" candidate environment
  cd "$project_root" || return 1
  if [ -n "${MAIGOKITE_PYTHON:-}" ]; then
    candidate="$MAIGOKITE_PYTHON"
    case "$candidate" in '~/'*) candidate="$HOME/${candidate:2}" ;; esac
    maigokite_probe_python "$candidate" && return 0
    printf 'MAIGOKITE_PYTHON is not a usable Python 3.14.x executable: %s\n' "$candidate" >&2
    return 1
  fi
  environment="$(maigokite_venv_dir "$project_root")"
  if candidate="$(maigokite_env_python "$environment")"; then
    maigokite_probe_python "$candidate" && return 0
    printf 'Project environment requires Python 3.14.x: %s. Stop the app and run setup with uv; without uv, rename the old environment first.\n' "$environment" >&2
    return 1
  fi
  if [ -n "${VIRTUAL_ENV:-}" ] && candidate="$(maigokite_env_python "$VIRTUAL_ENV")"; then
    if maigokite_probe_python "$candidate"; then return 0; fi
  fi
  # Delegate managed interpreter / .python-version discovery to uv, without downloads.
  if command -v uv >/dev/null 2>&1; then
    if candidate="$(uv python find 3.14 --no-python-downloads 2>/dev/null)" && maigokite_probe_python "$candidate"; then
      return 0
    fi
  fi
  for candidate in python3.14 python python3; do
    if command -v "$candidate" >/dev/null 2>&1 && maigokite_probe_python "$candidate"; then return 0; fi
  done
  if command -v py >/dev/null 2>&1 && maigokite_probe_python py -3.14; then return 0; fi
  printf 'Python 3.14.x not found. Run scripts/setup.sh with uv or set MAIGOKITE_PYTHON.\n' >&2
  return 1
)
