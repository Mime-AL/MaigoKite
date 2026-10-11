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
  # The minimum version matches pyproject.toml. Preserve the venv executable path.
  "$@" -I -c 'import sys; sys.exit("Python 3.11+ required") if sys.version_info < (3, 11) else print(sys.executable)' 2>/dev/null
}

maigokite_resolve_python() (
  local project_root="$1" candidate environment
  cd "$project_root" || return 1
  if [ -n "${MAIGOKITE_PYTHON:-}" ]; then
    candidate="$MAIGOKITE_PYTHON"
    case "$candidate" in '~/'*) candidate="$HOME/${candidate:2}" ;; esac
    maigokite_probe_python "$candidate" && return 0
    printf 'MAIGOKITE_PYTHON is not a usable Python 3.11+ executable: %s\n' "$candidate" >&2
    return 1
  fi
  environment="$(maigokite_venv_dir "$project_root")"
  if candidate="$(maigokite_env_python "$environment")"; then
    maigokite_probe_python "$candidate" && return 0
    printf 'Project Python environment is unusable: %s. Run scripts/setup.sh.\n' "$environment" >&2
    return 1
  fi
  if [ -n "${VIRTUAL_ENV:-}" ] && candidate="$(maigokite_env_python "$VIRTUAL_ENV")"; then
    if maigokite_probe_python "$candidate"; then return 0; fi
  fi
  # Delegate managed interpreter / .python-version discovery to uv, without downloads.
  if command -v uv >/dev/null 2>&1; then
    if candidate="$(uv python find --no-python-downloads 2>/dev/null)" && maigokite_probe_python "$candidate"; then
      return 0
    fi
  fi
  for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1 && maigokite_probe_python "$candidate"; then return 0; fi
  done
  if command -v py >/dev/null 2>&1 && maigokite_probe_python py -3; then return 0; fi
  printf 'No usable Core Python found. Run scripts/setup.sh or set MAIGOKITE_PYTHON.\n' >&2
  return 1
)
