#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
printf '%s\n' "warning: install-sol.sh is deprecated; use install-agentx.sh." >&2
exec "${SCRIPT_DIR}/install-agentx.sh" "$@"
