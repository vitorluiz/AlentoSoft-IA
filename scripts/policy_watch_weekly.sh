#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"

if [[ -n "${POLICY_WATCH_ENV_FILE:-}" ]]; then
    if [[ ! -f "$POLICY_WATCH_ENV_FILE" ]]; then
        echo "Ficheiro de ambiente não encontrado: $POLICY_WATCH_ENV_FILE" >&2
        exit 1
    fi
    set -a
    # shellcheck disable=SC1090
    source "$POLICY_WATCH_ENV_FILE"
    set +a
fi

exec python3 -m alento_soft_ia.policy_watch "$@"
