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
  printf '%s\n' "${C_HEAD}AgentX Ubuntu installer${C_RESET}"
  printf '%s\n' "${C_INFO}Fresh-machine bootstrap for the AgentX app bundle and managed runtime${C_RESET}"
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

env_value() {
  local name="$1"
  local default="${2:-}"
  local value="${!name-}"
  if [[ -n "$value" ]]; then
    printf '%s\n' "$value"
    return 0
  fi
  if [[ "$name" == AGENTX_* ]]; then
    local suffix="${name#AGENTX_}"
    local legacy_name="NEXAI_${suffix}"
    local legacy_value="${!legacy_name-}"
    if [[ -n "$legacy_value" ]]; then
      printf '%s\n' "$legacy_value"
      return 0
    fi
  fi
  printf '%s\n' "$default"
}

usage() {
  cat <<'EOF'
Usage: ./install.sh [--help]

Fresh Ubuntu 24 installer for AgentX.

Environment overrides:
  AGENTX_REPO_URL          Git clone URL (default: https://github.com/VielAgentX/AgentX.git)
  AGENTX_REF               Git ref to install (default: main)
  AGENTX_APP_ROOT          App bundle path (default: ~/.local/share/agentx/app)
  AGENTX_RUNTIME_ROOT      Mutable runtime root (default: ~/.local/share/agentx)
  AGENTX_WORKDIR           Working directory for AgentX tools (default: $HOME)
  AGENTX_PROFILE           Install profile passed to `agentx setup` (default: standard)
  AGENTX_MODEL_PROVIDER    Model provider for setup (default: ollama)
  AGENTX_OLLAMA_BASE_URL   Ollama URL for setup (default: http://127.0.0.1:11434)
  AGENTX_SKIP_APT          Set to 1 to skip apt package installation
  AGENTX_SKIP_WEB_BUILD    Set to 1 to skip AgentXWeb npm install/build
  AGENTX_AUTOSTART         Set to 1 to run `agentx start` after setup

Legacy NEXAI_* installer environment variables are still accepted as
deprecated fallbacks when the matching AGENTX_* variable is unset.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "error: required command not found: $1"
  fi
}

ensure_local_bin_on_path_for_session() {
  local user_bin_dir="${HOME}/.local/bin"
  if ! echo ":$PATH:" | grep -Fq ":${user_bin_dir}:"; then
    export PATH="${user_bin_dir}:$PATH"
  fi
}

ensure_linux() {
  if [[ "${OSTYPE:-}" != linux* ]]; then
    die "error: install.sh currently supports Linux only."
  fi
}

load_os_release() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
  else
    die "error: could not read /etc/os-release"
  fi
}

ensure_supported_os() {
  load_os_release
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
    warn "warning: this installer is designed for Ubuntu 24.04."
    warn "detected: ${PRETTY_NAME:-unknown}"
    warn "continuing anyway because the script may still work on compatible Debian/Ubuntu systems."
  fi
}

apt_install_if_needed() {
  local packages=("$@")
  local missing=()
  local pkg
  for pkg in "${packages[@]}"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
      missing+=("$pkg")
    fi
  done
  if ((${#missing[@]} == 0)); then
    return 0
  fi
  if [[ "$(env_value AGENTX_SKIP_APT 0)" == "1" ]]; then
    die "error: missing required packages while AGENTX_SKIP_APT=1: ${missing[*]}"
  fi
  local sudo_cmd=()
  if [[ "$(id -u)" -ne 0 ]]; then
    require_cmd sudo
    sudo_cmd=(sudo)
  fi
  info "Installing required Ubuntu packages..."
  "${sudo_cmd[@]}" apt-get update
  "${sudo_cmd[@]}" apt-get install -y "${missing[@]}"
}

ensure_nodejs_supported() {
  local need_nodesource=0
  local node_version=""
  if command -v node >/dev/null 2>&1; then
    node_version="$(node -p "process.versions.node" 2>/dev/null || true)"
  fi
  if ! node_version_is_supported "$node_version"; then
    need_nodesource=1
  fi

  if [[ "$need_nodesource" -eq 0 ]]; then
    return 0
  fi

  if [[ "$(env_value AGENTX_SKIP_APT 0)" == "1" ]]; then
    die "error: Node.js 20.19+ or 22.12+ is required for the Vite 8 toolchain, but the current version is unsupported and AGENTX_SKIP_APT=1."
  fi

  local sudo_cmd=()
  if [[ "$(id -u)" -ne 0 ]]; then
    require_cmd sudo
    sudo_cmd=(sudo)
  fi

  info "Installing a Node.js runtime compatible with Vite 8 for AgentXWeb..."
  "${sudo_cmd[@]}" mkdir -p /etc/apt/keyrings
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | "${sudo_cmd[@]}" gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | "${sudo_cmd[@]}" tee /etc/apt/sources.list.d/nodesource.list >/dev/null
  "${sudo_cmd[@]}" apt-get update
  "${sudo_cmd[@]}" apt-get install -y nodejs
}

node_version_is_supported() {
  local version="${1#v}"
  local major minor patch
  IFS=. read -r major minor patch <<<"$version"
  if [[ -z "${major:-}" || -z "${minor:-}" || -z "${patch:-}" ]]; then
    return 1
  fi
  if ! [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ && "$patch" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  if (( major == 20 )); then
    (( minor >= 19 ))
    return
  fi
  if (( major == 22 )); then
    (( minor >= 12 ))
    return
  fi
  (( major > 22 ))
}

prepare_repo_checkout() {
  local app_root="$1"
  local repo_url="$2"
  local ref="$3"

  mkdir -p "$(dirname "$app_root")"

  if [[ -d "$app_root/.git" ]]; then
    local existing_remote
    existing_remote="$(git -C "$app_root" remote get-url origin 2>/dev/null || true)"
    if [[ "$existing_remote" != "$repo_url" ]]; then
      die "error: ${app_root} already exists but points to a different git remote: ${existing_remote}"
    fi
    info "Updating existing AgentX checkout..."
    git -C "$app_root" fetch --tags origin
    git -C "$app_root" checkout "$ref"
    if git -C "$app_root" rev-parse --verify "origin/$ref" >/dev/null 2>&1; then
      git -C "$app_root" reset --hard "origin/$ref"
    fi
    git -C "$app_root" clean -fdx -e .venv -e venv
    return 0
  fi

  if [[ -e "$app_root" ]] && [[ -n "$(find "$app_root" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]]; then
    die "error: app root exists and is not an empty AgentX checkout: ${app_root}"
  fi

  info "Cloning AgentX repository..."
  rm -rf "$app_root"
  git clone --branch "$ref" --depth 1 "$repo_url" "$app_root"
}

build_agentxweb() {
  local app_root="$1"
  if [[ "$(env_value AGENTX_SKIP_WEB_BUILD 0)" == "1" ]]; then
    warn "warning: skipping AgentXWeb build because AGENTX_SKIP_WEB_BUILD=1"
    return 0
  fi
  info "Installing AgentXWeb dependencies..."
  rm -rf "$app_root/AgentXWeb/node_modules"
  npm --prefix "$app_root/AgentXWeb" install
  info "Building AgentXWeb production assets..."
  npm --prefix "$app_root/AgentXWeb" run build
}

run_bootstrap_install() {
  local app_root="$1"
  local runtime_root="$2"
  local working_dir="$3"
  local profile="$4"
  local provider="$5"
  local ollama_url="$6"

  info "Running AgentX bootstrap + managed runtime setup..."
  bash "$app_root/install-agentx.sh" -- \
    --non-interactive \
    --profile "$profile" \
    --app-root "$app_root" \
    --runtime-root "$runtime_root" \
    --working-dir "$working_dir" \
    --model-provider "$provider" \
    --ollama-base-url "$ollama_url" \
    --api-host 127.0.0.1 \
    --api-port 8420 \
    --web-host 127.0.0.1 \
    --web-port 5173 \
    --web-enabled true \
    --service-mode none
}

main() {
  if (($#)); then
    case "$1" in
      --help|-h)
        usage
        exit 0
        ;;
      *)
        die "error: unknown argument: $1"
        ;;
    esac
  fi

  ensure_linux
  ensure_supported_os

  local repo_url
  repo_url="$(env_value AGENTX_REPO_URL "https://github.com/VielAgentX/AgentX.git")"
  local ref
  ref="$(env_value AGENTX_REF main)"
  local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
  local app_root
  app_root="$(env_value AGENTX_APP_ROOT "$data_home/agentx/app")"
  local runtime_root
  runtime_root="$(env_value AGENTX_RUNTIME_ROOT "$data_home/agentx")"
  local working_dir
  working_dir="$(env_value AGENTX_WORKDIR "$HOME")"
  local profile
  profile="$(env_value AGENTX_PROFILE standard)"
  local provider
  provider="$(env_value AGENTX_MODEL_PROVIDER ollama)"
  local ollama_url
  ollama_url="$(env_value AGENTX_OLLAMA_BASE_URL "http://127.0.0.1:11434")"

  header
  printf '  Repo URL:       %s\n' "$repo_url"
  printf '  Git ref:        %s\n' "$ref"
  printf '  App root:       %s\n' "$app_root"
  printf '  Runtime root:   %s\n' "$runtime_root"
  printf '  Working dir:    %s\n' "$working_dir"
  printf '  Install profile:%s\n' " $profile"
  printf '  Model provider: %s\n' "$provider"
  printf '\n'

  apt_install_if_needed ca-certificates curl git gnupg python3 python3-venv python3-pip
  require_cmd git
  require_cmd python3
  require_cmd bash
  ensure_nodejs_supported
  require_cmd npm

  prepare_repo_checkout "$app_root" "$repo_url" "$ref"
  build_agentxweb "$app_root"
  run_bootstrap_install "$app_root" "$runtime_root" "$working_dir" "$profile" "$provider" "$ollama_url"
  ensure_local_bin_on_path_for_session

  local launcher="agentx"
  printf '\n'
  ok "AgentX install completed."
  printf '  Launcher:       %s\n' "${HOME}/.local/bin/agentx"
  printf '  App root:       %s\n' "$app_root"
  printf '  Runtime root:   %s\n' "$runtime_root"
  printf '\n'
  ok "The 'agentx' command is ready to use. Run: agentx start"

  if [[ "$(env_value AGENTX_AUTOSTART 0)" == "1" ]]; then
    info "Starting AgentX services..."
    "$launcher" start
  fi

  info "Next steps:"
  printf '  %s start\n' "$launcher"
  printf '  %s stop\n' "$launcher"
  printf '  %s restart\n' "$launcher"
  printf '  %s status\n' "$launcher"
  printf '  %s uninstall\n' "$launcher"
  printf '  %s doctor\n' "$launcher"
  printf '  Web UI: http://127.0.0.1:5173\n'
  if [[ "$provider" == "ollama" ]]; then
    printf '  Ollama: make sure a local Ollama server is running at %s\n' "$ollama_url"
  fi
}

main "$@"
