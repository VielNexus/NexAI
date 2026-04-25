#!/usr/bin/env bash
set -euo pipefail

if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'
  C_HEAD=$'\033[1;36m'
  C_INFO=$'\033[0;36m'
  C_WARN=$'\033[1;33m'
  C_ERR=$'\033[1;31m'
  C_OK=$'\033[1;32m'
else
  C_RESET=""
  C_HEAD=""
  C_INFO=""
  C_WARN=""
  C_ERR=""
  C_OK=""
fi

header() {
  printf '%s\n' "${C_HEAD}AgentX${C_RESET}"
  printf '%s\n' "${C_INFO}Local-first AI assistant platform${C_RESET}"
  printf '\n'
}

info() {
  printf '%s\n' "${C_INFO}$1${C_RESET}"
}

warn() {
  printf '%s\n' "${C_WARN}$1${C_RESET}" >&2
}

die() {
  printf '%s\n' "${C_ERR}$1${C_RESET}" >&2
  exit 1
}

ok() {
  printf '%s\n' "${C_OK}$1${C_RESET}"
}

usage() {
  cat <<'EOF'
Usage: ./install-agentx.sh [--skip-setup] [-- <agentx setup args...>]

Bootstraps the AgentX CLI into a lightweight user-local environment and installs
an end-user launcher at ~/.local/bin/agentx plus deprecated compatibility
aliases at ~/.local/bin/nexai and ~/.local/bin/sol.

By default this script runs `agentx setup` after bootstrap install.
Use --skip-setup to stop after installing the launcher.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "error: required command not found: $1"
  fi
}

detect_shell_profile() {
  local shell_name=""
  shell_name="$(basename "${SHELL:-}")"
  if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$shell_name" == "zsh" ]]; then
    printf '%s\n' "${HOME}/.zshrc"
    return 0
  fi
  printf '%s\n' "${HOME}/.bashrc"
}

ensure_user_bin_path() {
  local profile_path="$1"
  local path_line="$2"
  local updated_current="0"
  local updated_profile="0"

  if ! echo ":$PATH:" | grep -Fq ":${USER_BIN_DIR}:"; then
    export PATH="${USER_BIN_DIR}:$PATH"
    updated_current="1"
  fi

  if [[ ! -f "$profile_path" ]]; then
    : >"$profile_path"
  fi

  if ! grep -Fqx "$path_line" "$profile_path"; then
    printf '\n%s\n' "$path_line" >>"$profile_path"
    updated_profile="1"
  fi

  PATH_UPDATE_CURRENT="$updated_current"
  PATH_UPDATE_PROFILE="$updated_profile"
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_ROOT="$SCRIPT_DIR"
RUN_SETUP=1
SETUP_ARGS=()

while (($#)); do
  case "$1" in
    --skip-setup|--no-setup)
      RUN_SETUP=0
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      SETUP_ARGS=("$@")
      break
      ;;
    *)
      SETUP_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ! -f "$APP_ROOT/AgentX/pyproject.toml" ]]; then
  warn "expected: $APP_ROOT/AgentX/pyproject.toml"
  die "error: install-agentx.sh must be run from the AgentX app bundle root."
fi

OS_KIND="linux"
if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  OS_KIND="wsl"
fi

if [[ "$OSTYPE" != linux* ]] && [[ "$OS_KIND" != "wsl" ]]; then
  die "error: install-agentx.sh currently supports Linux and WSL only."
fi

require_cmd python3
require_cmd curl

if ! python3 -c "import venv" >/dev/null 2>&1; then
  warn "install the python3-venv package and run this script again."
  die "error: python3 can run, but the stdlib venv module is missing."
fi

if [[ -n "${XDG_DATA_HOME:-}" ]]; then
  BOOTSTRAP_ROOT="${XDG_DATA_HOME}/agentx/bootstrap"
else
  BOOTSTRAP_ROOT="${HOME}/.local/share/agentx/bootstrap"
fi

if [[ -n "${XDG_BIN_HOME:-}" ]]; then
  USER_BIN_DIR="${XDG_BIN_HOME}"
else
  USER_BIN_DIR="${HOME}/.local/bin"
fi

BOOTSTRAP_VENV="${BOOTSTRAP_ROOT}/venv"
BOOTSTRAP_PYTHON="${BOOTSTRAP_VENV}/bin/python"
LAUNCHER_PATH="${USER_BIN_DIR}/agentx"
COMPAT_NEXAI_LAUNCHER_PATH="${USER_BIN_DIR}/nexai"
COMPAT_SOL_LAUNCHER_PATH="${USER_BIN_DIR}/sol"
INSTALL_LOG="${BOOTSTRAP_ROOT}/install.log"
BOOTSTRAP_FALLBACK="${BOOTSTRAP_PYTHON} -m agentx"
PROFILE_PATH="$(detect_shell_profile)"
DEFAULT_USER_BIN_DIR="${HOME}/.local/bin"
if [[ "$USER_BIN_DIR" == "$DEFAULT_USER_BIN_DIR" ]]; then
  PATH_EXPORT_LINE='export PATH="$HOME/.local/bin:$PATH"'
else
  PATH_EXPORT_LINE="export PATH=\"${USER_BIN_DIR}:\$PATH\""
fi

mkdir -p "$BOOTSTRAP_ROOT" "$USER_BIN_DIR"
: >"$INSTALL_LOG"

{
  echo "[bootstrap] platform=${OS_KIND}"
  echo "[bootstrap] app_root=${APP_ROOT}"
  echo "[bootstrap] bootstrap_root=${BOOTSTRAP_ROOT}"
  echo "[bootstrap] bootstrap_python=${BOOTSTRAP_PYTHON}"
  echo "[bootstrap] user_bin_dir=${USER_BIN_DIR}"
} >>"$INSTALL_LOG"

header
info "Bootstrap install"
printf '  App bundle:      %s\n' "${APP_ROOT}"
printf '  Platform:        %s\n' "${OS_KIND}"
printf '  Bootstrap env:   %s\n' "${BOOTSTRAP_VENV}"
printf '  Launcher:        %s\n' "${LAUNCHER_PATH}"
printf '  Legacy nexai:    %s\n' "${COMPAT_NEXAI_LAUNCHER_PATH}"
printf '  Legacy sol:      %s\n' "${COMPAT_SOL_LAUNCHER_PATH}"
printf '\n'

if [[ ! -x "$BOOTSTRAP_PYTHON" ]]; then
  info "Creating bootstrap virtual environment..."
  python3 -m venv "$BOOTSTRAP_VENV" >>"$INSTALL_LOG" 2>&1 || {
    warn "install log: ${INSTALL_LOG}"
    die "error: failed to create bootstrap virtual environment."
  }
fi

if [[ ! -x "$BOOTSTRAP_PYTHON" ]]; then
  warn "install log: ${INSTALL_LOG}"
  die "error: bootstrap interpreter missing after venv creation: ${BOOTSTRAP_PYTHON}"
fi

info "Installing AgentX CLI into bootstrap environment..."
"$BOOTSTRAP_PYTHON" -m pip install --upgrade pip setuptools wheel >>"$INSTALL_LOG" 2>&1 || {
  warn "install log: ${INSTALL_LOG}"
  die "error: failed to upgrade bootstrap packaging tools."
}
"$BOOTSTRAP_PYTHON" -m pip install --upgrade "${APP_ROOT}/AgentX[cli]" >>"$INSTALL_LOG" 2>&1 || {
  warn "install log: ${INSTALL_LOG}"
  die "error: failed to install AgentX into the bootstrap environment."
}

"$BOOTSTRAP_PYTHON" - <<PY >>"$INSTALL_LOG" 2>&1 || {
import sys
from pathlib import Path
from agentx.install.bootstrap import (
    bootstrap_app_root_record_path,
    ensure_bootstrap_python,
    launcher_validation_error,
    launcher_targets_bootstrap_python,
    write_bootstrap_app_root_record,
    write_bootstrap_launcher,
)

expected_bootstrap_root = Path(r"${BOOTSTRAP_ROOT}").expanduser().absolute()
expected_bootstrap_python = ensure_bootstrap_python(
    bootstrap_python=Path(r"${BOOTSTRAP_PYTHON}"),
    bootstrap_root=expected_bootstrap_root,
    require_exists=True,
)
actual_python = Path(sys.executable).expanduser().absolute()
print(f"[bootstrap-helper] sys.executable={actual_python}")
print(f"[bootstrap-helper] expected_bootstrap_python={expected_bootstrap_python}")
print(f"[bootstrap-helper] app_root={Path(r'${APP_ROOT}').resolve()}")
if actual_python != expected_bootstrap_python:
    raise RuntimeError(
        "Bootstrap helper is running under the wrong interpreter: "
        f"{actual_python}. Expected: {expected_bootstrap_python}. "
        "install-agentx.sh must invoke every bootstrap helper via BOOTSTRAP_PYTHON."
    )

launcher = write_bootstrap_launcher(
    launcher_path=Path(r"${LAUNCHER_PATH}"),
    bootstrap_python=expected_bootstrap_python,
    app_root=Path(r"${APP_ROOT}"),
)
compat_launcher = write_bootstrap_launcher(
    launcher_path=Path(r"${COMPAT_NEXAI_LAUNCHER_PATH}"),
    bootstrap_python=expected_bootstrap_python,
    app_root=Path(r"${APP_ROOT}"),
)
sol_compat_launcher = write_bootstrap_launcher(
    launcher_path=Path(r"${COMPAT_SOL_LAUNCHER_PATH}"),
    bootstrap_python=expected_bootstrap_python,
    app_root=Path(r"${APP_ROOT}"),
)
write_bootstrap_app_root_record(
    record_path=bootstrap_app_root_record_path(bootstrap_python=expected_bootstrap_python),
    app_root=Path(r"${APP_ROOT}"),
    bootstrap_python=expected_bootstrap_python,
)
text = launcher.read_text(encoding="utf-8")
if not launcher_targets_bootstrap_python(launcher_text=text, bootstrap_python=expected_bootstrap_python):
    raise RuntimeError(f"launcher does not target bootstrap interpreter: {launcher}")
validation_error = launcher_validation_error(
    launcher_text=text,
    bootstrap_python=expected_bootstrap_python,
    app_root=Path(r"${APP_ROOT}"),
)
if validation_error:
    raise RuntimeError(validation_error)
compat_text = compat_launcher.read_text(encoding="utf-8")
compat_error = launcher_validation_error(
    launcher_text=compat_text,
    bootstrap_python=expected_bootstrap_python,
    app_root=Path(r"${APP_ROOT}"),
)
if compat_error:
    raise RuntimeError(f"compatibility launcher invalid: {compat_error}")
sol_compat_text = sol_compat_launcher.read_text(encoding="utf-8")
sol_compat_error = launcher_validation_error(
    launcher_text=sol_compat_text,
    bootstrap_python=expected_bootstrap_python,
    app_root=Path(r"${APP_ROOT}"),
)
if sol_compat_error:
    raise RuntimeError(f"sol compatibility launcher invalid: {sol_compat_error}")
PY
  warn "install log: ${INSTALL_LOG}"
  die "error: failed to write the AgentX launchers."
}

ensure_user_bin_path "$PROFILE_PATH" "$PATH_EXPORT_LINE"

CURRENT_AGENTX="$(command -v agentx 2>/dev/null || true)"
if [[ -n "$CURRENT_AGENTX" ]] && [[ "$CURRENT_AGENTX" != "$LAUNCHER_PATH" ]]; then
  warn "warning: another agentx command is currently ahead on PATH: ${CURRENT_AGENTX}"
  warn "intended launcher: ${LAUNCHER_PATH}"
fi
CURRENT_NEXAI="$(command -v nexai 2>/dev/null || true)"
if [[ -n "$CURRENT_NEXAI" ]] && [[ "$CURRENT_NEXAI" != "$COMPAT_NEXAI_LAUNCHER_PATH" ]]; then
  warn "warning: another nexai command is currently ahead on PATH: ${CURRENT_NEXAI}"
  warn "intended legacy launcher: ${COMPAT_NEXAI_LAUNCHER_PATH}"
fi
CURRENT_SOL="$(command -v sol 2>/dev/null || true)"
if [[ -n "$CURRENT_SOL" ]] && [[ "$CURRENT_SOL" != "$COMPAT_SOL_LAUNCHER_PATH" ]]; then
  warn "warning: 'sol' may resolve to a different command or a system game: ${CURRENT_SOL}"
  warn "use agentx as the supported AgentX command"
fi

printf '\n'
ok "Bootstrap install complete."
printf '  Bootstrap env:      %s\n' "${BOOTSTRAP_VENV}"
printf '  User launcher:      %s\n' "${LAUNCHER_PATH}"
printf '  Legacy nexai alias: %s\n' "${COMPAT_NEXAI_LAUNCHER_PATH}"
printf '  Legacy sol alias:   %s\n' "${COMPAT_SOL_LAUNCHER_PATH}"
printf '  CLI fallback:       %s\n' "${BOOTSTRAP_FALLBACK}"
printf '  Default runtime:    %s\n' "${HOME}/.local/share/agentx"
printf '  Install log:        %s\n' "${INSTALL_LOG}"
printf '  Shell profile:      %s\n' "${PROFILE_PATH}"
printf '\n'

if [[ "$PATH_UPDATE_PROFILE" == "1" ]]; then
  info "Added ${USER_BIN_DIR} to PATH in ${PROFILE_PATH}."
fi
if [[ "$PATH_UPDATE_CURRENT" == "1" ]]; then
  info "Updated PATH for this installer session."
fi
ok "The 'agentx' command is ready to use. Run: agentx start"

if (( RUN_SETUP )); then
  SETUP_CMD=("${BOOTSTRAP_PYTHON}" -m agentx setup "${SETUP_ARGS[@]}")
  printf -v SETUP_CMD_TEXT '%q ' "${SETUP_CMD[@]}"
  info "Launching AgentX setup with the bootstrap environment..."
  printf '  Command: %s\n' "${SETUP_CMD_TEXT% }"
  export AGENTX_BOOTSTRAP_APP_ROOT="${APP_ROOT}"
  if ! "${SETUP_CMD[@]}"; then
    warn "command: ${SETUP_CMD_TEXT% }"
    warn "install log: ${INSTALL_LOG}"
    die "error: failed to launch AgentX setup through the bootstrap environment."
  fi
  exit 0
fi

info "Next steps:"
printf '  %s setup\n' "agentx"
printf '  %s start\n' "agentx"
printf '  %s stop\n' "agentx"
printf '  %s restart\n' "agentx"
printf '  %s status\n' "agentx"
printf '  %s uninstall\n' "agentx"
printf '  %s doctor\n' "agentx"
printf '  Legacy nexai alias: %s\n' "${COMPAT_NEXAI_LAUNCHER_PATH}"
printf '  Legacy sol alias: %s\n' "${COMPAT_SOL_LAUNCHER_PATH}"
printf '  Bootstrap fallback: %s\n' "${BOOTSTRAP_FALLBACK}"
printf '  Web UI: http://127.0.0.1:5173\n'
